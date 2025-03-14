from typing import Dict, Any, Optional
import logging

from gateways.base import BaseGateway
from config import settings

logger = logging.getLogger("uvicorn")

class OrchestratorGateway(BaseGateway):
    """
    Шлюз для взаимодействия с сервисом оркестратора
    """
    
    def __init__(self):
        """
        Инициализация шлюза для сервиса оркестратора
        Параметры соединения берутся из настроек приложения
        """
        super().__init__(
            base_url=settings.ORCHESTRATOR_SERVICE_URL,
            timeout=settings.ORCHESTRATOR_SERVICE_TIMEOUT,
            max_retries=settings.ORCHESTRATOR_SERVICE_MAX_RETRIES,
            headers={
                "X-Service-Name": "aircraft-service"
            }
        )
    
    async def register_vehicle(self, aircraft_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Регистрирует транспортное средство (самолет) в сервисе оркестратора
        
        Args:
            aircraft_id: Опциональный ID самолета для логирования
                
        Returns:
            Dict[str, Any]: Результат регистрации от сервиса оркестратора, содержащий:
                - garrageNodeId: ID узла гаража/аэропорта
                - vehicleId: Назначенный ID транспортного средства
                - serviceSpots: Доступные сервисные точки
        """
        log_id = aircraft_id or "новый самолет"
        logger.info(f"Регистрация самолета в оркестраторе: {log_id}")
        
        try:
            # Отправляем пустой POST запрос на регистрацию самолета
            # Согласно формату API: POST /register-vehicle/airplane
            response = await self.post("register-vehicle/airplane", data={})
            
            logger.info(f"Самолет успешно зарегистрирован в оркестраторе с ID: {response.get('vehicleId', 'неизвестно')}")
            return response
        except Exception as e:
            logger.error(f"Ошибка при регистрации самолета в оркестраторе: {str(e)}")
            raise
            
    async def report_landing(self, aircraft_id: str, landing_point: str) -> Dict[str, Any]:
        """
        Отправляет сообщение о приземлении самолета в сервис оркестратора
        
        Args:
            aircraft_id: ID самолета
            landing_point: Точка приземления
                
        Returns:
            Dict[str, Any]: Результат операции от сервиса оркестратора
        """
        logger.info(f"Отправка сообщения о приземлении самолета {aircraft_id} в точке {landing_point}")
        
        try:
            # Отправляем POST запрос о приземлении
            data = {"landing_point": landing_point}
            response = await self.post(f"{aircraft_id}/landing", data=data)
            
            logger.info(f"Сообщение о приземлении самолета {aircraft_id} успешно отправлено в оркестратор")
            return response
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения о приземлении самолета {aircraft_id}: {str(e)}")
            raise
