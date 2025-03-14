from typing import Optional
from pydantic import BaseModel


class AircraftInstance(BaseModel):
    """Модель инстанса самолета"""
    id: Optional[str] = None
    model: str  # Модель самолета, соответствующая ключу в конфигурации
    flight_id: Optional[str] = None  # Идентификатор рейса
    node_id: Optional[str] = None  # Идентификатор узла (для распределенных систем)
    
    # Поля из конфигурации Aircraft
    baggage_capacity_kg: int  # Вместимость багажа в кг
    passenger_capacity: int   # Вместимость пассажиров
    water_capacity: int  # Вместимость воды в кг
    fuel_capacity: int  # Вместимость топлива в кг
    
    actual_passengers: int = 0  # Фактическое количество пассажиров
    actual_baggage_kg: int = 0  # Фактический вес багажа в кг
    actual_water_kg: int = 0  # Фактический вес воды в кг
    actual_fuel_kg: int = 0  # Фактический вес топлива в кг
    
    def update_passengers(self, count: int):
        """Обновляет количество пассажиров"""
        if count > self.passenger_capacity:
            raise ValueError(f"Количество пассажиров ({count}) превышает вместимость ({self.passenger_capacity})")
        self.actual_passengers = count
    
    def update_baggage(self, weight: int) -> None:
        """Обновляет вес багажа"""
        if weight > self.baggage_capacity_kg:
            raise ValueError(f"Вес багажа ({weight} кг) превышает вместимость ({self.baggage_capacity_kg} кг)")
        self.actual_baggage_kg = weight
    
    def update_water(self, weight: int) -> None:
        """Обновляет вес воды"""
        if weight > self.water_capacity:
            raise ValueError(f"Вес воды ({weight} кг) превышает вместимость ({self.water_capacity} кг)")
        self.actual_water_kg = weight
    
    def update_fuel(self, weight: int) -> None:
        """Обновляет вес топлива"""
        if weight > self.fuel_capacity:
            raise ValueError(f"Вес топлива ({weight} кг) превышает вместимость ({self.fuel_capacity} кг)")
        self.actual_fuel_kg = weight
    
    def update_node_id(self, node_id: str) -> None:
        """Обновляет ID узла"""
        self.node_id = node_id
