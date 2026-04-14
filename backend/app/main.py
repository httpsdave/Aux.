from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.charts import router as charts_router
from app.core.config import settings
from app.db.database import engine
from app.db.models import Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(charts_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
