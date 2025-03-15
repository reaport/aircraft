from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
import logging
from typing import Optional

from schemas.generate import GenerateRequest, GenerateResponse, LandingResponse
from services import AircraftServiceDep
from config import aircraft_config
from gateways.ground_control import GroundControlGateway
from gateways.orch import OrchestratorGateway
from models.aircraft_instance import AircraftInstance

router = APIRouter(
    tags=["aircraft"]
)

# Получаем логгер
logger = logging.getLogger("uvicorn")

# Модели запросов для новых эндпоинтов
class PassengerUpdate(BaseModel):
    passengers: int
    
class BaggageUpdate(BaseModel):
    baggage: int

class WaterUpdate(BaseModel):
    water_amount: int
    
class FuelUpdate(BaseModel):
    fuel_amount: int

@router.post("/generate", status_code=status.HTTP_201_CREATED, response_model=GenerateResponse)
async def generate_aircraft(
    service: AircraftServiceDep,
    request: GenerateRequest
):
    """
    Создает новый инстанс самолета со случайными данными для указанного рейса
    
    - **flight_id**: ID рейса для создаваемого инстанса
    """
    logger.info(f"Запрос на создание самолета: flight_id={request.flightId}")
    
    try:
        # Создаем инстанс самолета
        aircraft = await service.generate_random(request.flightId)
        
        # Получаем информацию о местах из конфигурации
        config_data = aircraft_config.aircraft.get(aircraft.model)
        if not config_data:
            # Это не должно произойти, но на всякий случай проверяем
            raise ValueError(f"Модель самолета '{aircraft.model}' не найдена в конфигурации")
        
        # Формируем ответ
        response = GenerateResponse(
            flightId=aircraft.flight_id,
            aircraft_model=aircraft.model,
            passengers_count=aircraft.actual_passengers,
            baggage_kg=aircraft.actual_baggage_kg,
            water_kg=aircraft.actual_water_kg,
            fuel_kg=aircraft.actual_fuel_kg,
            max_passengers=aircraft.passenger_capacity,
            max_baggage_kg=aircraft.baggage_capacity_kg,
            max_water_kg=aircraft.water_capacity,
            max_fuel_kg=aircraft.fuel_capacity,
            seats=config_data.seats
        )
        
        logger.info(f"Самолет успешно создан: модель={aircraft.model}, flight_id={aircraft.flight_id}")
        return response
    except ValueError as e:
        logger.error(f"Ошибка при создании самолета: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/{aircraft_id}/passengers", status_code=status.HTTP_204_NO_CONTENT)
async def update_aircraft_passengers(
    aircraft_id: str,
    passenger_data: PassengerUpdate,
    service: AircraftServiceDep
):
    """
    Обновляет количество пассажиров в инстансе самолета
    """
    logger.info(f"Запрос на обновление пассажиров: aircraft_id={aircraft_id}, passengers={passenger_data.passengers}")
    
    try:
        updated_aircraft = await service.update_passengers(aircraft_id, passenger_data.passengers)
        logger.info(f"Пассажиры обновлены: aircraft_id={aircraft_id}, passengers={passenger_data.passengers}")
        return updated_aircraft
    except HTTPException as e:
        logger.error(f"Ошибка HTTP при обновлении пассажиров: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Ошибка при обновлении пассажиров: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
@router.get("/{aircraft_id}/passengers", response_model=PassengerUpdate)
async def get_aircraft_passengers(
    aircraft_id: str,
    service: AircraftServiceDep
):
    """
    Получает количество пассажиров в инстансе самолета
    """
    logger.info(f"Запрос на получение количества пассажиров: aircraft_id={aircraft_id}")
    
    aircraft = await service.get_by_id(aircraft_id)
    if not aircraft:
        logger.warning(f"Самолет с ID {aircraft_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет с ID {aircraft_id} не найден"
        )
    
    logger.info(f"Получено количество пассажиров: aircraft_id={aircraft_id}, passengers={aircraft.actual_passengers}")
    return {"passengers": aircraft.actual_passengers}

@router.patch("/{aircraft_id}/baggage", status_code=status.HTTP_204_NO_CONTENT)
async def update_aircraft_baggage(
    aircraft_id: str,
    baggage_data: BaggageUpdate,
    service: AircraftServiceDep
):
    """
    Обновляет вес багажа в инстансе самолета
    """
    logger.info(f"Запрос на обновление веса багажа: aircraft_id={aircraft_id}, baggage={baggage_data.baggage}")
    
    try:
        updated_aircraft = await service.update_baggage(aircraft_id, baggage_data.baggage)
        logger.info(f"Вес багажа обновлен: aircraft_id={aircraft_id}, baggage={baggage_data.baggage}")
        return updated_aircraft
    except HTTPException as e:
        logger.error(f"Ошибка HTTP при обновлении веса багажа: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Ошибка при обновлении веса багажа: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{aircraft_id}/baggage", response_model=BaggageUpdate)
async def get_aircraft_baggage(
    aircraft_id: str,
    service: AircraftServiceDep
):
    """	
    Получает вес багажа в инстансе самолета
    """
    logger.info(f"Запрос на получение веса багажа: aircraft_id={aircraft_id}")
    
    aircraft = await service.get_by_id(aircraft_id)
    if not aircraft:
        logger.warning(f"Самолет с ID {aircraft_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет с ID {aircraft_id} не найден"
        )
    
    logger.info(f"Получен вес багажа: aircraft_id={aircraft_id}, baggage={aircraft.actual_baggage_kg}")
    return {"baggage": aircraft.actual_baggage_kg}

@router.patch("/{aircraft_id}/water", status_code=status.HTTP_204_NO_CONTENT)
async def update_aircraft_water(
    aircraft_id: str,
    water_data: WaterUpdate,
    service: AircraftServiceDep
):
    """
    Обновляет вес воды в инстансе самолета
    """
    logger.info(f"Запрос на обновление веса воды: aircraft_id={aircraft_id}, water={water_data.water_amount}")
    
    try:
        updated_aircraft = await service.update_water(aircraft_id, water_data.water_amount)
        logger.info(f"Вес воды обновлен: aircraft_id={aircraft_id}, water={water_data.water_amount}")
        return updated_aircraft
    except HTTPException as e:
        logger.error(f"Ошибка HTTP при обновлении веса воды: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Ошибка при обновлении веса воды: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{aircraft_id}/water", response_model=WaterUpdate)
async def get_aircraft_water(
    aircraft_id: str,
    service: AircraftServiceDep
):
    """
    Получает вес воды в инстансе самолета
    """
    logger.info(f"Запрос на получение веса воды: aircraft_id={aircraft_id}")
    
    aircraft = await service.get_by_id(aircraft_id)
    if not aircraft:
        logger.warning(f"Самолет с ID {aircraft_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет с ID {aircraft_id} не найден"
        )
    
    logger.info(f"Получен вес воды: aircraft_id={aircraft_id}, water={aircraft.actual_water_kg}")
    return {"water_amount": aircraft.actual_water_kg}

@router.patch("/{aircraft_id}/fuel", status_code=status.HTTP_204_NO_CONTENT)
async def update_aircraft_fuel(
    aircraft_id: str,
    fuel_data: FuelUpdate,
    service: AircraftServiceDep
):
    """
    Обновляет вес топлива в инстансе самолета
    """
    logger.info(f"Запрос на обновление веса топлива: aircraft_id={aircraft_id}, fuel={fuel_data.fuel_amount}")
    
    try:
        updated_aircraft = await service.update_fuel(aircraft_id, fuel_data.fuel_amount)
        logger.info(f"Вес топлива обновлен: aircraft_id={aircraft_id}, fuel={fuel_data.fuel_amount}")
        return updated_aircraft
    except HTTPException as e:
        logger.error(f"Ошибка HTTP при обновлении веса топлива: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Ошибка при обновлении веса топлива: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{aircraft_id}/fuel", response_model=FuelUpdate)
async def get_aircraft_fuel(
    aircraft_id: str,
    service: AircraftServiceDep
):
    """
    Получает вес топлива в инстансе самолета
    """
    logger.info(f"Запрос на получение веса топлива: aircraft_id={aircraft_id}")
    
    aircraft = await service.get_by_id(aircraft_id)
    if not aircraft:
        logger.warning(f"Самолет с ID {aircraft_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет с ID {aircraft_id} не найден"
        )
    
    logger.info(f"Получен вес топлива: aircraft_id={aircraft_id}, fuel={aircraft.actual_fuel_kg}")
    return {"fuel_amount": aircraft.actual_fuel_kg}

@router.post("/{flight_id}/landing", status_code=status.HTTP_200_OK, response_model=LandingResponse)
async def landing_aircraft(
    flight_id: str,
    service: AircraftServiceDep,
    ground_control: GroundControlGateway = Depends(),
    orchestrator: OrchestratorGateway = Depends()
):
    """
    Посадка самолета на землю
    
    1. Получение самолета по ID рейса
    2. Регистрация самолета в сервисе Ground Control
    3. Обновление данных самолета (vehicle_id, node_id)
    4. Отправка сообщения о посадке в оркестратор
    5. Возврат ID самолета
    
    Returns:
        dict: ID самолета
    """
    logger.info(f"Запрос на посадку самолета: flight_id={flight_id}")
    
    # Получаем самолет по ID рейса
    aircraft = await service.get_by_flight_id(flight_id)
    if not aircraft:
        logger.warning(f"Самолет для рейса с ID {flight_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет для рейса с ID {flight_id} не найден"
        )
    
    try:
        # Регистрируем самолет в сервисе Ground Control
        logger.info(f"Регистрация самолета в Ground Control: flight_id={flight_id}")
        gc_response = await ground_control.register_vehicle()
        logger.info(f"Ответ от Ground Control: {gc_response}")
        
        # Извлекаем ID транспортного средства и ID узла из ответа
        aircraft_id = gc_response.get('vehicleId')
        node_id = gc_response.get('garrageNodeId')
        
        if not aircraft_id or not node_id:
            logger.error(f"Сервис Ground Control вернул неполные данные: {gc_response}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Сервис Ground Control вернул неполные данные"
            )
        
        logger.info(f"Установка ID для самолета: flight_id={flight_id}, aircraft_id={aircraft_id}")
        aircraft = await service.set_aircraft_id(flight_id, aircraft_id)
        
        # Обновляем самолет с полученными ID
        logger.info(f"Обновление node_id для самолета: aircraft_id={aircraft_id}, node_id={node_id}")
        aircraft.update_node_id(node_id)
        await service.update(aircraft)
        
        # Сообщаем о посадке оркестратору
        logger.info(f"Отправка сообщения о посадке в оркестратор: aircraft_id={aircraft.id}, node_id={node_id}")
        await orchestrator.report_landing(aircraft.id, node_id)
        
        # Возвращаем ID самолета
        logger.info(f"Посадка самолета успешно выполнена: aircraft_id={aircraft.id}")
        return {"aircraft_id": aircraft.id}
        
    except Exception as e:
        logger.error(f"Ошибка при посадке самолета: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при посадке самолета: {str(e)}"
        )
        

@router.post("/{aircraft_id}/takeoff", status_code=status.HTTP_200_OK)
async def takeoff_aircraft(
    aircraft_id: str,
    service: AircraftServiceDep
):
    """
    Взлет самолета
    """
    logger.info(f"Запрос на взлет самолета: aircraft_id={aircraft_id}")
    
    try:
        await service.delete(aircraft_id)
        logger.info(f"Самолет успешно взлетел (удален): aircraft_id={aircraft_id}")
    except HTTPException as e:
        logger.error(f"Ошибка HTTP при взлете самолета: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Ошибка при взлете самолета: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Ошибка при взлете самолета: {str(e)}")

@router.get("/{aircraft_id}/coordinates")
async def get_aircraft_coordinates(
    aircraft_id: str,
    service: AircraftServiceDep
):
    """
    Получает координаты самолета
    """
    logger.info(f"Запрос на получение координат самолета: aircraft_id={aircraft_id}")
    
    aircraft = await service.get_by_id(aircraft_id)
    if not aircraft:
        logger.warning(f"Самолет с ID {aircraft_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет с ID {aircraft_id} не найден"
        )
    
    logger.info(f"Получены координаты самолета: aircraft_id={aircraft_id}, node_id={aircraft.node_id}")
    return {"node_id": aircraft.node_id}

class CoordinatesUpdate(BaseModel):
    node_id: str
    
@router.patch("/{aircraft_id}/coordinates", status_code=status.HTTP_204_NO_CONTENT)
async def set_aircraft_coordinates(
    aircraft_id: str,
    coordinates: CoordinatesUpdate,
    service: AircraftServiceDep
):
    """
    Устанавливает координаты самолета (node_id)
    """
    logger.info(f"Запрос на установку координат самолета: aircraft_id={aircraft_id}, node_id={coordinates.node_id}")
    
    try:
        await service.update_node_id(aircraft_id, coordinates.node_id)
        logger.info(f"Координаты самолета обновлены: aircraft_id={aircraft_id}, node_id={coordinates.node_id}")
        return
    except HTTPException as e:
        logger.error(f"Ошибка HTTP при установке координат самолета: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"Ошибка при установке координат самолета: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
        
@router.get("/{flight_id}/aircraft_id")
async def get_aircraft_id_by_flight_id(
    flight_id: str,
    service: AircraftServiceDep
):
    """
    Получает ID самолета по ID рейса
    """
    logger.info(f"Запрос на получение ID самолета по ID рейса: flight_id={flight_id}")
    
    aircraft = await service.get_by_flight_id(flight_id)
    if not aircraft:
        logger.warning(f"Самолет для рейса с ID {flight_id} не найден")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Самолет для рейса с ID {flight_id} не найден"
        )
    
    logger.info(f"Получен ID самолета: flight_id={flight_id}, aircraft_id={aircraft.id}")
    return {"aircraft_id": aircraft.id}