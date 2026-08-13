# 🛡️ CrowdShield — Control Room Web Dashboard

A high-performance Next.js 14 web application designed for **Control Room Command Operators** monitoring live venue crowds, AI risk scores, physical choke-point gates, and field officer deployments.

---

## 🚀 Technologies Used

- **Framework**: Next.js 14 (App Router, React 19, TypeScript)
- **Styling**: Tailwind CSS v4, Lucide React Icons
- **Realtime CDC**: Supabase Realtime WebSocket client (`@supabase/supabase-js`)
- **Maps**: Dual interactive map rendering (Free **OpenStreetMap Leaflet.js** + Vector SVG Schematic + Mapbox GL JS)
- **State & Data**: `@tanstack/react-query`, native React hooks

---

## 📂 Project Structure

```text
web/
├── src/
│   ├── app/
│   │   ├── overview/           # Main Command Overview Dashboard & Interactive Map
│   │   ├── zones/[id]/         # Sector Risk Detail, XAI Breakdowns & What-If Simulator
│   │   ├── incidents/          # Real-time Incident Stream & Triage Drawer
│   │   ├── officers/           # Deployed Field Officer Roster & Telemetry
│   │   ├── verify/             # Post-Dispatch Intervention Verification Loop
│   │   └── page.tsx            # Root redirect to /overview
│   ├── components/
│   │   ├── dashboard/          # VectorMap, LeafletMap, InteractiveMap switcher
│   │   ├── layout/             # Header, Sidebar, DashboardLayout shell
│   │   └── ui/                 # Loading skeletons & metric cards
│   └── lib/
│       ├── api.ts              # FastAPI backend client wrapper + mock fallback data
│       ├── constants.ts        # Global risk thresholds & color definitions
│       └── supabase/client.ts  # Browser-side Supabase Realtime client
├── .env.local                  # Environment variables
└── package.json
```

---

## 🛠️ Setup & Local Installation

### 1. Install Dependencies
```bash
cd web
npm install
```

### 2. Configure Environment Variables (`.env.local`)
Ensure your `web/.env.local` contains:

```env
# Supabase Configuration
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_ID.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_SUPABASE_ANON_KEY

# FastAPI Backend Endpoint
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1

# Optional Mapbox Access Token (Leaflet OpenStreetMap fallback runs without keys)
NEXT_PUBLIC_MAPBOX_TOKEN=pk.eyJ1IjoiY3Jvd2RzaGllbGQiLCJhIjoiY2xwbGFjZWhvbGRlciJ9.placeholder
```

### 3. Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 4. Build for Production
```bash
npm run build
npm run start
```

---

## 🎯 Key Operational Workflows

### 1. Command Overview (`/overview`)
- View total venue crowd estimate and max sector risk score.
- Toggle between **SVG Stadium Schematic** and **OpenStreetMap (Leaflet)** map layers.
- Real-time WebSocket CDC automatically updates zone colors (Green, Yellow, Orange, Red) live as risk changes.

### 2. Zone Risk Detail & AI Simulator (`/zones/z-1`)
- View 5-minute predicted risk projection and XAI explainable crowd diagnostic factors.
- Use **RUN WHAT-IF RISK SIMULATION** to calculate projected risk reduction prior to dispatch.
- Click **APPROVE** to confirm operator directive with automated officer assignment & citizen push alerts.

### 3. Incidents Stream (`/incidents`)
- Filter incoming citizen/officer incidents by status (`pending`, `verified`, `resolving`, `resolved`, `false_alarm`).
- Inspect GPS location coordinates, photo evidence, and update triage status.

### 4. Field Officer Roster (`/officers`)
- Monitor live officer battery levels, active sector assignments, and task completion states.

### 5. Intervention Verification (`/verify`)
- Review pre vs post-dispatch risk reduction metrics to verify mitigation success.

---

## ☁️ Deploying to Vercel

1. Import the `/web` repository in your [Vercel Dashboard](https://vercel.com).
2. Set the **Root Directory** to `web`.
3. Add `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, and `NEXT_PUBLIC_API_BASE_URL` in **Environment Variables**.
4. Click **Deploy**.
