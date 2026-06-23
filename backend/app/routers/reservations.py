from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import ReservationStatus, User, UserRole
from app.schemas import PaginatedResponse, ReservationCreate, ReservationResponse
from app.services.books import paginate
from app.services.reservations import (
    cancel_reservation,
    create_reservation,
    list_reservations,
    serialize_reservation,
)

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.post("", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def reserve_book(
    payload: ReservationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        reservation = create_reservation(db, current_user, payload.isbn.strip())
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rows, _ = list_reservations(db, user_id=reservation.user_id, page=1, page_size=1)
    return serialize_reservation(rows[0] if rows else reservation)


@router.get("", response_model=PaginatedResponse[ReservationResponse])
def get_reservations(
    user_id: int | None = Query(None),
    status_filter: ReservationStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.STUDENT:
        user_id = current_user.user_id

    rows, total = list_reservations(
        db,
        user_id=user_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse(
        items=[serialize_reservation(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=paginate(total, page, page_size),
    )


@router.post("/{reservation_id}/cancel", response_model=ReservationResponse)
def cancel(
    reservation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        reservation = cancel_reservation(db, current_user, reservation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    rows, _ = list_reservations(db, user_id=reservation.user_id, page=1, page_size=100)
    for row in rows:
        if row.reservation_id == reservation_id:
            return serialize_reservation(row)
    return serialize_reservation(reservation)
