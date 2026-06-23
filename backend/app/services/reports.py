from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Book, BorrowStatus, BorrowTransaction, User
from app.services.borrowing import refresh_overdue_status, serialize_transaction


def get_reports(db: Session, *, limit: int = 10) -> dict:
    refresh_overdue_status(db)

    most_borrowed = (
        db.query(
            Book.isbn,
            Book.title,
            Book.author,
            func.count(BorrowTransaction.transaction_id).label("borrow_count"),
        )
        .join(BorrowTransaction, BorrowTransaction.isbn == Book.isbn)
        .group_by(Book.isbn, Book.title, Book.author)
        .order_by(func.count(BorrowTransaction.transaction_id).desc())
        .limit(limit)
        .all()
    )

    active_users = (
        db.query(
            User.user_id,
            User.username,
            User.full_name,
            func.count(BorrowTransaction.transaction_id).label("active_borrows"),
        )
        .join(BorrowTransaction, BorrowTransaction.user_id == User.user_id)
        .filter(BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE]))
        .group_by(User.user_id, User.username, User.full_name)
        .order_by(func.count(BorrowTransaction.transaction_id).desc())
        .limit(limit)
        .all()
    )

    currently_borrowed = (
        db.query(BorrowTransaction)
        .options(joinedload(BorrowTransaction.book), joinedload(BorrowTransaction.user))
        .filter(BorrowTransaction.status.in_([BorrowStatus.ACTIVE, BorrowStatus.OVERDUE]))
        .order_by(BorrowTransaction.due_date.asc())
        .limit(50)
        .all()
    )

    overdue_books = (
        db.query(BorrowTransaction)
        .options(joinedload(BorrowTransaction.book), joinedload(BorrowTransaction.user))
        .filter(BorrowTransaction.status == BorrowStatus.OVERDUE)
        .order_by(BorrowTransaction.due_date.asc())
        .limit(50)
        .all()
    )

    monthly_stats = (
        db.query(
            func.to_char(BorrowTransaction.borrow_date, "YYYY-MM").label("month"),
            func.count(BorrowTransaction.transaction_id).label("borrow_count"),
        )
        .group_by(func.to_char(BorrowTransaction.borrow_date, "YYYY-MM"))
        .order_by(func.to_char(BorrowTransaction.borrow_date, "YYYY-MM").desc())
        .limit(12)
        .all()
    )

    return {
        "most_borrowed_books": [
            {
                "isbn": row.isbn,
                "title": row.title,
                "author": row.author,
                "borrow_count": row.borrow_count,
            }
            for row in most_borrowed
        ],
        "active_users": [
            {
                "user_id": row.user_id,
                "username": row.username,
                "full_name": row.full_name,
                "active_borrows": row.active_borrows,
            }
            for row in active_users
        ],
        "currently_borrowed_books": [serialize_transaction(row) for row in currently_borrowed],
        "overdue_books": [serialize_transaction(row) for row in overdue_books],
        "monthly_borrowing_statistics": [
            {"month": row.month, "borrow_count": row.borrow_count} for row in monthly_stats
        ],
    }
