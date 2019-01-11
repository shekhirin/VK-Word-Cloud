# from collections import Counter
# from datetime import datetime
import datetime
from queue import Queue
from threading import Thread

import vk_api

from vk_wc import send_cloud, worker
import config

vk_group_session = vk_api.VkApi(token=config.vk_community_token)
vk_group = vk_group_session.get_api()
vk_session = vk_api.VkApi(token=config.vk_user_token)
vk = vk_session.get_api()

if __name__ == '__main__':
    q = Queue()
    for i in range(10):
        t = Thread(target=worker, args=(q, True))
        t.start()


    def start_checking(conversations):
        # users = [x['conversation']['peer']['id'] for x in conversations if
        #          'unread_count' in x['conversation']
        #          and x['last_message']['from_id'] == x['conversation']['peer']['id']
        #          and x['conversation']['can_write']['allowed']]
        users = vk_group.users.get(user_ids=','.join([str(x['conversation']['peer']['id']) for x in conversations if
                                                      (datetime.datetime.now() - datetime.datetime.fromtimestamp(
                                                          x['last_message']['date'])).days > 30]),
                                   fields='sex,birthdate')
        users = [x['id'] for x in users]
        #
        # users = [53448, 984706, 5944, 143978, 877944]
        #
        # mutual = []
        # pairs = []
        # for user in users:
        #     for target in users:
        #         if user != target and (user, target) not in pairs:
        #             mutual.extend(vk.friends.getMutual(source_uid=user, target_uid=target))
        #             pairs.append((user, target))
        #             pairs.append((target, user))
        #
        # users = list(dict(list(Counter(mutual).most_common())[:30]).keys()) + users
        # print(users)
        # print(len(users))

        for user in users:
            q.put((send_cloud, (user, 'облако', True), {}))


    start_checking(vk_api.VkTools(vk_group_session).get_all('messages.getConversations', 200)['items'])
    q.join()
