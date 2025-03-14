from typing import Annotated
from fastapi import Depends

import redis.asyncio as redis

from db.redis import get_redis_client
from services.aircraft_service import AircraftService

async def get_aircraft_service(
    redis_client: Annotated[redis.Redis, Depends(get_redis_client)]
) -> AircraftService:
    """
    Фабрика для создания AircraftService.
    Используется как зависимость в FastAPI.
    
    Args:
        redis_client: Клиент Redis
        
    Returns:
        AircraftService: Сервис для работы с инстансами самолетов
    """
    return AircraftService(redis_client)

# Аннотированная зависимость для удобного использования
AircraftServiceDep = Annotated[AircraftService, Depends(get_aircraft_service)] 