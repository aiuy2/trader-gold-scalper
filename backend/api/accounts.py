"""accounts.py - link/list/remove the user's MT5 trading accounts."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from database.models.user import User
from app.dependencies import get_current_user
from services.account_service import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])


class LinkAccountRequest(BaseModel):
    login: str
    password: str
    server: str
    broker: str = ""
    is_live: bool = False


@router.get("")
def list_accounts(user: User = Depends(get_current_user)):
    return AccountService.list_accounts(user.id)


@router.post("")
def link_account(payload: LinkAccountRequest, user: User = Depends(get_current_user)):
    return AccountService.link_account(
        user.id, payload.login, payload.password, payload.server, payload.broker, payload.is_live
    )


@router.delete("/{account_id}")
def remove_account(account_id: int, user: User = Depends(get_current_user)):
    return {"success": AccountService.remove_account(user.id, account_id)}
