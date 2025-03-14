import logging
import random
from typing import Optional

from fastapi import HTTPException
import redis.asyncio as redis

from models.aircraft_instance import AircraftInstance
from config import aircraft_config

logger = logging.getLogger("uvicorn")

class AircraftService:
    """Сервис для работы с инстансами самолетов в Redis"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def generate_random(self, flight_id: str, model: Optional[str] = None) -> AircraftInstance:
        """
        Создает новый инстанс самолета со случайными данными и сохраняет по flight_id
        
        Args:
            flight_id: ID рейса для создаваемого инстанса
            model: Опциональная модель самолета, если не указана - выбирается случайная из конфигурации
            
        Returns:
            AircraftInstance: Созданный инстанс самолета без ID (будет установлен позже)
        """
        # Если модель не указана, выбираем случайную из конфигурации
        available_models = list(aircraft_config.aircraft.keys())
        if not model:
            if not available_models:
                raise ValueError("В конфигурации не найдены модели самолетов")
            model = random.choice(available_models)
        elif model not in available_models:
            raise ValueError(f"Модель самолета '{model}' не найдена в конфигурации")
            
        # Получаем конфигурационные данные для этой модели
        config_data = aircraft_config.aircraft[model]
        
        # Генерируем случайное количество пассажиров и вес багажа
        passenger_capacity = config_data.passenger_capacity
        baggage_capacity_kg = config_data.baggage_capacity_kg
        water_capacity = config_data.water_capacity
        fuel_capacity = config_data.fuel_capacity
        
        actual_passengers = random.randint(0, passenger_capacity)
        actual_baggage_kg = random.randint(0, baggage_capacity_kg)
        actual_water_kg = random.randint(0, water_capacity)
        actual_fuel_kg = random.randint(0, fuel_capacity)
        
        # Создаем данные инстанса
        aircraft_data = {
            "model": model,
            "flight_id": flight_id,
            "baggage_capacity_kg": baggage_capacity_kg,
            "passenger_capacity": passenger_capacity,
            "actual_passengers": actual_passengers,
            "actual_baggage_kg": actual_baggage_kg,
            "actual_water_kg": actual_water_kg,
            "actual_fuel_kg": actual_fuel_kg
        }
        
        # Создаем инстанс самолета (без ID)
        aircraft = AircraftInstance(**aircraft_data)
        
        # Сохраняем в Redis по ключу flight_id
        flight_key = f"flight:{flight_id}"
        await self.redis.set(flight_key, aircraft.model_dump_json())
        
        # Добавляем flight_id в набор всех рейсов
        await self.redis.sadd("flights:all", flight_id)
        
        logger.info(f"Создан и сохранен случайный инстанс самолета: {aircraft.model} для рейса {aircraft.flight_id} (без ID)")
        return aircraft
    
    async def get_by_flight_id(self, flight_id: str) -> Optional[AircraftInstance]:
        """
        Получает инстанс самолета по ID рейса
        
        Args:
            flight_id: ID рейса
            
        Returns:
            Optional[AircraftInstance]: Инстанс самолета или None, если не найден
        """
        
        # Если нет маппинга, пробуем получить напрямую по flight_id
        flight_key = f"flight:{flight_id}"
        data = await self.redis.get(flight_key)
        
        if not data:
            logger.warning(f"Самолет для рейса {flight_id} не найден")
            raise HTTPException(status_code=404, detail=f"Самолет для рейса {flight_id} не найден")
        
        return AircraftInstance.model_validate_json(data)
    
    async def set_aircraft_id(self, flight_id: str, aircraft_id: str) -> AircraftInstance:
        """
        Устанавливает ID для инстанса самолета и сохраняет его в Redis
        
        Args:
            flight_id: ID рейса самолета
            aircraft_id: ID для установки
            
        Returns:
            AircraftInstance: Обновленный инстанс самолета с установленным ID
        """
        # Получаем инстанс по flight_id
        aircraft = await self.get_by_flight_id(flight_id)
        
        # Проверяем, не существует ли уже самолет с таким ID
        existing = await self.get_by_id(aircraft_id)
        if existing:
            raise HTTPException(status_code=400, detail=f"Самолет с ID {aircraft_id} уже существует")
        
        # Устанавливаем ID
        aircraft.id = aircraft_id
        # Сохраняем в Redis по новому ключу flight_id
        flight_key = f"flight:{flight_id}"
        # Обновляем объект с установленным ID
        await self.redis.set(flight_key, aircraft.model_dump_json())
        
        # Создаем маппинги для быстрого поиска
        # aircraft_id -> flight_id
        await self.redis.set(f"aircraft_to_flight:{aircraft_id}", flight_id)
        
        logger.info(f"Установлен ID {aircraft_id} для инстанса самолета: {aircraft.model} для рейса {flight_id}")
        return aircraft
    
    async def get_by_id(self, aircraft_id: str) -> Optional[AircraftInstance]:
        """
        Получает инстанс самолета по ID
        
        Args:
            aircraft_id: ID самолета
            
        Returns:
            Optional[AircraftInstance]: Инстанс самолета или None, если не найден
        """
        # Сначала проверяем маппинг aircraft_id -> flight_id
        flight_id = await self.redis.get(f"aircraft_to_flight:{aircraft_id}")
        
        if not flight_id:
            logger.warning(f"Маппинг aircraft_id -> flight_id для {aircraft_id} не найден")
            raise HTTPException(status_code=404, detail=f"Маппинг aircraft_id -> flight_id для {aircraft_id} не найден")
        

        logger.info(f"Найден маппинг aircraft_id -> flight_id: {aircraft_id} -> {flight_id}")
        
        # Ищем по flight_id
        flight_key = f"flight:{flight_id}"
        data = await self.redis.get(flight_key)
        
        if not data:
            logger.warning(f"Маппинг найден, но данные по flight_id {flight_id} не найдены")
            raise HTTPException(status_code=404, detail=f"Данные по flight_id {flight_id} не найдены")
        return AircraftInstance.model_validate_json(data)
    
    async def update(self, aircraft: AircraftInstance) -> AircraftInstance:
        """
        Обновляет инстанс самолета в Redis
        
        Args:
            aircraft: Инстанс самолета для обновления (должен содержать id)
            
        Returns:
            AircraftInstance: Обновленный инстанс самолета
        """
        # Проверяем наличие ID самолета
        if not aircraft.id:
            raise HTTPException(status_code=400, detail="ID самолета не указан")
            
        # Проверяем, есть ли маппинг для ID самолета
        flight_id = await self.redis.get(f"aircraft_to_flight:{aircraft.id}")
        if not flight_id:
            logger.warning(f"Маппинг aircraft_id -> flight_id для {aircraft.id} не найден")
            raise HTTPException(status_code=404, detail=f"Маппинг aircraft_id -> flight_id для {aircraft.id} не найден")
	
        logger.info(f"Найден маппинг aircraft_id -> flight_id: {aircraft.id} -> {flight_id}")
        
        # Проверяем, существует ли рейс с таким ID
        flight_key = f"flight:{flight_id}"
        data = await self.redis.get(flight_key)
        if not data:
            logger.warning(f"Данные по flight_id {flight_id} не найдены")
            raise HTTPException(status_code=404, detail=f"Данные по flight_id {flight_id} не найдены")
        
        # Сохраняем обновленные данные по ключу flight_id
        await self.redis.set(flight_key, aircraft.model_dump_json())
        
        logger.info(f"Обновлены данные самолета с ID {aircraft.id} для рейса {flight_id}")
        return aircraft
    
    async def delete(self, aircraft_id: str) -> bool:
        """
        Удаляет инстанс самолета из Redis
        
        Args:
            aircraft_id: ID самолета для удаления
            
        Returns:
            bool: True если удаление успешно, иначе False
        """
        try:
            # Получаем маппинг aircraft_id -> flight_id
            flight_id = await self.redis.get(f"aircraft_to_flight:{aircraft_id}")
            if not flight_id:
                logger.warning(f"Маппинг aircraft_id -> flight_id для {aircraft_id} не найден при попытке удаления")
                return False
            
            logger.info(f"Найден маппинг aircraft_id -> flight_id: {aircraft_id} -> {flight_id} для удаления")
            
            # Удаляем данные по ключу flight:{flight_id}
            flight_key = f"flight:{flight_id}"
            flight_deleted = await self.redis.delete(flight_key)
            
            # Удаляем маппинг aircraft_id -> flight_id
            mapping_deleted = await self.redis.delete(f"aircraft_to_flight:{aircraft_id}")
            
            # Удаляем flight_id из набора всех рейсов
            await self.redis.srem("flights:all", flight_id)
            
            logger.info(f"Удален инстанс самолета с ID {aircraft_id} для рейса {flight_id}. Статус: данные={flight_deleted}, маппинг={mapping_deleted}")
            
            # Успешно удалено, если хотя бы одна запись была удалена
            return flight_deleted > 0 or mapping_deleted > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении самолета с ID {aircraft_id}: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Ошибка при удалении самолета: {str(e)}"
            )
    
    async def update_passengers(self, aircraft_id: str, count: int) -> Optional[AircraftInstance]:
        """
        Обновляет количество пассажиров
        
        Args:
            aircraft_id: ID самолета
            count: Новое количество пассажиров
            
        Returns:
            Optional[AircraftInstance]: Обновленный инстанс самолета или None, если не найден
        """
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            
            # Применяем обновление через метод модели
            current.update_passengers(count)
            
            # Сохраняем обновленный инстанс
            return await self.update(current)
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при обновлении количества пассажиров: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при обновлении количества пассажиров: {str(e)}")
    
    async def update_baggage(self, aircraft_id: str, weight: int) -> Optional[AircraftInstance]:
        """
        Обновляет вес багажа
        
        Args:
            aircraft_id: ID самолета
            weight: Новый вес багажа в кг
            
        Returns:
            Optional[AircraftInstance]: Обновленный инстанс самолета или None, если не найден
        """
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            
            # Применяем обновление через метод модели
            current.update_baggage(weight)
            
            # Сохраняем обновленный инстанс
            return await self.update(current)
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при обновлении веса багажа: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при обновлении веса багажа: {str(e)}")
            
    async def update_water(self, aircraft_id: str, weight: int) -> Optional[AircraftInstance]:
        """
        Обновляет вес воды
        
        Args:
            aircraft_id: ID самолета
            weight: Новый вес воды в кг
            
        Returns:
            Optional[AircraftInstance]: Обновленный инстанс самолета или None, если не найден
        """
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            
            # Применяем обновление через метод модели
            current.update_water(weight)
            
            # Сохраняем обновленный инстанс
            return await self.update(current)
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при обновлении веса воды: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при обновлении веса воды: {str(e)}")
            
    async def update_fuel(self, aircraft_id: str, weight: int) -> Optional[AircraftInstance]:
        """
        Обновляет вес топлива
        
        Args:
            aircraft_id: ID самолета
            weight: Новый вес топлива в кг
            
        Returns:
            Optional[AircraftInstance]: Обновленный инстанс самолета или None, если не найден
        """
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            
            # Применяем обновление через метод модели
            current.update_fuel(weight)
            
            # Сохраняем обновленный инстанс
            return await self.update(current)
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при обновлении веса топлива: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при обновлении веса топлива: {str(e)}") 
        
    async def update_node_id(self, aircraft_id: str, node_id: str) -> Optional[AircraftInstance]:
        """
        Обновляет ID узла для инстанса самолета
        
        Args:
            aircraft_id: ID самолета
            node_id: ID узла
            
        Returns:
            Optional[AircraftInstance]: Обновленный инстанс самолета или None, если не найден
        """
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            
            # Применяем обновление через метод модели
            current.update_node_id(node_id)
            
            # Сохраняем обновленный инстанс
            return await self.update(current)
        except HTTPException as e:
            raise e
        except Exception as e:
            logger.error(f"Ошибка при обновлении ID узла: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при обновлении ID узла: {str(e)}")