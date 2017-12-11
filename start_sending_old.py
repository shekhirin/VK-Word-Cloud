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
            if dialog['message']['body'].lower() == 'облако':
                q.put((send_cloud, (dialog['message']['user_id'], dialog['message']['body']), {}))
            if dialog['message']['body'].startswith('Посмотрим'):
                q.put((send_cloud, (dialog['message']['user_id'], 'облако'), {}))
            # if not dialog['message']['body'].startswith('Кстати'):
            #     q.put((vk_group.messages.send, (),
            #            {'user_id': dialog['message']['user_id'],
            #             'message': 'Кстати, у нас в группе скоро будет проходить розыгрыш НАСТОЯЩЕГО облака, '
            #                        'не пропусти 🎁🎁🎁',
            #             'attachment': ['audio179996500_456239257'] +
            #                           (['wall-136503501_466'] if
            #                            datetime.now().year == 2017 and
            #                            datetime.now().month == 12 and
            #                            datetime.now().day >= 12 else [])
            #             }))

    start_checking(vk_api.VkTools(vk_group_session).get_all('messages.getDialogs', 200)['items'])
    q.join()
