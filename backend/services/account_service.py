"""account_service.py - link/list/remove the user's MT5 trading accounts.
Passwords are encrypted before they touch the database (security/encryption.py)
and are only ever decrypted in-memory when a bot worker needs to log in."""
from database.database import SessionLocal
from database.repositories import accounts as accounts_repo
from security.encryption import encrypt_value, decrypt_value


def _public(account):
    return {
        "id": account.id,
        "login": account.login,
        "server": account.server,
        "broker": account.broker,
        "is_live": account.is_live,
        "is_active": account.is_active,
    }


class AccountService:
    @staticmethod
    def list_accounts(user_id: int):
        db = SessionLocal()
        try:
            return [_public(a) for a in accounts_repo.list_for_user(db, user_id)]
        finally:
            db.close()

    @staticmethod
    def link_account(user_id: int, login: str, password: str, server: str,
                      broker: str = "", is_live: bool = False):
        db = SessionLocal()
        try:
            encrypted = encrypt_value(password)
            account = accounts_repo.create(
                db, user_id=user_id, login=login, encrypted_password=encrypted,
                server=server, broker=broker, is_live=is_live,
            )
            return _public(account)
        finally:
            db.close()

    @staticmethod
    def remove_account(user_id: int, account_id: int) -> bool:
        db = SessionLocal()
        try:
            return accounts_repo.delete(db, user_id, account_id)
        finally:
            db.close()

    @staticmethod
    def get_credentials(user_id: int, account_id: int):
        """Internal use only (trading engine) - returns the decrypted password."""
        db = SessionLocal()
        try:
            account = accounts_repo.get(db, user_id, account_id)
            if not account:
                return None
            return {
                "login": account.login,
                "password": decrypt_value(account.encrypted_password),
                "server": account.server,
            }
        finally:
            db.close()
