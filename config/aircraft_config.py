from typing import List, Dict
from enum import Enum
from pydantic import BaseModel, Field

from config.settings import settings

class SeatClass(str, Enum):
    FIRST = "first"
    BUSINESS = "business"
    PREMIUM_ECONOMY = "premium_economy"
    ECONOMY = "economy"

class Seat(BaseModel):
    """Модель места в самолете"""
    seat_number: str = Field(..., alias="seatNumber")
    seat_class: SeatClass = Field(..., alias="seatClass")

class Aircraft(BaseModel):
    """Модель самолета"""
    model: str
    baggage_capacity_kg: int = Field(..., alias="baggageCapacityKg")
    passenger_capacity: int = Field(..., alias="passengerCapacity")
    water_capacity: int = Field(..., alias="waterCapacity")
    fuel_capacity: int = Field(..., alias="fuelCapacity")
    seats: List[Seat]

class AircraftConfig(BaseModel):
    """Корневая модель конфигурации самолетов"""
    aircraft: Dict[str, Aircraft]

    @classmethod
    def from_config(cls, config_path: str) -> "AircraftConfig":
        """Загрузка конфигурации из JSON файла"""
        import json
        with open(config_path, "r") as f:
            data = json.load(f)
            
        # Если в данных старый формат (список), преобразуем его в новый (словарь)
        if isinstance(data.get("aircraft"), list):
            aircraft_list = data["aircraft"]
            data["aircraft"] = {item["model"]: item for item in aircraft_list}
            
        return cls.model_validate(data)
    
aircraft_config = AircraftConfig.from_config(settings.AIRCRAFT_CONFIG_PATH)
