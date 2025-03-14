from contextlib import asynccontextmanager
from fastapi import FastAPI

from db.redis import redis_lifespan

@asynccontextmanager
async def global_lifespan(app: FastAPI):
    """
    Глобальный асинхронный контекстный менеджер для управления 
    жизненным циклом всех ресурсов приложения.
    
    Этот менеджер вызывает все другие контекстные менеджеры lifespan
    для различных компонентов приложения.
    """
    # Создаем несколько контекстных менеджеров
    async with redis_lifespan(app):
        # Здесь можно добавить другие контекстные менеджеры
        # когда они появятся в приложении
        # async with other_component_lifespan(app):
        
        # Передаем управление приложению
        yield 