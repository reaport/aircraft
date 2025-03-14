from pydantic import BaseModel
from typing import List

from config.aircraft_config import Seat

class GenerateRequest(BaseModel):
	flightId: str
	
class GenerateResponse(BaseModel):
	flightId: str
	aircraft_model: str
	passengers_count: int
	baggage_kg: int
	water_kg: int
	fuel_kg: int
	max_passengers: int
	max_baggage_kg: int
	max_water_kg: int
	max_fuel_kg: int
	seats: List[Seat]
	
class LandingResponse(BaseModel):
	aircraft_id: str