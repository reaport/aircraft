from fastapi import FastAPI
import logging
from config.aircraft_config import aircraft_config
from lifespan import global_lifespan
from routers import generate, aircraft

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("app")

# Создаем экземпляр FastAPI с указанием глобального lifespan
app = FastAPI(
    title="Aircraft API",
    description="API для работы с данными самолетов",
    version="1.0.0",
    lifespan=global_lifespan
)

# Регистрируем роутеры
app.include_router(generate.router)
app.include_router(aircraft.router)

# Корневой маршрут
@app.get("/")
async def root():
    logger.info("Запрос к корневому маршруту")
    return {
        "message": "Aircraft API is running",
        "available_models": list(aircraft_config.aircraft.keys())
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("Запуск приложения Aircraft API")
    uvicorn.run(app, host="0.0.0.0", port=8000)