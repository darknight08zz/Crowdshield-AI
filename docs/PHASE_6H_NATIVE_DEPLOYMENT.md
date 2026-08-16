# CrowdShield — Phase 6H Native Windows Deployment Guide (ZERO DOCKER)

## Architecture Overview

CrowdShield is engineered to run natively on Windows without containerization overhead. Docker is **not required** for the CrowdShield deployment configuration.

The native stack comprises:
- **FastAPI / Uvicorn**: Asynchronous REST & WebSocket backend engine.
- **Next.js (Turbopack)**: React-based real-time operator & field dashboard.
- **SQLAlchemy & PostgreSQL / Supabase**: Relational persistence engine with asynchronous worker queue.
- **YOLOv8 + ByteTrack + PyTorch**: Native computer vision and risk forecasting engine.
- **PowerShell Process Manager**: Native startup, shutdown, and health diagnostic orchestration scripts.

```text
                  ┌──────────────────────┐
                  │   CCTV / RTSP /      │
                  │   Video / Webcam     │
                  └──────────┬───────────┘
                             ↓
                  LatestFrameBuffer
                             ↓
                  YOLOv8 + ByteTrack
                             ↓
                  CV Telemetry
                             ↓
                  Physics Risk Engine
                             ↓
                  Temporal Feature Buffer
                             ↓
                  v2.0.0 Temporal AI
                             ↓
                  Early Warning Engine
                             ↓
                RealtimeInferenceOrchestrator
                             │
                 ┌───────────┴───────────┐
                 ↓                       ↓
          WebSocket / REST       AsyncPersistenceManager
                 ↓                       ↓
          Next.js Dashboard       PostgreSQL/Supabase
                 │
        ┌────────┴─────────┐
        ↓                  ↓
   Incident Center     Field Center
        │                  │
        └────────┬─────────┘
                 ↓
             Audit Logs
                 ↓
        Security / RBAC / Request ID

        ─────────────────────────────
        Native Windows Infrastructure
        ─────────────────────────────
        PowerShell startup:  .\scripts\start_crowdshield.ps1
        PowerShell shutdown: .\scripts\stop_crowdshield.ps1
        Status check:        .\scripts\status_crowdshield.ps1
        Health API:          http://localhost:8000/health
        Readiness API:       http://localhost:8000/readiness
```

---

## 1. Prerequisites

Before deploying CrowdShield natively on Windows, ensure the following software dependencies are installed:
- **Python 3.11+** (with `pip` and virtual environment support)
- **Node.js v18+ & npm v9+**
- **PowerShell 5.1 / 7+**
- **PostgreSQL Database** or **Supabase Instance**

*Note: Docker is not required for the CrowdShield deployment configuration.*

---

## 2. Environment Configuration

### Backend Configuration (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` (or root `.env`):
```env
PROJECT_NAME="CrowdShield API"
VERSION="1.0.0"
ENV="development" # Set to "production" for production deployment
DEBUG="false"
HOST="0.0.0.0"
PORT="8000"
LOG_LEVEL="INFO"
LOG_FILE_PATH="logs/application.log"
REALTIME_ENABLED="true"

# Security & CORS Origins
CORS_ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000"

# Supabase / JWT Credentials
SUPABASE_URL="https://YOUR_PROJECT_ID.supabase.co"
SUPABASE_ANON_KEY="YOUR_SUPABASE_ANON_KEY"
SUPABASE_SERVICE_ROLE_KEY="YOUR_SUPABASE_SERVICE_ROLE_KEY"
SUPABASE_JWT_SECRET="YOUR_SUPABASE_JWT_SECRET"

# Database Connection URI
DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@db.YOUR_PROJECT_ID.supabase.co:5432/postgres"

# Connection Pooling & Persistence Queue Settings
DATABASE_POOL_SIZE="10"
DATABASE_MAX_OVERFLOW="20"
REALTIME_PERSISTENCE_QUEUE_MAXSIZE="100"
REALTIME_PERSISTENCE_WORKERS="2"
```

### Frontend Configuration (`web/.env.local`)

Copy `web/.env.example` to `web/.env.local`:
```env
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000/api/v1/realtime/stream
```

---

## 3. Platform Execution & Scripts

### Full System Orchestration Startup
To start both Backend and Frontend servers automatically with health probing:
```powershell
.\scripts\start_crowdshield.ps1
```

### System Health & Status Diagnostic Check
To inspect real-time component health (Database, Persistence, AI Engine, Camera, Frontend):
```powershell
.\scripts\status_crowdshield.ps1
```

### Graceful Platform Shutdown
To cleanly drain persistence queues and terminate CrowdShield processes:
```powershell
.\scripts\stop_crowdshield.ps1
```

### Individual Service Control

#### Backend Only
```powershell
.\backend\scripts\start_backend.ps1
```

#### Frontend Only
```powershell
.\web\scripts\start_frontend.ps1
```

#### Deployment Smoke Test
```powershell
$env:PYTHONPATH="backend"
python backend/scripts/smoke_test_deployment.py
```

---

## 4. Health & Observability Endpoints

- **Liveness Probe**: `GET http://localhost:8000/health` (Lightweight, no DB queries)
- **Readiness Probe**: `GET http://localhost:8000/readiness` (Comprehensive component diagnostics)
- **Real-Time Stream**: `WS ws://localhost:8000/api/v1/realtime/stream`

---

## 5. Troubleshooting & FAQ

| Issue | Resolution |
| :--- | :--- |
| **Port 8000 / 3000 in use** | Run `.\scripts\stop_crowdshield.ps1` to stop prior CrowdShield instances. |
| **Database Connection Warning** | Verify `DATABASE_URL` credentials in `.env` and firewall rules for port 5432. |
| **Persistence Status `PERSISTENCE_DEGRADED`** | Database connectivity was temporarily lost. The inference engine continues operating; workers auto-retry. |
| **YOLO model missing** | `yolov8n.pt` will automatically download on first execution if not present in backend directory. |

---

## 6. Known Limitations & Validation Boundaries

```text
model_status:         PROTOTYPE
label_type:           PHYSICS_DEFINED_PROXY
ground_truth_status:  NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED
generalization_status: INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION
```

1. **Software Engineering Validation**: Native deployment and operational infrastructure validated for the current prototype environment.
2. **Empirical Benchmarks**: Performance measurements (~11.69 FPS at 640x640, ~20.27 FPS at 320x320) are host-hardware dependent (measured on AMD Ryzen 5 5500U, CUDA unavailable).
3. **No Operational Safety Claims**: This prototype is not clinically or operationally validated for emergency management without human operator oversight.
