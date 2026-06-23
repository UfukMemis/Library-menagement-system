from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.migrations import run_migrations
from app.routers import auth, books, borrowing, reports, reservations, users
from app.routers.auth import init_auth
from app.database import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_migrations()
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

uploads_dir = settings.upload_path
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "library-management-system"}
