from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_admin
from app.db.session import get_db
from app.models import User
from app.schemas import AdminDashboardStats, UserResponse, UserStatusUpdate
from app.services.admin_service import AdminService

router = APIRouter()

@router.get("/dashboard", response_model=AdminDashboardStats)
async def get_dashboard_metrics(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve system-wide aggregated metrics for the administrative dashboard."""
    return await AdminService.get_dashboard_stats(db)

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List system users with pagination and search filter."""
    return await AdminService.list_users(db, skip=skip, limit=limit, search=search)

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a specific user's details by UUID."""
    return await AdminService.get_user_by_id(db, user_id)

@router.patch("/users/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: UUID,
    status_update: UserStatusUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate user account with server-side administrative protection."""
    return await AdminService.update_user_status(db, user_id, status_update, admin)
