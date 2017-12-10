import os


vk_community_token = os.environ.get('vk_community_token')
vk_user_token = os.environ.get('vk_user_token')
album_id = os.environ.get('album_id')
group_id = os.environ.get('group_id')
mongo_host = os.environ.get('MONGODB_URI', None)
mongo_db = os.environ.get('MONGODB_DB', 'wordcloud')
