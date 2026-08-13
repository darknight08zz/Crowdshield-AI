#!/usr/bin/env python3
"""
CROWDSHIELD SYSTEM ADMINISTRATOR BOOTSTRAP SCRIPT
=================================================
Initializes the initial System Administrator account via a secure CLI script.
This script is executed manually during deployment and cannot be called via any API.
"""

import sys
import os
import argparse
import secrets
import string
from uuid import uuid4

# Add backend root to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app.models
from app.core.database import SessionLocal, engine, Base
from app.models.user import User, UserRoleEnum, AccountStatusEnum
from app.core.security import hash_password
from app.core.audit import log_audit_event




def generate_temp_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def bootstrap_system_admin(email: str, name: str, password: str = None, db = None):
    Base.metadata.create_all(bind=engine)
    close_db = False

    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        temp_pass = None
        if not password:
            temp_pass = generate_temp_password(16)
            password = temp_pass

        hashed_pass = hash_password(password)

        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            existing_user.role = UserRoleEnum.SYSTEM_ADMIN
            existing_user.name = name
            existing_user.password_hash = hashed_pass
            existing_user.account_status = AccountStatusEnum.ACTIVE.value
            existing_user.is_active = True
            db.commit()
            db.refresh(existing_user)
            user_id = existing_user.id
            action_type = "BOOTSTRAP_SYSTEM_ADMIN_UPDATED"
        else:
            user_id = uuid4()
            sysadmin = User(
                id=user_id,
                email=email,
                name=name,
                role=UserRoleEnum.SYSTEM_ADMIN,
                password_hash=hashed_pass,
                account_status=AccountStatusEnum.ACTIVE.value,
                is_active=True
            )
            db.add(sysadmin)
            db.commit()
            action_type = "BOOTSTRAP_SYSTEM_ADMIN_CREATED"

        log_audit_event(
            db=db,
            action=action_type,
            target=f"user:{user_id}",
            after_state={"email": email, "role": "system_admin", "account_status": "active"}
        )

        print("\n=======================================================")
        print(" [OK] CROWDSHIELD SYSTEM ADMINISTRATOR INITIALIZED")
        print("=======================================================")
        print(f" User ID : {user_id}")
        print(f" Name    : {name}")
        print(f" Email   : {email}")
        print(f" Role    : system_admin")
        print(f" Status  : active")
        if temp_pass:
            print("-------------------------------------------------------")
            print(f" Generated Password : {temp_pass}")
            print(" IMPORTANT: Save this password now! It will NOT be shown again.")
        print("=======================================================\n")

    except Exception as e:
        db.rollback()
        print(f"[!] Error bootstrapping System Administrator: {e}")
        raise e
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap CrowdShield System Administrator Account")
    parser.add_argument("--email", default=os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@crowdshield.gov"), help="Admin email address")
    parser.add_argument("--name", default=os.getenv("BOOTSTRAP_ADMIN_NAME", "System Administrator"), help="Admin full name")
    parser.add_argument("--password", default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", None), help="Optional initial password")

    args = parser.parse_args()
    bootstrap_system_admin(email=args.email, name=args.name, password=args.password)
