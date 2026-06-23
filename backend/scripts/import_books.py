"""Import and clean Kaggle Books dataset into PostgreSQL."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, engine
from app.models import Base, Book

DEFAULT_PATHS = [
    Path("/app/data/Books.csv"),
    Path("/app/data/books.csv"),
    Path(__file__).resolve().parents[2] / "data" / "Books.csv",
    Path(__file__).resolve().parents[2] / "data" / "books.csv",
]

INVALID_ISBN = {"", "0", "NULL", "null", "NA", "N/A"}


def normalize_isbn(value: object) -> str | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper().replace("-", "").replace(" ", "")
    if text in INVALID_ISBN:
        return None
    if not re.fullmatch(r"[0-9X]{10,13}", text):
        return None
    return text


def clean_year(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        year = int(float(str(value).strip()))
    except ValueError:
        return None
    if year < 1000 or year > 2100:
        return None
    return year


def clean_text(value: object, fallback: str = "Unknown") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    text = str(value).strip()
    return text if text else fallback


def resolve_dataset_path(explicit: str | None) -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if path.exists() else None
    for candidate in DEFAULT_PATHS:
        if candidate.exists():
            return candidate
    return None


def load_and_clean_dataframe(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="latin-1", on_bad_lines="skip", low_memory=False)

    column_map = {
        "ISBN": "isbn",
        "Book-Title": "title",
        "Book-Author": "author",
        "Publisher": "publisher",
        "Year-Of-Publication": "publication_year",
        "isbn": "isbn",
        "title": "title",
        "author": "author",
        "publisher": "publisher",
        "publication_year": "publication_year",
    }
    df = df.rename(columns={col: column_map[col] for col in df.columns if col in column_map})

    required = {"isbn", "title", "author"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset missing required columns: {', '.join(sorted(missing))}")

    df["isbn"] = df["isbn"].map(normalize_isbn)
    df = df.dropna(subset=["isbn"])
    df["title"] = df["title"].map(lambda v: clean_text(v, "Untitled"))
    df["author"] = df["author"].map(lambda v: clean_text(v, "Unknown Author"))
    if "publisher" in df.columns:
        df["publisher"] = df["publisher"].map(
            lambda v: None
            if v is None or (isinstance(v, float) and pd.isna(v)) or not str(v).strip()
            else str(v).strip()
        )
    else:
        df["publisher"] = None
    if "publication_year" in df.columns:
        df["publication_year"] = df["publication_year"].map(clean_year)
    else:
        df["publication_year"] = None

    df = df.drop_duplicates(subset=["isbn"], keep="first")
    return df[["isbn", "title", "author", "publisher", "publication_year"]]


def import_books(db: Session, df: pd.DataFrame, copies: int = 2) -> int:
    inserted = 0
    for row in df.itertuples(index=False):
        if db.get(Book, row.isbn):
            continue
        db.add(
            Book(
                isbn=row.isbn,
                title=row.title[:500],
                author=row.author[:500],
                publisher=(row.publisher[:255] if row.publisher else None),
                publication_year=row.publication_year,
                total_copies=copies,
                available_copies=copies,
            )
        )
        inserted += 1
    db.commit()
    return inserted


def seed_sample_books(db: Session) -> int:
    samples = [
        ("0439554896", "Harry Potter and the Chamber of Secrets", "J.K. Rowling", "Scholastic", 1999),
        ("0439785960", "Harry Potter and the Goblet of Fire", "J.K. Rowling", "Scholastic", 2000),
        ("0316769177", "The Catcher in the Rye", "J.D. Salinger", "Little, Brown", 1951),
        ("0618640150", "The Lord of the Rings", "J.R.R. Tolkien", "Houghton Mifflin", 1954),
        ("0142437239", "Crime and Punishment", "Fyodor Dostoyevsky", "Penguin Classics", 1866),
        ("0743273567", "The Great Gatsby", "F. Scott Fitzgerald", "Scribner", 1925),
        ("0156012197", "Life of Pi", "Yann Martel", "Harvest Books", 2001),
        ("0385472579", "The Handmaid's Tale", "Margaret Atwood", "Anchor", 1985),
        ("0061120081", "To Kill a Mockingbird", "Harper Lee", "Harper Perennial", 1960),
        ("0451524934", "1984", "George Orwell", "Signet Classic", 1949),
    ]
    inserted = 0
    for isbn, title, author, publisher, year in samples:
        if db.get(Book, isbn):
            continue
        db.add(
            Book(
                isbn=isbn,
                title=title,
                author=author,
                publisher=publisher,
                publication_year=year,
                total_copies=3,
                available_copies=3,
            )
        )
        inserted += 1
    db.commit()
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Kaggle Books dataset")
    parser.add_argument("--path", help="Path to Books.csv")
    parser.add_argument("--copies", type=int, default=2, help="Copies per imported title")
    parser.add_argument("--if-empty", action="store_true", help="Skip import when books already exist")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(Book).count()
        if args.if_empty and existing > 0:
            print(f"Skipping import; {existing} books already in database.")
            return

        dataset_path = resolve_dataset_path(args.path)
        if dataset_path:
            print(f"Importing from {dataset_path}")
            df = load_and_clean_dataframe(dataset_path)
            count = import_books(db, df, copies=args.copies)
            print(f"Imported {count} books from dataset ({len(df)} cleaned rows).")
        else:
            print("No Kaggle CSV found. Seeding sample inventory instead.")
            count = seed_sample_books(db)
            print(f"Seeded {count} sample books.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
