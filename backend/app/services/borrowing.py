from datetime import date, timedelta

from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Book, BorrowStatus, BorrowTransaction, Reservation, ReservationStatus, User
from app.services.books import get_book


def count_active_borrows(db: Session, user_id: int) -> int:
    return (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.user_id == user_id,
            BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE]),
        )
        .count()
    )


def refresh_overdue_status(db: Session) -> None:
    today = date.today()
    overdue_rows = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.status == BorrowStatus.ACTIVE,
            BorrowTransaction.due_date < today,
        )
        .all()
    )
    for row in overdue_rows:
        row.status = BorrowStatus.OVERDUE
    if overdue_rows:
        db.commit()


def borrow_book(db: Session, user: User, isbn: str) -> BorrowTransaction:
    refresh_overdue_status(db)

    book = get_book(db, isbn)
    if not book:
        raise LookupError("Book not found")
    if book.available_copies <= 0:
        raise ValueError("Book is not available for borrowing")

    active_count = count_active_borrows(db, user.user_id)
    if active_count >= settings.max_borrows_per_user:
        raise ValueError(f"Maximum borrow limit of {settings.max_borrows_per_user} reached")

    existing_active = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.user_id == user.user_id,
            BorrowTransaction.isbn == isbn,
            BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE]),
        )
        .first()
    )
    if existing_active:
        raise ValueError("You already have an active borrow for this book")

    borrow_date = date.today()
    due_date = borrow_date + timedelta(days=settings.borrow_days)

    transaction = BorrowTransaction(
        user_id=user.user_id,
        isbn=isbn,
        borrow_date=borrow_date,
        due_date=due_date,
        status=BorrowStatus.ACTIVE,
    )
    book.available_copies -= 1
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def return_book(db: Session, user: User, transaction_id: int) -> BorrowTransaction:
    refresh_overdue_status(db)

    transaction = (
        db.query(BorrowTransaction)
        .options(joinedload(BorrowTransaction.book))
        .filter(BorrowTransaction.transaction_id == transaction_id)
        .first()
    )
    if not transaction:
        raise LookupError("Borrow transaction not found")

    if user.role.value == "student" and transaction.user_id != user.user_id:
        raise PermissionError("You can only return your own borrowed books")

    if transaction.status == BorrowStatus.RETURNED:
        raise ValueError("This book has already been returned")

    book = transaction.book or get_book(db, transaction.isbn)
    if not book:
        raise LookupError("Associated book not found")

    transaction.return_date = date.today()
    transaction.status = BorrowStatus.RETURNED
    book.available_copies = min(book.total_copies, book.available_copies + 1)

    pending_reservation = (
        db.query(Reservation)
        .filter(
            Reservation.isbn == transaction.isbn,
            Reservation.status == ReservationStatus.PENDING,
        )
        .order_by(Reservation.reservation_date.asc())
        .first()
    )
    if pending_reservation and book.available_copies > 0:
        pending_reservation.status = ReservationStatus.FULFILLED
        from datetime import datetime, timezone

        pending_reservation.fulfilled_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(transaction)
    return transaction


def list_transactions(
    db: Session,
    *,
    user_id: int | None = None,
    status: BorrowStatus | None = None,
    active_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[BorrowTransaction], int]:
    refresh_overdue_status(db)
    query = db.query(BorrowTransaction).options(
        joinedload(BorrowTransaction.book),
        joinedload(BorrowTransaction.user),
    )

    if user_id is not None:
        query = query.filter(BorrowTransaction.user_id == user_id)
    if status is not None:
        query = query.filter(BorrowTransaction.status == status)
    if active_only:
        query = query.filter(
            BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE])
        )

    total = query.count()
    rows = (
        query.order_by(BorrowTransaction.borrow_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def serialize_transaction(row: BorrowTransaction) -> dict:
    return {
        "transaction_id": row.transaction_id,
        "user_id": row.user_id,
        "isbn": row.isbn,
        "borrow_date": row.borrow_date,
        "due_date": row.due_date,
        "return_date": row.return_date,
        "status": row.status,
        "book_title": row.book.title if row.book else None,
        "username": row.user.username if row.user else None,
        "full_name": row.user.full_name if row.user else None,
    }


def get_transaction_with_details(db: Session, transaction_id: int) -> BorrowTransaction | None:
    return (
        db.query(BorrowTransaction)
        .options(joinedload(BorrowTransaction.book), joinedload(BorrowTransaction.user))
        .filter(BorrowTransaction.transaction_id == transaction_id)
        .first()
    )
