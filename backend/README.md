# 🛡️ CrowdShield Backend API

FastAPI-powered backend and AI risk engine service for **CrowdShield**, a real-time crowd-safety and stampede prevention platform.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
* **Python 3.11+** installed
* **PostgreSQL / Supabase Account**

### 2. Environment Setup

From the `backend/` directory, create and activate a Python virtual environment:

```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

Install all dependencies:

```bash
pip install -r requirements.txt
```

### 3. Environment Variables Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Fill in your `.env` configuration file:

```env
# Server Settings
PROJECT_NAME="CrowdShield API"
VERSION="1.0.0"
ENV="development"
HOST="0.0.0.0"
PORT="8000"

# Supabase Credentials (from Supabase Dashboard -> Project Settings -> API)
SUPABASE_URL="https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY"
SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_JWT_SECRET="YOUR_SUPABASE_JWT_SECRET"

# Database Connection URI (use Port 5432 Direct Session Mode pooler URL for SQLAlchemy & DDL migrations)
DATABASE_URL="postgresql://postgres.YOUR_PROJECT_ID:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres"
```

---

## 🗄️ Database Setup & Migrations

### 1. Execute SQL Migration
Copy the contents of `migrations/001_initial_schema.sql` and run it inside your **Supabase SQL Editor**. This sets up:
* Enums: `user_role`, `gate_type`, `gate_status`, `incident_status`, `assignment_status`, `recommendation_status`
* Core Tables: `users`, `events`, `zones`, `gates`, `incidents`, `officer_assignments`, `ai_recommendations`, `audit_log`
* Foreign keys with cascading actions & performance indexes on `zone_id` and `event_id`
* Row Level Security (RLS) policies

### 2. Seed Mock Data for Local Development
Populate the database with 1 event, 4 zones, 6 choke-point gates, 5 role-based users, 1 incident, and 1 AI recommendation:

```powershell
python scripts/seed.py
```

---

## 🏃 Running the Server

Start the FastAPI backend with hot-reload enabled:

```powershell
uvicorn app.main:app --reload --port 8000
```

* **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🔐 Role-Based Access Control (RBAC) & Endpoints

All protected endpoints expect a Supabase JWT in the `Authorization` header: `Bearer <JWT_TOKEN>`.

### 👥 5 Platform Roles
1. `citizen` — Safety map view, report incidents
2. `field_officer` — Receive dispatched tasks, update task execution status
3. `operator` — Control Room live monitoring, approve/modify/reject AI recommendations, gate overrides
4. `event_admin` — Configure events, zones, gates, and venue geometry
5. `system_admin` — Global configuration, RBAC, and full forensic audit log inspection

### 📌 API Route Overview
* `GET /api/v1/auth/me` — Decoded profile payload from Supabase JWT
* `POST /api/v1/citizens/incidents` — Submit crowd surge / medical incident report
* `GET /api/v1/citizens/zones` — Get live zone crowd density & safety risk map
* `GET /api/v1/officers/assignments` — View assigned field tasks
* `PATCH /api/v1/officers/assignments/{id}/status` — Update task status (`acknowledged`, `in_progress`, `completed`)
* `GET /api/v1/operator/dashboard` — Unified real-time Control Room telemetry
* `POST /api/v1/operator/recommendations/{id}/action` — Approve, Modify, or Reject AI recommendations
* `POST /api/v1/operator/dispatch` — Dispatch field officers to a zone
* `PATCH /api/v1/operator/gates/{id}/status` — Manual gate choke-point status override
* `POST /api/v1/admin/events` — Create new event
* `POST /api/v1/admin/zones` — Define safety zone polygon
* `POST /api/v1/admin/gates` — Register choke-point gate
* `GET /api/v1/admin/audit-logs` — Forensic audit trail

---

## ☁️ Production Deployment (Railway / Render)

This repository uses native Python buildpacks (**No Dockerfile required**).

1. Connect your GitHub repository to Railway or Render.
2. Set Build Command: `pip install -r requirements.txt`
3. Set Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variables from your production `.env`.
