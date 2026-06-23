import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    ADMINISTRATOR = "administrator"
    LIBRARIAN = "librarian"
    STUDENT = "student"


class BorrowStatus(str, enum.Enum):
    ACTIVE = "active"
    RETURNED = "returned"
    OVERDUE = "overdue"


class ReservationStatus(str, enum.Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    borrow_transactions = relationship("BorrowTransaction", back_populates="user")
    reservations = relationship("Reservation", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    isbn = Column(String(20), primary_key=True)
    title = Column(String(500), nullable=False, index=True)
    author = Column(String(500), nullable=False, index=True)
    publisher = Column(String(255), nullable=True, index=True)
    publication_year = Column(Integer, nullable=True, index=True)
    total_copies = Column(Integer, nullable=False, default=1)
    available_copies = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    borrow_transactions = relationship("BorrowTransaction", back_populates="book")
    reservations = relationship("Reservation", back_populates="book")

    __table_args__ = (
        CheckConstraint("total_copies >= 0", name="ck_books_total_copies_nonneg"),
        CheckConstraint("available_copies >= 0", name="ck_books_available_copies_nonneg"),
        CheckConstraint(
            "available_copies <= total_copies",
            name="ck_books_available_lte_total",
        ),
    )


class BorrowTransaction(Base):
    __tablename__ = "borrow_transactions"

    transaction_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    isbn = Column(String(20), ForeignKey("books.isbn"), nullable=False, index=True)
    borrow_date = Column(Date, nullable=False, server_default=func.current_date())
    due_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    status = Column(Enum(BorrowStatus), nullable=False, default=BorrowStatus.ACTIVE)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="borrow_transactions")
    book = relationship("Book", back_populates="borrow_transactions")


class Reservation(Base):
    __tablename__ = "reservations"

    reservation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    isbn = Column(String(20), ForeignKey("books.isbn"), nullable=False, index=True)
    reservation_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(ReservationStatus), nullable=False, default=ReservationStatus.PENDING)
    fulfilled_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")
