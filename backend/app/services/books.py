from math import ceil
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from pathlib import Path

from app.config import settings
from app.models import Book, BorrowStatus, BorrowTransaction, Reservation, ReservationStatus, User
from app.schemas import BookCreate, BookUpdate
from app.services.covers import delete_cover_files


def book_availability_status(book: Book) -> str:
    if book.available_copies <= 0:
        return "unavailable"
    if book.available_copies < book.total_copies:
        return "partially_available"
    return "available"


def serialize_book(book: Book) -> dict:
    return {
        "isbn": book.isbn,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "publication_year": book.publication_year,
        "total_copies": book.total_copies,
        "available_copies": book.available_copies,
        "availability_status": book_availability_status(book),
        "cover_url": book.cover_url,
        "created_at": book.created_at,
    }


def list_books(
    db: Session,
    *,
    search: Optional[str] = None,
    author: Optional[str] = None,
    publisher: Optional[str] = None,
    year: Optional[int] = None,
    available_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Book], int]:
    query = db.query(Book)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Book.title.ilike(pattern),
                Book.isbn.ilike(pattern),
                Book.author.ilike(pattern),
                Book.publisher.ilike(pattern),
            )
        )
    if author:
        query = query.filter(Book.author.ilike(f"%{author.strip()}%"))
    if publisher:
        query = query.filter(Book.publisher.ilike(f"%{publisher.strip()}%"))
    if year is not None:
        query = query.filter(Book.publication_year == year)
    if available_only:
        query = query.filter(Book.available_copies > 0)

    total = query.count()
    books = (
        query.order_by(Book.title.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return books, total


def get_book(db: Session, isbn: str) -> Optional[Book]:
    return db.query(Book).filter(Book.isbn == isbn).first()


def create_book(db: Session, payload: BookCreate) -> Book:
    existing = get_book(db, payload.isbn)
    if existing:
        raise ValueError("A book with this ISBN already exists")

    book = Book(
        isbn=payload.isbn.strip(),
        title=payload.title.strip(),
        author=payload.author.strip(),
        publisher=payload.publisher.strip() if payload.publisher else None,
        publication_year=payload.publication_year,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def update_book(db: Session, isbn: str, payload: BookUpdate) -> Book:
    book = get_book(db, isbn)
    if not book:
        raise LookupError("Book not found")

    borrowed_count = book.total_copies - book.available_copies

    if payload.title is not None:
        book.title = payload.title.strip()
    if payload.author is not None:
        book.author = payload.author.strip()
    if payload.publisher is not None:
        book.publisher = payload.publisher.strip() if payload.publisher else None
    if payload.publication_year is not None:
        book.publication_year = payload.publication_year
    if payload.total_copies is not None:
        if payload.total_copies < borrowed_count:
            raise ValueError("Total copies cannot be less than currently borrowed copies")
        delta = payload.total_copies - book.total_copies
        book.total_copies = payload.total_copies
        book.available_copies = max(0, book.available_copies + delta)

    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, isbn: str) -> None:
    book = get_book(db, isbn)
    if not book:
        raise LookupError("Book not found")

    active_borrows = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.isbn == isbn,
            BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE]),
        )
        .count()
    )
    if active_borrows > 0:
        raise ValueError("Cannot delete a book with active borrow transactions")

    pending_reservations = (
        db.query(Reservation)
        .filter(Reservation.isbn == isbn, Reservation.status == ReservationStatus.PENDING)
        .count()
    )
    if pending_reservations > 0:
        raise ValueError("Cannot delete a book with pending reservations")

    delete_cover_files(Path(settings.upload_dir), book.isbn)
    db.delete(book)
    db.commit()


def paginate(total: int, page: int, page_size: int) -> int:
    return max(1, ceil(total / page_size)) if total else 1
