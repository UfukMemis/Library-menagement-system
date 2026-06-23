from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_roles
# Added User here alongside UserRole
from app.models import User, UserRole 
from app.schemas import ReportsResponse
from app.services.reports import get_reports

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=ReportsResponse)
def reports(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.LIBRARIAN)),
):
    return get_reports(db)