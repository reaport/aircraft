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
            response = await self.post(f"aircraft/{aircraft_id}/landing", data=data)
            
            logger.info(f"Сообщение о приземлении самолета {aircraft_id} успешно отправлено в оркестратор")
            return response
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения о приземлении самолета {aircraft_id}: {str(e)}")
            raise
