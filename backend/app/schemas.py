from datetime import date, datetime
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BorrowStatus, ReservationStatus, UserRole

T = TypeVar("T")


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[UserRole] = None


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.STUDENT


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    user_id: int
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BookBase(BaseModel):
    isbn: str = Field(min_length=10, max_length=20)
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=500)
    publisher: Optional[str] = Field(default=None, max_length=255)
    publication_year: Optional[int] = Field(default=None, ge=0, le=2100)
    total_copies: int = Field(default=1, ge=0)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    author: Optional[str] = Field(default=None, min_length=1, max_length=500)
    publisher: Optional[str] = Field(default=None, max_length=255)
    publication_year: Optional[int] = Field(default=None, ge=0, le=2100)
    total_copies: Optional[int] = Field(default=None, ge=0)


class BookResponse(BookBase):
    available_copies: int
    availability_status: str
    cover_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BorrowRequest(BaseModel):
    isbn: str


class ReturnRequest(BaseModel):
    transaction_id: int


class BorrowTransactionResponse(BaseModel):
    transaction_id: int
    user_id: int
    isbn: str
    borrow_date: date
    due_date: date
    return_date: Optional[date]
    status: BorrowStatus
    book_title: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReservationCreate(BaseModel):
    isbn: str


class ReservationResponse(BaseModel):
    reservation_id: int
    user_id: int
    isbn: str
    reservation_date: datetime
    status: ReservationStatus
    book_title: Optional[str] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MostBorrowedReportItem(BaseModel):
    isbn: str
    title: str
    author: str
    borrow_count: int


class ActiveUserReportItem(BaseModel):
    user_id: int
    username: str
    full_name: str
    active_borrows: int


class MonthlyBorrowStat(BaseModel):
    month: str
    borrow_count: int


class ReportsResponse(BaseModel):
    most_borrowed_books: list[MostBorrowedReportItem]
    active_users: list[ActiveUserReportItem]
    currently_borrowed_books: list[BorrowTransactionResponse]
    overdue_books: list[BorrowTransactionResponse]
    monthly_borrowing_statistics: list[MonthlyBorrowStat]
