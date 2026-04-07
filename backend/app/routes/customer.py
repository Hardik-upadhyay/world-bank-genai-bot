"""
Customer Routes
-----------------
GET /customer/dashboard → returns profile, accounts, and recent transactions
                          for the currently authenticated customer.
"""
from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.auth.auth_service import get_current_user, CurrentUser
from app.db.queries import get_customer_profile, get_accounts, get_transactions

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def get_dashboard(current_user: CurrentUser = Depends(get_current_user)):
    """Return aggregated dashboard data for the logged-in customer."""
    try:
        profile = get_customer_profile(current_user.user_id)
        accounts = get_accounts(current_user.user_id)
        transactions = get_transactions(current_user.user_id, limit=10)

        return {
            "user": {
                "user_id": current_user.user_id,
                "full_name": current_user.full_name,
                "role": current_user.role,
                "email": profile.get("email") if profile else None,
                "customer_id": profile.get("customer_id") if profile else None,
                "kyc_status": profile.get("kyc_status") if profile else "unknown",
                "phone": profile.get("phone") if profile else None,
                "address": profile.get("address") if profile else None,
            },
            "accounts": [
                {
                    "account_number": a.get("account_number"),
                    "account_type": a.get("account_type"),
                    "balance": a.get("balance", 0),
                    "currency": a.get("currency", "USD"),
                    "branch": a.get("branch"),
                    "status": a.get("status", "Active"),
                    "opened_date": a.get("opened_date"),
                }
                for a in accounts
            ],
            "recent_transactions": [
                {
                    "id": t.get("id"),
                    "account_number": t.get("account_number"),
                    "account_type": t.get("account_type"),
                    "date": t.get("date"),
                    "description": t.get("description"),
                    "amount": t.get("amount", 0),
                    "transaction_type": t.get("type", "debit"),
                    "balance_after": t.get("balance_after"),
                }
                for t in transactions
            ],
        }
    except Exception as e:
        logger.error(f"Dashboard fetch failed for user {current_user.user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard data.")
