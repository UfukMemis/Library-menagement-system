from sqlalchemy.orm import Session, joinedload

from app.models import Book, BorrowStatus, BorrowTransaction, Reservation, ReservationStatus, User
from app.services.books import get_book


def create_reservation(db: Session, user: User, isbn: str) -> Reservation:
    book = get_book(db, isbn)
    if not book:
        raise LookupError("Book not found")

    if book.available_copies > 0:
        raise ValueError("Book is currently available; borrow it instead of reserving")

    existing_pending = (
        db.query(Reservation)
        .filter(
            Reservation.user_id == user.user_id,
            Reservation.isbn == isbn,
            Reservation.status == ReservationStatus.PENDING,
        )
        .first()
    )
    if existing_pending:
        raise ValueError("You already have a pending reservation for this book")

    active_borrow = (
        db.query(BorrowTransaction)
        .filter(
            BorrowTransaction.user_id == user.user_id,
            BorrowTransaction.isbn == isbn,
            BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE]),
        )
        .first()
    )
    if active_borrow:
        raise ValueError("You already borrowed this book")

    reservation = Reservation(
        user_id=user.user_id,
        isbn=isbn,
        status=ReservationStatus.PENDING,
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation


def list_reservations(
    db: Session,
    *,
    user_id: int | None = None,
    status: ReservationStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Reservation], int]:
    query = db.query(Reservation).options(
        joinedload(Reservation.book),
        joinedload(Reservation.user),
    )
    if user_id is not None:
        query = query.filter(Reservation.user_id == user_id)
    if status is not None:
        query = query.filter(Reservation.status == status)

    total = query.count()
    rows = (
        query.order_by(Reservation.reservation_date.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return rows, total


def cancel_reservation(db: Session, user: User, reservation_id: int) -> Reservation:
    reservation = db.query(Reservation).filter(Reservation.reservation_id == reservation_id).first()
    if not reservation:
        raise LookupError("Reservation not found")

    if user.role.value == "student" and reservation.user_id != user.user_id:
        raise PermissionError("You can only cancel your own reservations")

    if reservation.status != ReservationStatus.PENDING:
        raise ValueError("Only pending reservations can be cancelled")

    reservation.status = ReservationStatus.CANCELLED
    db.commit()
    db.refresh(reservation)
    return reservation


def serialize_reservation(row: Reservation) -> dict:
    return {
        "reservation_id": row.reservation_id,
        "user_id": row.user_id,
        "isbn": row.isbn,
        "reservation_date": row.reservation_date,
        "status": row.status,
        "book_title": row.book.title if row.book else None,
        "username": row.user.username if row.user else None,
        "full_name": row.user.full_name if row.user else None,
    }


def get_reservation_with_details(db: Session, reservation_id: int) -> Reservation | None:
    return (
        db.query(Reservation)
        .options(joinedload(Reservation.book), joinedload(Reservation.user))
        .filter(Reservation.reservation_id == reservation_id)
        .first()
    )
