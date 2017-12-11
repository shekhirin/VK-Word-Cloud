import os
from queue import Queue
from threading import Thread

import requests
from concurrent.futures import ThreadPoolExecutor
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from datetime import datetime
import time
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
import matplotlib

matplotlib.use('Agg')
from wordcloud import WordCloud
import random
import pymorphy2
from pymongo import MongoClient
import config
import io

print('Connecting to VK...', end=' ')
vk_group_session = vk_api.VkApi(token=config.vk_community_token)
vk_group = vk_group_session.get_api()
vk_session = vk_api.VkApi(token=config.vk_user_token)
tools = vk_api.VkTools(vk_session)
vk = vk_session.get_api()
vk_upload = vk_api.VkUpload(vk_session)
print('Done')

print('Connecting to MongoDB...', end=' ')
collection = MongoClient(config.mongo_host)[config.mongo_db]['photos']
print('Done')

remove_words = ['год']
DIR = os.path.dirname(__file__)

processing = []


def cloud(user_id):
    wall = tools.get_all('wall.get', 100, {'owner_id': user_id})['items']
    wall = list(filter(lambda x: datetime.fromtimestamp(x['date']).year == 2017, wall))

    tokenizer = RegexpTokenizer('[а-яА-ЯёЁ]+')
    morph = pymorphy2.MorphAnalyzer()

    def transform(sentence):
        return map(lambda x: morph.parse(x)[0].normal_form.replace('ё', 'е'),
                   filter(
                       lambda x: len(x) > 2 and 'NOUN' in morph.parse(x)[0].tag,
                       tokenizer.tokenize(sentence.replace('\xa0', ' '))
                   )
                   )

    top_words = []
    for post in wall:
        if 'text' in post:
            top_words.extend(transform(post['text']))
        if 'copy_history' in post:
            for copy in post['copy_history']:
                if 'text' in copy:
                    top_words.extend(transform(copy['text']))
    top_words = list(filter(lambda x: x.lower() not in remove_words, top_words))
    if not top_words:
        return

    # def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    #     return "hsl(%d, 100%%, %d%%)" % (random.randint(0, 360), random.randint(20, 50))

    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        return "rgb(255, 255, 255)"

    sw = (stopwords.words('russian') + stopwords.words('english') + remove_words)
    wordcloud = WordCloud(
        max_words=200,
        max_font_size=500,
        background_color='black',
        margin=5,
        width=1000,
        height=1000,
        stopwords=sw,
        prefer_horizontal=0.95,
        font_path='font.ttf'
    ).generate(' '.join(top_words).upper())
    wordcloud = wordcloud.recolor(color_func=color_func, random_state=3).to_image()
    img_arr = io.BytesIO()
    wordcloud.save(img_arr, format='PNG')
    img_arr.seek(0)
    return img_arr, wall, top_words


def send_cloud(user_id, message):
    if message.lower() != 'облако':
        vk_group.messages.send(user_id=user_id, message='Если ты хочешь получить свое облако тегов за 2017 '
                                                        'год, отправь мне слово "облако" без кавычек 🙃')
        time.sleep(5)
        return

    processing.append(user_id)

    print('Generating cloud for', user_id)
    try:
        # if not vk.groups.isMember(group_id=config.group_id, user_id=user_id):
        #     vk_group.messages.send(user_id=user_id,
        #                            message='Чтобы составить облако тегов, '
        #                                    'подпишись на меня https://vk.com/wwcloud 🙄')
        #     time.sleep(1)
        #     vk_group.messages.send(user_id=user_id,
        #                            message='Когда будешь готов, снова отправь кодовое слово "облако" 😊')
        #     processing.remove(user_id)
        #     time.sleep(5)
        #     return
        if len(vk.wall.get(owner_id=user_id, count=1)['items']) == 0:
            vk_group.messages.send(user_id=user_id,
                                   message='Похоже, у тебя недостаточно записей на стене '
                                           'для составления облака тегов☹️')
            processing.remove(user_id)
            time.sleep(5)
            return
        vk_group.messages.send(user_id=user_id, message='Посмотрим, что тебя интересовало в 2017 году больше всего 😋')
        user = vk.users.get(user_ids=user_id)[0]
        user_id = user['id']
        name = user['first_name'] + ' ' + user['last_name']
        clouded = cloud(user_id)
        if not clouded:
            vk_group.messages.send(user_id=user_id,
                                   message='Похоже, у тебя недостаточно записей на стене '
                                           'для составления облака тегов ☹️')
            processing.remove(user_id)
            time.sleep(5)
            return
        clouded, wall, top_words = clouded
        photo = vk_upload.photo(
            clouded,
            album_id=config.album_id,
            group_id=config.group_id
        )[0]
        vk_group.messages.send(user_id=user_id, message='А вот и твое облако тегов! 🌍',
                               attachment='photo{}_{}'.format(photo['owner_id'], photo['id']))
        vk_group.messages.send(user_id=user_id, message='Не забудь рассказать друзьям 😉')

        post_id = None
        if len(top_words) > 50 and \
                not collection.find_one({'user_id': user_id, 'timestamp': {'$gt': time.time() - 86400}}):
            try:
                post_id = vk.wall.post(owner_id='-{}'.format(config.group_id), from_group=1,
                                       message='Облако тегов для *id{}({})'.format(user_id, name),
                                       attachments='photo{}_{}'.format(photo['owner_id'], photo['id']))['post_id']
            except Exception as e:
                print(e)
                vk_group.messages.send(user_id=user_id,
                                       message='Похоже, я превысил лимит количества постов на сегодня 😭')
                vk_group.messages.send(user_id=user_id,
                                       message='Создай новое облако завтра, и я выложу его на стену группы 😎')

        vk_group.messages.send(
            user_id=user_id,
            message='Кстати, у нас в группе скоро будет проходить розыгрыш НАСТОЯЩЕГО облака, '
                    'не пропусти 🎁🎁🎁',
            attachment=['audio179996500_456239257'] +
                       (['wall-136503501_466'] if
                        datetime.now().year == 2017 and
                        datetime.now().month == 12 and
                        datetime.now().day >= 12 else [])
        )

        if post_id:
            collection.insert({
                'user_id': user_id,
                'owner_id': photo['owner_id'],
                'id': photo['id'],
                'post': post_id,
                'timestamp': time.time()
            })
            vk_group.messages.send(user_id=user_id, attachment='wall{}_{}'.format(photo['owner_id'], post_id))
        else:
            collection.insert({
                'user_id': user_id,
                'owner_id': photo['owner_id'],
                'id': photo['id'],
                'timestamp': time.time()
            })
        processing.remove(user_id)
        print('Finished cloud for', user_id)
        return
    except Exception as e:
        processing.remove(user_id)
        print('Finished cloud for', user_id, 'with error')
        raise e


def worker(q):
    while True:
        # Получаем задание из очереди
        item = q.get()
        item[0](*item[1], **item[2])
        # Сообщаем о выполненном задании
        q.task_done()


if __name__ == '__main__':
    q = Queue()
    for i in range(10):
        t = Thread(target=worker, args=(q,))
        t.setDaemon(True)
        t.start()

    print('Initializing longpoll connection...', end=' ')
    longpoll = VkLongPoll(vk_group_session)
    print('Done')

    for event in longpoll.listen():
        if event.to_me and event.type == VkEventType.MESSAGE_NEW and event.user_id not in processing:
            print(event.user_id, event.text)
            q.put((send_cloud, (event.user_id, event.text), {}))
    q.join()
