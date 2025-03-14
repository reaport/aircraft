import redis.asyncio as redis
from typing import AsyncGenerator, Optional
from fastapi import FastAPI
from contextlib import asynccontextmanager

from config.settings import settings

# Хранилище для клиента Redis
class RedisStore:
    client: Optional[redis.Redis] = None
    
    @classmethod
    async def init_redis(cls):
        """Инициализация клиента Redis при запуске приложения"""
        cls.client = redis.from_url(
            settings.redis_url,
            decode_responses=True
        )
        
    @classmethod
    async def close_redis(cls):
        """Закрытие клиента Redis при остановке приложения"""
        if cls.client:
            await cls.client.close()
            cls.client = None

# Функция для получения клиента Redis в зависимостях
async def get_redis_client() -> AsyncGenerator[redis.Redis, None]:
    """
    Асинхронный генератор для предоставления экземпляра Redis-клиента.
    Используется как зависимость FastAPI.
    
    Пример использования:
        @app.get("/")
        async def read_item(redis: Annotated[redis.Redis, Depends(get_redis_client)]):
            value = await redis.get("my_key")
            return {"value": value}
    """
    if RedisStore.client is None:
        # Обычно это не должно происходить, если приложение корректно инициализировано
        # Но на всякий случай создаем клиента
        await RedisStore.init_redis()
        
    # Предоставляем клиента вызывающему коду
    assert RedisStore.client is not None
    yield RedisStore.client

# Асинхронный контекстный менеджер для управления жизненным циклом Redis
@asynccontextmanager
async def redis_lifespan(app: FastAPI):
    """
    Асинхронный контекстный менеджер для управления жизненным циклом Redis.
    Используется в параметре lifespan при создании FastAPI-приложения.
    
    Пример использования:
        app = FastAPI(lifespan=redis_lifespan)
    """
    # Инициализируем Redis при запуске приложения
    await RedisStore.init_redis()
    try:
        # Передаем управление приложению
        yield
    finally:
        # Закрываем соединение при завершении работы приложения
        await RedisStore.close_redis() 