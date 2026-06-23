from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, books, borrowing, reports, reservations, users
from app.routers.auth import init_auth
from app.database import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_auth(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Library Management System API",
    description="REST API for managing books, users, borrowing, reservations, and reports.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(books.router)
app.include_router(borrowing.router)
app.include_router(reservations.router)
app.include_router(reports.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "library-management-system"}
