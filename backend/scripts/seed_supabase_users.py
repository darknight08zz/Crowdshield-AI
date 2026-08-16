#!/usr/bin/env python3
import sys
import os
from uuid import uuid4

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import app.models
from app.core.database import SessionLocal, engine, Base
from app.models.user import User, UserRoleEnum, AccountStatusEnum
from app.core.security import hash_password
from app.core.config import settings

SUPABASE_DB_URL = settings.DATABASE_URL


def seed_users():
    print("Connecting to Supabase PostgreSQL database...")
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    supa_engine = create_engine(SUPABASE_DB_URL, pool_pre_ping=True)
    SupaSession = sessionmaker(autocommit=False, autoflush=False, bind=supa_engine)

    try:
        Base.metadata.create_all(bind=supa_engine)
        print("Schema tables created / verified on Supabase.")
    except Exception as e:
        print(f"Table creation note: {e}")

    db = SupaSession()
    try:
        users_to_seed = [
            {
                "email": "admin@crowdshield.gov",
                "name": "System Administrator",
                "role": UserRoleEnum.SYSTEM_ADMIN,
                "password": "AdminPassword123!"
            },
            {
                "email": "eventadmin@crowdshield.gov",
                "name": "Event Director",
                "role": UserRoleEnum.EVENT_ADMIN,
                "password": "EventAdminPassword123!"
            },
            {
                "email": "operator@crowdshield.gov",
                "name": "Control Room Operator",
                "role": UserRoleEnum.OPERATOR,
                "password": "OperatorPassword123!"
            }
        ]

        for u_info in users_to_seed:
            existing = db.query(User).filter(User.email == u_info["email"]).first()
            hashed_pass = hash_password(u_info["password"])
            if existing:
                existing.name = u_info["name"]
                existing.role = u_info["role"]
                existing.password_hash = hashed_pass
                existing.account_status = AccountStatusEnum.ACTIVE.value
                existing.is_active = True
                print(f" Updated existing account: {u_info['email']} (Role: {u_info['role'].value})")
            else:
                new_user = User(
                    id=uuid4(),
                    email=u_info["email"],
                    name=u_info["name"],
                    role=u_info["role"],
                    password_hash=hashed_pass,
                    account_status=AccountStatusEnum.ACTIVE.value,
                    is_active=True
                )
                db.add(new_user)
                print(f" Created new account: {u_info['email']} (Role: {u_info['role'].value})")

        db.commit()
        print("\n=======================================================")
        print(" [OK] SUPABASE USERS SEEDED SUCCESSFULLY!")
        print("=======================================================")
        print(" System Admin  : admin@crowdshield.gov / AdminPassword123!")
        print(" Event Admin   : eventadmin@crowdshield.gov / EventAdminPassword123!")
        print(" Operator      : operator@crowdshield.gov / OperatorPassword123!")
        print("=======================================================\n")
    except Exception as e:
        db.rollback()
        print(f"Error seeding Supabase database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
