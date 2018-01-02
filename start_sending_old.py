from collections import Counter
from datetime import datetime
from queue import Queue
from threading import Thread

import vk_api
from tqdm import tqdm

from vk_wc import send_cloud, worker
import config

vk_group_session = vk_api.VkApi(token=config.vk_community_token)
vk_group = vk_group_session.get_api()
vk_session = vk_api.VkApi(token=config.vk_user_token)
vk = vk_session.get_api()

if __name__ == '__main__':
    q = Queue()
    for i in range(10):
        t = Thread(target=worker, args=(q,))
        t.setDaemon(True)
        t.start()


    def start_checking(dialogs):
        # users = vk_group.users.get(user_ids=','.join([str(x['message']['user_id']) for x in dialogs]),
        #                            fields='sex,birthdate')
        # users = [x['id'] for x in users if 'bdate' in x
        #            and len(x['bdate'].split('.')) == 3
        #            and int(x['bdate'].split('.')[2]) <= 1990]

        users = [53448, 984706, 5944, 143978, 877944]

        mutual = []
        pairs = []
        for user in users:
            for target in users:
                if user != target and (user, target) not in pairs:
                    mutual.extend(vk.friends.getMutual(source_uid=user, target_uid=target))
                    pairs.append((user, target))
                    pairs.append((target, user))

        users = list(dict(list(Counter(mutual).most_common())[:30]).keys()) + users
        print(users)
        print(len(users))

        for user in tqdm(users):
            q.put((send_cloud, (user, 'облако', False), {}))
        return

        for i, dialog in enumerate(dialogs):
            if dialog['message']['user_id'] in users:
                q.put((vk_group.messages.send, (),
                       {
                           'user_id': dialog['message']['user_id'],
                           'message': 'Привет, Новый Год уже на носу, поэтому мы с командой придумали новую штуку – '
                                      'поздравления для взрослых и детей от Дедушки Мороза.\n'
                                      'Выглядит круто, дети под впечатлением. Подписчикам облака скидка 20%, то есть '
                                      'всего за 400 рублей можем сделать тебе такое видео поздравление. '
                                      'Если что непонятно, пиши :)',
                           'attachment': 'wall-98703606_325'
                       }))

        return
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
