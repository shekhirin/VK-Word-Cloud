from datetime import datetime
from queue import Queue
from threading import Thread

import vk_api

from vk_wc import send_cloud, worker
import config

vk_group_session = vk_api.VkApi(token=config.vk_community_token)
vk_group = vk_group_session.get_api()

if __name__ == '__main__':
    q = Queue()
    for i in range(10):
        t = Thread(target=worker, args=(q,))
        t.setDaemon(True)
        t.start()


    def start_checking(dialogs):
        for i, dialog in enumerate(dialogs):
            # if dialog['message']['date'] < datetime(2017, 3, 1).timestamp():
            # if dialog['message']['body'].lower() == 'облако':
            #     q.put((send_cloud, (dialog['message']['user_id'], dialog['message']['body']), {}))
            # if dialog['message']['body'].startswith('Посмотрим'):
            #     q.put((send_cloud, (dialog['message']['user_id'], 'облако'), {}))
            if dialog['message']['body'] != 'Кстати, у нас в группе проходит конкурс, советую принять участие 😉':
                q.put((vk_group.messages.send, (),
                       {'user_id': dialog['message']['user_id'],
                        'message': 'Кстати, у нас в группе проходит конкурс, советую принять участие 😉',
                        'attachment': 'wall-136503501_467'
                        }))

    start_checking(vk_api.VkTools(vk_group_session).get_all('messages.getDialogs', 200)['items'])
    q.join()
