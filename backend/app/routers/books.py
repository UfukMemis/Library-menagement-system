from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import User, UserRole
from app.schemas import BookCreate, BookResponse, BookUpdate, PaginatedResponse
from app.services.books import (
    create_book,
    delete_book,
    get_book,
    list_books,
    paginate,
    serialize_book,
    update_book,
)

router = APIRouter(prefix="/books", tags=["Books"])


@router.get("", response_model=PaginatedResponse[BookResponse])
def get_books(
    search: str | None = Query(None),
    author: str | None = Query(None),
    publisher: str | None = Query(None),
    year: int | None = Query(None),
    available_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    books, total = list_books(
        db,
        search=search,
        author=author,
        publisher=publisher,
        year=year,
        available_only=available_only,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_book(book) for book in books],
        total=total,
        page=page,
        page_size=page_size,
        pages=paginate(total, page, page_size),
    )


@router.get("/{isbn}", response_model=BookResponse)
def get_book_by_isbn(isbn: str, db: Session = Depends(get_db)):
    book = get_book(db, isbn)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return serialize_book(book)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def add_book(
    payload: BookCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.LIBRARIAN)),
):
    try:
        book = create_book(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_book(book)


@router.put("/{isbn}", response_model=BookResponse)
def update_book_by_isbn(
    isbn: str,
    payload: BookUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.LIBRARIAN)),
):
    try:
        book = update_book(db, isbn, payload)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_book(book)


@router.delete("/{isbn}", status_code=status.HTTP_204_NO_CONTENT)
def remove_book(
    isbn: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.LIBRARIAN)),
):
    try:
        delete_book(db, isbn)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
