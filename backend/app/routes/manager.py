"""
Manager Routes
-----------------
POST /manager/customers  → create new customer
GET  /manager/customers  → list all customers

All routes require manager role JWT.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
import logging

from app.auth.auth_service import require_manager, CurrentUser
from app.auth.auth_service import hash_password
from app.db.queries import create_customer_user, list_all_customers

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateCustomerRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    email: str = Field(...)
    phone: Optional[str] = None
    address: Optional[str] = None
    account_type: str = Field(default="Savings")
    initial_balance: float = Field(default=0.0, ge=0)
    currency: str = Field(default="USD")
    branch: str = Field(default="World Bank HQ")


class CreateCustomerResponse(BaseModel):
    message: str
    account_number: str
    customer_id: str


@router.post("/customers", response_model=CreateCustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(
    request: CreateCustomerRequest,
    manager: CurrentUser = Depends(require_manager),
):
    """Manager-only: Create a new customer with an initial account."""
    import random, string
    customer_id = "WB-CUST-" + "".join(random.choices(string.digits, k=5))

    try:
        result = create_customer_user(
            username=request.username.strip().lower(),
            password_hash=hash_password(request.password),
            full_name=request.full_name,
            email=request.email,
            customer_id=customer_id,
            phone=request.phone or "",
            address=request.address or "",
            account_type=request.account_type,
            initial_balance=request.initial_balance,
            currency=request.currency,
            branch=request.branch,
            manager_user_id=manager.user_id,
        )
        logger.info(f"Manager {manager.username} created customer: {request.username}")
        return CreateCustomerResponse(
            message=f"Customer '{request.full_name}' created successfully.",
            account_number=result["account_number"],
            customer_id=customer_id,
        )
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{request.username}' already exists.",
            )
        logger.error(f"Create customer failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create customer.")


@router.get("/customers")
async def get_all_customers(manager: CurrentUser = Depends(require_manager)):
    """Manager-only: List all customers with account summaries."""
    customers = list_all_customers()
    return {"total": len(customers), "customers": customers}
