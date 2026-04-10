from fastapi import FastAPI

from gateway.lifespan import lifespan
from gateway.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Coffee Shop API Gateway", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
