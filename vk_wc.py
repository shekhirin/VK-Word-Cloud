
# coding: utf-8

# In[1]:

import requests
from threading import Thread
import os
import vk_api
from datetime import datetime
import time
from nltk.tokenize import RegexpTokenizer
from nltk.corpus import stopwords
import nltk
from collections import Counter
from wordcloud import WordCloud
import random
import pymorphy2
from multiprocessing.pool import Pool
from tqdm import tqdm
from pymongo import MongoClient
import config
import math
from textblob import TextBlob as tb

vk_group = vk_api.VkApi(token=config.vk_community_token).get_api()
vk_session = vk_api.VkApi(token=config.vk_user_token)
tools = vk_api.VkTools(vk_session)
vk = vk_session.get_api()
collection = MongoClient()['wordcloud']['photos']
remove_words = ['год']

processing = []

def tf(word, blob):
    return blob.words.count(word) / len(blob.words)

def n_containing(word, bloblist):
    return sum(1 for blob in bloblist if word in blob.words)

def idf(word, bloblist):
    return math.log(len(bloblist) / (1 + n_containing(word, bloblist)))

def tfidf(word, blob, bloblist):
    return tf(word, blob) * idf(word, bloblist)

def cloud(user_id):
    wall = []
    offset = 0
    while True:
        part = vk.wall.get(owner_id=user_id, count=100, offset=offset)['items']
        if len(part) == 0:
            break
        else:
            wall.extend(part)
            offset += 100
    tokenizer = RegexpTokenizer('[а-яА-ЯёЁ]+')
    morph = pymorphy2.MorphAnalyzer()
    def transform(sentence):
        return map(lambda x: morph.parse(x)[0].normal_form, filter(lambda x: len(x) > 2 and 'NOUN' in morph.parse(x)[0].tag, tokenizer.tokenize(sentence.replace('\xa0', ' '))))
    top_words = []
    for post in wall:
        if 'text' in post:
            top_words.extend(transform(post['text']))
        if 'copy_history' in post:
            for copy in post['copy_history']:
                if 'text' in copy:
                    top_words.extend(transform(copy['text']))
    top_words = list(filter(lambda x: x.lower() not in remove_words, top_words))
    if not top_words or len(set(top_words)) < 10:
        return
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        return "hsl(%d, 100%%, %d%%)" % (random.randint(0, 360), random.randint(20, 50))
    sw = (stopwords.words('russian') + stopwords.words('english') + remove_words)
    wordcloud = WordCloud(
        background_color='white',
        margin=5,
        width=1000,
        height=1000,
        stopwords=sw
    ).generate(' '.join(top_words))
    wordcloud = wordcloud.recolor(color_func=color_func, random_state=3)
    wordcloud.to_file('clouds/{}.jpg'.format(user_id))
    return open('clouds/{}.jpg'.format(user_id), 'rb'), top_words

def send_cloud(user_id):
    processing.append(user_id)
    try:
        if not vk.groups.isMember(group_id=config.group_id, user_id=user_id):
            vk_group.messages.send(user_id=user_id, message='Чтобы составить облако тегов, подпишись на меня https://vk.com/wordcloud2017 🙄')
            time.sleep(1)
            vk_group.messages.send(user_id=user_id, message='Когда будешь готов, снова отправь кодовое слово "облако" 😊')
            processing.remove(user_id)
            time.sleep(5)
            return
        if len(vk.wall.get(owner_id=user_id, count=1)['items']) == 0:
            vk_group.messages.send(user_id=user_id, message='Похоже, у тебя недостаточно записей на стене для составления облака тегов☹️')
            processing.remove(user_id)
            time.sleep(5)
            return
        else:
            latest = vk.wall.get(owner_id=user_id, count=1)['items'][0]
            if not latest['text']:
                if 'copy_history' in latest:
                    for copy in latest['copy_history']:
                        if 'text' not in copy:
                            vk_group.messages.send(user_id=user_id, message='Похоже, у тебя недостаточно записей на стене для составления облака тегов☹️')
                            processing.remove(user_id)
                            time.sleep(5)
                            return
        vk_group.messages.send(user_id=user_id, message='Посмотрим, что тебя интересует больше всего 😋')
        user = vk.users.get(user_ids=user_id)[0]
        user_id = user['id']
        name = user['first_name'] + ' ' + user['last_name']
        data = vk.photos.getUploadServer(album_id=config.album_id, group_id=config.group_id)
        DATA_UPLOAD_URL = data['upload_url']
        clouded, words = cloud(user_id)
        if not clouded:
            vk_group.messages.send(user_id=user_id, message='Похоже, у тебя недостаточно записей на стене для составления облака тегов☹️')
            time.sleep(5)
            return
        r = requests.post(DATA_UPLOAD_URL, files={'photo': clouded}).json()
        photo = vk.photos.save(server=r['server'], photos_list=r['photos_list'], group_id=r['gid'], album_id=r['aid'], hash=r['hash'])[0]
        collection.insert({'user_id': user_id, 'owner_id': photo['owner_id'], 'id': photo['id']})
        # post = vk.wall.post(owner_id=-136503501, from_group=1, message='Облако тегов за 2016 год для *id{}({})'.format(user_id, name), attachments='photo{}_{}'.format(photo['owner_id'], photo['id']))
        vk_group.messages.send(user_id=user_id, message='А вот и твое облако тегов! 🌍', attachment='photo{}_{}'.format(photo['owner_id'], photo['id']))
        vk_group.messages.send(user_id=user_id, message='Не забудь рассказать друзьям 😉')
    except Exception as e:
        processing.remove(user_id)
        print(e)
        pass
    processing.remove(user_id)

def send_friend_cloud(user_id, friend_id=None):
    if not friend_id:

        time.sleep(5)

def process_updates(updates):
    for update in updates:
        if update[0] == 4 and update[3] not in processing:
            if update[6].lower() in 'облако':
                Thread(target=send_cloud, args=(update[3], )).start()
            elif update[6].lower() in 'облако для друга':
                Thread(target=send_friend_cloud, args=(update[3], )).start()

if __name__ == '__main__':
    longpoll = vk_group.messages.getLongPollServer()
    while True:
        try:
            response = requests.get('https://{}?act=a_check&key={}&ts={}&wait=25%mode=128'.format(
                longpoll['server'],
                longpoll['key'],
                longpoll['ts']
            ), timeout=25).json()
            longpoll['ts'] = response['ts'] if 'ts' in response else longpoll['ts']
            Thread(target=process_updates, args=(response['updates'], )).start()
        except Exception as e:
            longpoll = vk_group.messages.getLongPollServer()
            print(e)
            continue
