import asyncio
import logging
import json
import time
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin

import aiohttp
from aiohttp.client_exceptions import ClientError

logger = logging.getLogger("uvicorn")

class BaseGateway:
    """
    Базовый класс для выполнения HTTP-запросов к внешним сервисам
    с механизмом бесконечных ретраев при ошибках.
    """
    
    def __init__(
        self,
        base_url: str,
        timeout: int = 30,
        max_retries: int = 5,
        retry_delay: int = 1,
        retry_multiplier: float = 2.0,
        max_retry_delay: int = 60,
        headers: Optional[Dict[str, str]] = None,
    ):
        """
        Инициализация Gateway для запросов к внешним сервисам.
        
        Args:
            base_url: Базовый URL сервиса
            timeout: Таймаут ожидания ответа в секундах
            max_retries: Максимальное количество повторных попыток (0 для бесконечных)
            retry_delay: Начальная задержка между повторными попытками в секундах
            retry_multiplier: Множитель для увеличения задержки при каждой следующей попытке
            max_retry_delay: Максимальная задержка между попытками в секундах
            headers: Дополнительные заголовки для запросов
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_multiplier = retry_multiplier
        self.max_retry_delay = max_retry_delay
        self.headers = headers or {}
        
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'application/json'
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], List[Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        allow_redirects: bool = True,
    ) -> Any:
        """
        Выполняет HTTP запрос с механизмом повторных попыток при ошибках.
        
        Args:
            method: HTTP метод (GET, POST, PUT, PATCH, DELETE)
            endpoint: Путь к ресурсу относительно base_url
            params: Параметры запроса (для query string)
            data: Данные для отправки в теле запроса
            headers: Дополнительные заголовки для запроса
            timeout: Таймаут для запроса (переопределяет значение по умолчанию)
            allow_redirects: Разрешать ли перенаправления
            
        Returns:
            Any: Ответ сервера, обычно в виде словаря или списка
            
        Raises:
            Exception: При ошибке после всех повторных попыток
        """
        url = urljoin(f"{self.base_url}/", endpoint.lstrip('/'))
        request_headers = {**self.headers}
        if headers:
            request_headers.update(headers)
            
        request_timeout = timeout or self.timeout
        
        # Преобразуем данные в JSON, если они заданы и не являются строкой
        json_data = None
        if data is not None:
            if not isinstance(data, str):
                json_data = data
                data = None
        
        # Логируем информацию о запросе
        log_data = {
            "method": method,
            "url": url,
            "params": params,
        }
        
        # Логируем данные запроса, исключая чувствительную информацию
        if json_data:
            # Создаем копию для логирования, чтобы не изменять оригинальные данные
            log_json_data = json_data
            if isinstance(log_json_data, dict):
                # Если это словарь, то делаем копию
                log_json_data = log_json_data.copy()
                # Маскируем чувствительные данные при их наличии
                for key in ['password', 'token', 'secret', 'key', 'auth']:
                    if key in log_json_data:
                        log_json_data[key] = '***'
            log_data["data"] = log_json_data
        
        logger.info(f"Отправка запроса: {json.dumps(log_data, ensure_ascii=False)}")
        
        retries = 0
        current_delay = self.retry_delay
        
        while self.max_retries == 0 or retries <= self.max_retries:
            try:
                async with aiohttp.ClientSession() as session:
                    logger.debug(f"Выполняю {method} запрос к {url}")
                    
                    async with session.request(
                        method=method,
                        url=url,
                        params=params,
                        data=data,
                        json=json_data,
                        headers=request_headers,
                        timeout=request_timeout,
                        allow_redirects=allow_redirects,
                    ) as response:
                        # Читаем ответ
                        content = await response.read()
                        
                        # Обрабатываем статус ответа
                        if 200 <= response.status < 300:
                            # Успешный ответ
                            if not content:
                                logger.info(f"Получен пустой ответ от {url}, status={response.status}")
                                return None
                                
                            try:
                                response_json = await response.json()
                                # Логируем ответ сервера
                                logger.info(f"Получен ответ от {url}, status={response.status}, data={json.dumps(response_json, ensure_ascii=False)}")
                                return response_json
                            except json.JSONDecodeError:
                                # Если ответ не JSON, логируем как текст
                                response_text = content.decode('utf-8')
                                logger.info(f"Получен текстовый ответ от {url}, status={response.status}, data={response_text[:500]}")
                                return response_text
                        else:
                            error_msg = f"Ошибка запроса {method} {url}: статус {response.status}"
                            try:
                                error_data = await response.json()
                                error_msg += f", данные: {error_data}"
                            except:
                                if content:
                                    error_msg += f", контент: {content.decode('utf-8', errors='replace')}"
                            
                            logger.error(error_msg)
                            
                            # Не повторяем запрос для клиентских ошибок (4xx)
                            if 400 <= response.status < 500:
                                # Для 429 (Too Many Requests) все же делаем ретрай
                                if response.status != 429:
                                    raise Exception(error_msg)
                            
                            # Сервер недоступен или ошибка - повторяем запрос
                            raise Exception(error_msg)
                            
            except (ClientError, asyncio.TimeoutError, Exception) as e:
                retries += 1
                
                if self.max_retries > 0 and retries > self.max_retries:
                    logger.error(f"Превышено максимальное количество попыток ({self.max_retries}) для {method} {url}. Последняя ошибка: {str(e)}")
                    raise
                
                # Логируем информацию о повторе
                logger.warning(f"Ошибка при выполнении {method} запроса к {url}: {str(e)}. Повторная попытка {retries} через {current_delay} сек.")
                
                # Ждем перед следующей попыткой
                await asyncio.sleep(current_delay)
                
                # Увеличиваем задержку для следующей попытки
                current_delay = min(current_delay * self.retry_multiplier, self.max_retry_delay)
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        """
        Выполняет GET запрос
        
        Args:
            endpoint: Путь к ресурсу
            params: Параметры запроса
            kwargs: Дополнительные параметры для _make_request
            
        Returns:
            Any: Ответ сервера
        """
        return await self._make_request("GET", endpoint, params=params, **kwargs)
    
    async def post(self, endpoint: str, data: Optional[Union[Dict[str, Any], List[Any]]] = None, **kwargs) -> Any:
        """
        Выполняет POST запрос
        
        Args:
            endpoint: Путь к ресурсу
            data: Данные для отправки
            kwargs: Дополнительные параметры для _make_request
            
        Returns:
            Any: Ответ сервера
        """
        return await self._make_request("POST", endpoint, data=data, **kwargs)
    
    async def put(self, endpoint: str, data: Optional[Union[Dict[str, Any], List[Any]]] = None, **kwargs) -> Any:
        """
        Выполняет PUT запрос
        
        Args:
            endpoint: Путь к ресурсу
            data: Данные для отправки
            kwargs: Дополнительные параметры для _make_request
            
        Returns:
            Any: Ответ сервера
        """
        return await self._make_request("PUT", endpoint, data=data, **kwargs)
    
    async def patch(self, endpoint: str, data: Optional[Union[Dict[str, Any], List[Any]]] = None, **kwargs) -> Any:
        """
        Выполняет PATCH запрос
        
        Args:
            endpoint: Путь к ресурсу
            data: Данные для отправки
            kwargs: Дополнительные параметры для _make_request
            
        Returns:
            Any: Ответ сервера
        """
        return await self._make_request("PATCH", endpoint, data=data, **kwargs)
    
    async def delete(self, endpoint: str, **kwargs) -> Any:
        """
        Выполняет DELETE запрос
        
        Args:
            endpoint: Путь к ресурсу
            kwargs: Дополнительные параметры для _make_request
            
        Returns:
            Any: Ответ сервера или None
        """
        return await self._make_request("DELETE", endpoint, **kwargs)
