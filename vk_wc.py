
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

vk_group = vk_api.VkApi(token=config.vk_community_token).get_api()
vk_session = vk_api.VkApi(token=config.vk_user_token)
tools = vk_api.VkTools(vk_session)
vk = vk_session.get_api()
collection = MongoClient()['wordcloud']['photos']

processing = []

def cloud(user_id):
    wall = []
    offset = 0
    year = int(time.mktime(datetime(2016, 1, 1).timetuple()))
    while True:
        part = vk.wall.get(owner_id=user_id, count=100, offset=offset)['items']
        part = list(filter(lambda x: x['date'] > year, part))
        if len(part) == 0:
            break
        else:
            wall.extend(part)
            offset += 100
    tokenizer = RegexpTokenizer('[a-zA-Zа-яА-ЯёЁ]+')
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
    if not top_words:
        return
    def color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        return "hsl(%d, 100%%, %d%%)" % (random.randint(0, 360), random.randint(20, 50))
    sw = (stopwords.words('russian') + stopwords.words('english'))
    wordcloud = WordCloud(
        max_words=100,
        background_color='white',
        margin=5,
        stopwords=sw,
        width=1000,
        height=1000
    ).generate(' '.join(top_words))
    wordcloud = wordcloud.recolor(color_func=color_func, random_state=3)
    wordcloud.to_file('{}.jpg'.format(user_id))
    return open('{}.jpg'.format(user_id), 'rb')

def make_cloud(user_id):
    processing.append(user_id)
    try:
        if len(vk.wall.get(owner_id=user_id, count=1)['items']) == 0:
            vk_group.messages.send(user_id=user_id, message='Похоже, у тебя недостаточно записей на стене для составления облака тегов☹️')
            time.sleep(5)
            return
        else:
            latest = vk.wall.get(owner_id=user_id, count=1)['items'][0]
            if latest['date'] < int(time.mktime(datetime(2016, 1, 1).timetuple())) or not latest['text']:
                if 'copy_history' in latest:
                    for copy in latest['copy_history']:
                        if 'text' not in copy:
                            vk_group.messages.send(user_id=user_id, message='Похоже, у тебя недостаточно записей на стене для составления облака тегов☹️')
                            time.sleep(5)
                            return
        vk_group.messages.send(user_id=user_id, message='Посмотрим, чем ты увлекался в 2016 году...⌛️')
        user = vk.users.get(user_ids=user_id)[0]
        user_id = user['id']
        name = user['first_name'] + ' ' + user['last_name']
        data = vk.photos.getUploadServer(album_id=239993461, group_id=136503501)
        DATA_UPLOAD_URL = data['upload_url']
        if os.path.isfile('{}.jpg'.format(user_id)):
            clouded = open('{}.jpg'.format(user_id), 'rb')
            photo = collection.find_one({'user_id': user_id})
        else:
            clouded = cloud(user_id)
            if not clouded:
                vk_group.messages.send(user_id=user_id, message='Похоже, у тебя недостаточно записей на стене для составления облака тегов☹️')
                time.sleep(5)
                return
            r = requests.post(DATA_UPLOAD_URL, files={'photo': clouded}).json()
            photo = vk.photos.save(server=r['server'], photos_list=r['photos_list'], group_id=r['gid'], album_id=r['aid'], hash=r['hash'])[0]
            collection.insert({'user_id': user_id, 'owner_id': photo['owner_id'], 'id': photo['id']})
        # post = vk.wall.post(owner_id=-136503501, from_group=1, message='Облако тегов за 2016 год для *id{}({})'.format(user_id, name), attachments='photo{}_{}'.format(photo['owner_id'], photo['id']))
        vk_group.messages.send(user_id=user_id, message='А вот и твое облако тегов на 2016 год!', attachment='photo{}_{}'.format(photo['owner_id'], photo['id']))
        vk_group.messages.send(user_id=user_id, message='Не забудь рассказать друзьям 😉')
    except Exception as e:
        processing.remove(user_id)
        print(e)
        pass
    processing.remove(user_id)

def process_updates(updates):
    for update in updates:
        if update[0] == 4 and update[3] not in processing and update[6].lower() == 'облако':
            make_cloud(update[3])

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
        continue
