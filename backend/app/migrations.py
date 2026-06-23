from sqlalchemy import text

from app.database import engine
from app.models import Base


def run_migrations() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE books ADD COLUMN IF NOT EXISTS cover_url VARCHAR(500)"))
