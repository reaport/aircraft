from typing import Dict, Any
import logging

from gateways.base import BaseGateway
from config import settings

logger = logging.getLogger("uvicorn")

class GroundControlGateway(BaseGateway):
    """
    Шлюз для взаимодействия с сервисом ground control
    """
    
    def __init__(self):
        """
        Инициализация шлюза для сервиса ground control
        Параметры соединения берутся из настроек приложения
        """
        super().__init__(
            base_url=settings.GROUND_CONTROL_SERVICE_URL,
            timeout=settings.GROUND_CONTROL_SERVICE_TIMEOUT,
            max_retries=settings.GROUND_CONTROL_SERVICE_MAX_RETRIES,
            headers={
                "X-Service-Name": "aircraft-service"
            }
        )
    
    async def register_vehicle(self) -> Dict[str, Any]:
        """
        Регистрирует транспортное средство (самолет) в сервисе ground control
        
        Args:
            aircraft_id: Опциональный ID самолета для логирования
                
        Returns:
            Dict[str, Any]: Результат регистрации от сервиса ground control, содержащий:
                - garrageNodeId: ID узла гаража/аэропорта
                - vehicleId: Назначенный ID транспортного средства
                - serviceSpots: Доступные сервисные точки
        """
        logger.info(f"Регистрация самолета в ground control")
        
        try:
            # Отправляем пустой POST запрос на регистрацию самолета
            # Согласно формату API: POST /register-vehicle/airplane
            response = await self.post("register-vehicle/airplane", data={})
            
            logger.info(f"Самолет успешно зарегистрирован в ground control с ID: {response.get('vehicleId', 'неизвестно')}")
            return response
        except Exception as e:
            logger.error(f"Ошибка при регистрации самолета в ground control: {str(e)}")
            raise
