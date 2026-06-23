from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_roles
from app.models import BorrowStatus, User, UserRole
from app.schemas import BorrowRequest, BorrowTransactionResponse, PaginatedResponse, ReturnRequest
from app.services.books import paginate
from app.services.borrowing import borrow_book, list_transactions, return_book, serialize_transaction

router = APIRouter(tags=["Borrowing"])


@router.post("/borrow", response_model=BorrowTransactionResponse, status_code=status.HTTP_201_CREATED)
def borrow(
    payload: BorrowRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        transaction = borrow_book(db, current_user, payload.isbn.strip())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rows, _ = list_transactions(db, user_id=transaction.user_id, page=1, page_size=100)
    for row in rows:
        if row.transaction_id == transaction.transaction_id:
            return serialize_transaction(row)
    return serialize_transaction(transaction)


@router.post("/return", response_model=BorrowTransactionResponse)
def return_item(
    payload: ReturnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        transaction = return_book(db, current_user, payload.transaction_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_transaction(transaction)


@router.get("/transactions", response_model=PaginatedResponse[BorrowTransactionResponse])
def get_transactions(
    user_id: int | None = Query(None),
    status_filter: BorrowStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.STUDENT:
        user_id = current_user.user_id
    elif user_id is None:
        user_id = None

    rows, total = list_transactions(
        db,
        user_id=user_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_transaction(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=paginate(total, page, page_size),
    )
