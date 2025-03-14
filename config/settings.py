from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    AIRCRAFT_CONFIG_PATH: str = "config/aircraft_config.json"
    REDIS_URL: str = "redis://localhost:6379"
    
    # Настройки для внешнего сервиса Example Service
    ORCHESTRATOR_SERVICE_URL: str = "http://orchestrator-service-api.com"
    ORCHESTRATOR_SERVICE_TIMEOUT: int = 30
    ORCHESTRATOR_SERVICE_MAX_RETRIES: int = 5
    
    GROUND_CONTROL_SERVICE_URL: str = "http://ground-control-service-api.com"
    GROUND_CONTROL_SERVICE_TIMEOUT: int = 30
    GROUND_CONTROL_SERVICE_MAX_RETRIES: int = 5
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()
