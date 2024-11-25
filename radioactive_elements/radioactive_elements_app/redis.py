import redis
from radioactive_elements import settings
session_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)