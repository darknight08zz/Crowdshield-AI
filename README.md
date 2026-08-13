# 🛡️ CrowdShield — AI-Powered Stadium & Event Crowd Safety Platform

**CrowdShield** is an end-to-end AI platform engineered to monitor venue crowd mechanics, predict physical crushing risks using XGBoost machine learning, provide Explainable AI (XAI) diagnostics, and orchestrate emergency interventions across Web Command Dashboards and Mobile Surfaces.

---

## 🏗️ Platform System Architecture

```text
                               ┌────────────────────────────────────────┐
                               │     Control Room Web Dashboard         │
                               │   (Next.js 14, Tailwind, Leaflet/SVG)  │
                               └──────────────────┬─────────────────────┘
                                                  │ Supabase Realtime CDC
                                                  ▼
┌───────────────────────────┐     ┌─────────────────────────────────────┐     ┌───────────────────────────┐
│   Citizen Mobile Surface  │────▶│    FastAPI & AI XGBoost Engine      │◀────│ Field Officer Surface     │
│   (Expo SDK 54, React Native) │     │ (Feature Extraction, XAI, What-If)  │     │ (Task Dispatch, Triage)   │
└───────────────────────────┘     └──────────────────┬──────────────────┘     └───────────────────────────┘
                                                     │ PostgreSQL / Supabase
                                                     ▼
                                          ┌──────────────────────┐
                                          │ Firebase Admin FCM   │
                                          │ Push Notifications   │
                                          └──────────────────────┘
```

---

## 📦 Project Directory Overview

| Directory | Role / Stack | Quick Start Command |
| :--- | :--- | :--- |
| **`/backend`** | FastAPI REST & Realtime Backend, XGBoost Risk Model, SQLAlchemy | `cd backend && uvicorn app.main:app --reload` |
| **`/web`** | Control Room Web Dashboard (Next.js 14, Tailwind, Leaflet/SVG) | `cd web && npm run dev` |
| **`/mobile`** | Cross-Platform Citizen & Officer App (Expo SDK 54, React Native) | `cd mobile && npx expo start` |

---

## ⚡ Quick Start Instructions

### 1. Start the Backend API (FastAPI + AI Engine)
```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Open API Docs at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Start the Control Room Web Dashboard (Next.js)
```bash
cd web
npm install
npm run dev
```
- Open Dashboard at: [http://localhost:3000](http://localhost:3000)

### 3. Start the Mobile App (Expo SDK 54)
```bash
cd mobile
npm install
npx expo start
```
- Scan QR code with **Expo Go** on your physical phone.

---

## 📚 Complete Project Documentation

For phase-by-phase implementation logs, test suite verification results, database schemas, and production readiness matrices:
- Refer to [PROJECT_PHASES_LOG.md](./PROJECT_PHASES_LOG.md)
- Web Dashboard Setup: [web/README.md](./web/README.md)
- Mobile Application Setup: [mobile/README.md](./mobile/README.md)
