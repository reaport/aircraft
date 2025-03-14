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
        logger.info(f"Генерация случайного самолета для рейса {flight_id}, модель={model or 'случайная'}")
        
        # Если модель не указана, выбираем случайную из конфигурации
        available_models = list(aircraft_config.aircraft.keys())
        if not model:
            if not available_models:
                logger.error("В конфигурации не найдены модели самолетов")
                raise ValueError("В конфигурации не найдены модели самолетов")
            model = random.choice(available_models)
            logger.info(f"Выбрана случайная модель: {model}")
        elif model not in available_models:
            logger.error(f"Модель самолета '{model}' не найдена в конфигурации")
            raise ValueError(f"Модель самолета '{model}' не найдена в конфигурации")
            
        # Получаем конфигурационные данные для этой модели
        config_data = aircraft_config.aircraft[model]
        logger.debug(f"Получены конфигурационные данные для модели {model}")
        
        # Генерируем случайное количество пассажиров и вес багажа
        passenger_capacity = config_data.passenger_capacity
        baggage_capacity_kg = config_data.baggage_capacity_kg
        water_capacity = config_data.water_capacity
        fuel_capacity = config_data.fuel_capacity
        
        actual_passengers = random.randint(0, passenger_capacity)
        actual_baggage_kg = random.randint(0, baggage_capacity_kg)
        actual_water_kg = random.randint(0, water_capacity)
        actual_fuel_kg = random.randint(0, fuel_capacity)
        
        logger.debug(f"Сгенерированы данные: passengers={actual_passengers}/{passenger_capacity}, " +
                     f"baggage={actual_baggage_kg}/{baggage_capacity_kg}, " +
                     f"water={actual_water_kg}/{water_capacity}, " +
                     f"fuel={actual_fuel_kg}/{fuel_capacity}")
        
        # Создаем данные инстанса
        aircraft_data = {
            "model": model,
            "flight_id": flight_id,
            "baggage_capacity_kg": baggage_capacity_kg,
            "passenger_capacity": passenger_capacity,
            "water_capacity": water_capacity,
            "fuel_capacity": fuel_capacity,
            "actual_passengers": actual_passengers,
            "actual_baggage_kg": actual_baggage_kg,
            "actual_water_kg": actual_water_kg,
            "actual_fuel_kg": actual_fuel_kg
        }
        
        # Создаем инстанс самолета (без ID)
        aircraft = AircraftInstance(**aircraft_data)
        
        # Логируем данные перед сохранением
        logger.info(f"Сохранение инстанса самолета: flight_id={flight_id}, model={model}")
        
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
        logger.info(f"Получение самолета по ID рейса: {flight_id}")
        
        # Если нет маппинга, пробуем получить напрямую по flight_id
        flight_key = f"flight:{flight_id}"
        data = await self.redis.get(flight_key)
        
        if not data:
            logger.warning(f"Самолет для рейса {flight_id} не найден")
            raise HTTPException(status_code=404, detail=f"Самолет для рейса {flight_id} не найден")
        
        aircraft = AircraftInstance.model_validate_json(data)
        logger.info(f"Найден самолет для рейса {flight_id}: model={aircraft.model}, id={aircraft.id or 'не назначен'}")
        return aircraft
    
    async def set_aircraft_id(self, flight_id: str, aircraft_id: str) -> AircraftInstance:
        """
        Устанавливает ID для инстанса самолета и сохраняет его в Redis
        
        Args:
            flight_id: ID рейса самолета
            aircraft_id: ID для установки
            
        Returns:
            AircraftInstance: Обновленный инстанс самолета с установленным ID
        """
        logger.info(f"Установка ID самолета: flight_id={flight_id}, aircraft_id={aircraft_id}")
        
        # Получаем инстанс по flight_id
        aircraft = await self.get_by_flight_id(flight_id)
        
        try:
            # Проверяем, не существует ли уже самолет с таким ID
            existing = await self.get_by_id(aircraft_id)
            if existing:
                logger.error(f"Самолет с ID {aircraft_id} уже существует")
                raise HTTPException(status_code=400, detail=f"Самолет с ID {aircraft_id} уже существует")
        except HTTPException as e:
            if e.status_code != 404:
                # Если ошибка не "не найден", то пробрасываем дальше
                raise

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
        logger.info(f"Получение самолета по ID: {aircraft_id}")
        
        # Сначала проверяем маппинг aircraft_id -> flight_id
        flight_id = await self.redis.get(f"aircraft_to_flight:{aircraft_id}")
        
        if not flight_id:
            logger.warning(f"Маппинг aircraft_id -> flight_id для {aircraft_id} не найден")
            raise HTTPException(status_code=404, detail=f"Маппинг aircraft_id -> flight_id для {aircraft_id} не найден")
        
        flight_id_str = flight_id.decode('utf-8') if isinstance(flight_id, bytes) else flight_id
        logger.info(f"Найден маппинг aircraft_id -> flight_id: {aircraft_id} -> {flight_id_str}")
        
        # Ищем по flight_id
        flight_key = f"flight:{flight_id_str}"
        data = await self.redis.get(flight_key)
        
        if not data:
            logger.warning(f"Маппинг найден, но данные по flight_id {flight_id_str} не найдены")
            raise HTTPException(status_code=404, detail=f"Данные по flight_id {flight_id_str} не найдены")
        
        aircraft = AircraftInstance.model_validate_json(data)
        logger.info(f"Найден самолет: ID={aircraft_id}, model={aircraft.model}, flight_id={aircraft.flight_id}")
        return aircraft
    
    async def update(self, aircraft: AircraftInstance) -> AircraftInstance:
        """
        Обновляет инстанс самолета в Redis
        
        Args:
            aircraft: Инстанс самолета для обновления (должен содержать id)
            
        Returns:
            AircraftInstance: Обновленный инстанс самолета
        """
        logger.info(f"Обновление самолета: ID={aircraft.id}, model={aircraft.model}")
        
        # Проверяем наличие ID самолета
        if not aircraft.id:
            logger.error("ID самолета не указан при попытке обновления")
            raise HTTPException(status_code=400, detail="ID самолета не указан")
            
        # Проверяем, есть ли маппинг для ID самолета
        flight_id = await self.redis.get(f"aircraft_to_flight:{aircraft.id}")
        if not flight_id:
            logger.warning(f"Маппинг aircraft_id -> flight_id для {aircraft.id} не найден")
            raise HTTPException(status_code=404, detail=f"Маппинг aircraft_id -> flight_id для {aircraft.id} не найден")
        
        # Получаем ID рейса из маппинга
        flight_id_str = flight_id.decode('utf-8') if isinstance(flight_id, bytes) else flight_id
        logger.info(f"Найден маппинг aircraft_id -> flight_id: {aircraft.id} -> {flight_id_str}")
        
        # Проверяем, существует ли рейс с таким ID
        flight_key = f"flight:{flight_id_str}"
        data = await self.redis.get(flight_key)
        if not data:
            logger.warning(f"Данные по flight_id {flight_id_str} не найдены")
            raise HTTPException(status_code=404, detail=f"Данные по flight_id {flight_id_str} не найдены")
        
        # Логируем данные перед сохранением
        logger.debug(f"Сохранение обновленных данных: {aircraft.model_dump_json()}")
        
        # Сохраняем обновленные данные по ключу flight_id
        await self.redis.set(flight_key, aircraft.model_dump_json())
        
        logger.info(f"Обновлены данные самолета с ID {aircraft.id} для рейса {flight_id_str}")
        return aircraft
    
    async def delete(self, aircraft_id: str) -> bool:
        """
        Удаляет инстанс самолета из Redis
        
        Args:
            aircraft_id: ID самолета для удаления
            
        Returns:
            bool: True если удаление успешно, иначе False
        """
        logger.info(f"Запрос на удаление самолета: ID={aircraft_id}")
        
        try:
            # Получаем маппинг aircraft_id -> flight_id
            flight_id = await self.redis.get(f"aircraft_to_flight:{aircraft_id}")
            if not flight_id:
                logger.warning(f"Маппинг aircraft_id -> flight_id для {aircraft_id} не найден при попытке удаления")
                return False
            
            # Преобразуем bytes в строку, если необходимо
            flight_id_str = flight_id.decode('utf-8') if isinstance(flight_id, bytes) else flight_id
            logger.info(f"Найден маппинг aircraft_id -> flight_id: {aircraft_id} -> {flight_id_str} для удаления")
            
            # Удаляем данные по ключу flight:{flight_id}
            flight_key = f"flight:{flight_id_str}"
            flight_deleted = await self.redis.delete(flight_key)
            
            # Удаляем маппинг aircraft_id -> flight_id
            mapping_deleted = await self.redis.delete(f"aircraft_to_flight:{aircraft_id}")
            
            # Удаляем flight_id из набора всех рейсов
            await self.redis.srem("flights:all", flight_id_str)
            
            logger.info(f"Удален инстанс самолета с ID {aircraft_id} для рейса {flight_id_str}. Статус: данные={flight_deleted}, маппинг={mapping_deleted}")
            
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
        logger.info(f"Запрос на обновление количества пассажиров: aircraft_id={aircraft_id}, count={count}")
        
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            logger.info(f"Текущее количество пассажиров: {current.actual_passengers}/{current.passenger_capacity}")
            
            # Применяем обновление через метод модели
            current.update_passengers(count)
            logger.info(f"Новое количество пассажиров: {current.actual_passengers}/{current.passenger_capacity}")
            
            # Сохраняем обновленный инстанс
            updated = await self.update(current)
            logger.info(f"Количество пассажиров успешно обновлено: aircraft_id={aircraft_id}, count={count}")
            return updated
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации при обновлении количества пассажиров: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            logger.error(f"HTTP ошибка при обновлении количества пассажиров: {e.status_code} - {e.detail}")
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
        logger.info(f"Запрос на обновление веса багажа: aircraft_id={aircraft_id}, weight={weight}")
        
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            logger.info(f"Текущий вес багажа: {current.actual_baggage_kg}/{current.baggage_capacity_kg}")
            
            # Применяем обновление через метод модели
            current.update_baggage(weight)
            logger.info(f"Новый вес багажа: {current.actual_baggage_kg}/{current.baggage_capacity_kg}")
            
            # Сохраняем обновленный инстанс
            updated = await self.update(current)
            logger.info(f"Вес багажа успешно обновлен: aircraft_id={aircraft_id}, weight={weight}")
            return updated
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации при обновлении веса багажа: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            logger.error(f"HTTP ошибка при обновлении веса багажа: {e.status_code} - {e.detail}")
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
        logger.info(f"Запрос на обновление веса воды: aircraft_id={aircraft_id}, weight={weight}")
        
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            logger.info(f"Текущий вес воды: {current.actual_water_kg}/{current.water_capacity}")
            
            # Применяем обновление через метод модели
            current.update_water(weight)
            logger.info(f"Новый вес воды: {current.actual_water_kg}/{current.water_capacity}")
            
            # Сохраняем обновленный инстанс
            updated = await self.update(current)
            logger.info(f"Вес воды успешно обновлен: aircraft_id={aircraft_id}, weight={weight}")
            return updated
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации при обновлении веса воды: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            logger.error(f"HTTP ошибка при обновлении веса воды: {e.status_code} - {e.detail}")
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
        logger.info(f"Запрос на обновление веса топлива: aircraft_id={aircraft_id}, weight={weight}")
        
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            logger.info(f"Текущий вес топлива: {current.actual_fuel_kg}/{current.fuel_capacity}")
            
            # Применяем обновление через метод модели
            current.update_fuel(weight)
            logger.info(f"Новый вес топлива: {current.actual_fuel_kg}/{current.fuel_capacity}")
            
            # Сохраняем обновленный инстанс
            updated = await self.update(current)
            logger.info(f"Вес топлива успешно обновлен: aircraft_id={aircraft_id}, weight={weight}")
            return updated
        except ValueError as e:
            # Перехватываем ошибки валидации из модели
            logger.error(f"Ошибка валидации при обновлении веса топлива: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException as e:
            logger.error(f"HTTP ошибка при обновлении веса топлива: {e.status_code} - {e.detail}")
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
        logger.info(f"Запрос на обновление ID узла: aircraft_id={aircraft_id}, node_id={node_id}")
        
        try:
            # Получаем текущий инстанс
            current = await self.get_by_id(aircraft_id)
            logger.info(f"Текущий ID узла: {current.node_id}")
            
            # Применяем обновление через метод модели
            current.update_node_id(node_id)
            logger.info(f"Новый ID узла: {current.node_id}")
            
            # Сохраняем обновленный инстанс
            updated = await self.update(current)
            logger.info(f"ID узла успешно обновлен: aircraft_id={aircraft_id}, node_id={node_id}")
            return updated
        except HTTPException as e:
            logger.error(f"HTTP ошибка при обновлении ID узла: {e.status_code} - {e.detail}")
            raise e
        except Exception as e:
            logger.error(f"Ошибка при обновлении ID узла: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Ошибка при обновлении ID узла: {str(e)}")