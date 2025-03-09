import os
import redis

redis_host = os.getenv("REDIS_HOST", "localhost")  # Usa la variable de entorno
redis_port = int(os.getenv("REDIS_PORT", 6379))     # Usa la variable de entorno

redis_client = redis.Redis(host=redis_host, port=redis_port)
