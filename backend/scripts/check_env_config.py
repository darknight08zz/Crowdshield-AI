#!/usr/bin/env python3
"""
Environment Variable & Supabase Connectivity Health Check
--------------------------------------------------------
Safely checks configuration loading and Supabase/Database readiness
without printing any secret values into logs or terminal outputs.
"""

import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings

def check_environment():
    print("==================================================")
    print(" CROWDSHIELD ENVIRONMENT & SUPABASE HEALTH CHECK ")
    print("==================================================")

    # 1. Config Loading Verification
    print(f"Project Name   : {settings.PROJECT_NAME}")
    print(f"Environment    : {settings.ENV}")
    print(f"Host / Port    : {settings.HOST}:{settings.PORT}")
    print(f"Config Load    : PASS")
    print("--------------------------------------------------")

    # 2. Required Variable Status (Never print values, only SET or MISSING)
    def check_var(val: str, placeholder_substr="YOUR_"):
        if not val or placeholder_substr in val:
            return "MISSING (Needs manual population)"
        return "SET"

    supa_url_status = check_var(settings.SUPABASE_URL)
    supa_anon_status = check_var(settings.SUPABASE_ANON_KEY)
    supa_role_status = check_var(settings.SUPABASE_SERVICE_ROLE_KEY)
    supa_jwt_status = check_var(settings.SUPABASE_JWT_SECRET)
    db_url_status = check_var(settings.DATABASE_URL)

    print("VARIABLE STATUS:")
    print(f" - SUPABASE_URL           : {supa_url_status}")
    print(f" - SUPABASE_ANON_KEY       : {supa_anon_status}")
    print(f" - SUPABASE_SERVICE_ROLE_KEY: {supa_role_status}")
    print(f" - SUPABASE_JWT_SECRET    : {supa_jwt_status}")
    print(f" - DATABASE_URL           : {db_url_status}")
    print("--------------------------------------------------")

    # 3. Database Connectivity Check
    db_url = settings.DATABASE_URL
    if db_url and "YOUR_" not in db_url:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {})
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("Database Connectivity Check : PASS")
        except Exception as e:
            print(f"Database Connectivity Check : FAIL ({e})")
    else:
        print("Database Connectivity Check : SKIPPED (DATABASE_URL not configured)")

    # 4. Supabase Client Initialization Check
    if settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and "YOUR_" not in settings.SUPABASE_URL:
        try:
            from supabase import create_client
            client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
            print("Supabase Client Init Check  : PASS")
        except Exception as e:
            print(f"Supabase Client Init Check  : FAIL ({e})")
    else:
        print("Supabase Client Init Check  : SKIPPED (Credentials missing in local .env)")

    print("==================================================")

if __name__ == "__main__":
    check_environment()
