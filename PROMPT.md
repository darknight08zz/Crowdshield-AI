# CrowdShield — AI Agent Build Prompts

This is a phased set of prompts you can paste directly into your coding agent (Antigravity, Claude Code, Cursor, etc.), one phase at a time. Each phase builds on the last. Do not skip ahead — a weak foundation (auth, schema, roles) will break every module built on top of it later.

---

## 0. Recommended Tech Stack (and why)

You have three deployable surfaces: **Citizen + Field Officer mobile app** (Play Store), **Control Room / Event Admin / System Admin web app**, and a **backend + AI engine**. No Docker — everything below runs on managed platforms with native buildpacks, so your agent never has to write a Dockerfile.

| Layer | Choice | Why |
|---|---|---|
| Mobile app | **React Native + Expo (TypeScript)** | Single codebase compiles to a real Play Store `.aab`, no native Android/Kotlin needed, matches your React/TS background |
| Web app | **Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui** | You already use this stack; SSR is useful for the live dashboard |
| Backend API | **FastAPI (Python)** | Matches your Python strength, best for the AI engine living in the same service, async-native for websockets |
| AI / ML | **XGBoost (risk scoring) + scikit-learn (feature pipeline)**, served from the same FastAPI service | You already know XGBoost; no need for a separate ML microservice at MVP scale |
| Database | **PostgreSQL via Supabase** | Relational data (users, roles, zones, gates, incidents) + built-in Auth + Row Level Security for RBAC + Realtime channels, no server to manage |
| Realtime (live map, alerts) | **Supabase Realtime (Postgres change streams) or native FastAPI WebSockets** | Avoid standing up Redis/Kafka for MVP; Postgres LISTEN/NOTIFY via Supabase is enough |
| Push notifications | **Firebase Cloud Messaging (FCM)** | Required for real Play Store alerts to Citizens/Officers when app is backgrounded |
| Maps | **Leaflet / OpenStreetMap (web) + react-native-maps (mobile)** | 100% free zero API-cost map tiles and zone/polygon overlays |
| Backend hosting | **Railway or Render** (native Python buildpack) | No Dockerfile needed, auto-deploys from GitHub |
| Web hosting | **Vercel** | Native Next.js support |
| Mobile build/release | **Expo EAS Build + EAS Submit** | Builds the Play Store `.aab` and can submit directly to Play Console |

Give your agent this table as context before every phase below — paste Phase 1's prompt with this table included the first time.

---

## 1. Master Context Prompt (paste this first, in every new agent session)

```
You are helping me build CrowdShield, a real crowd-safety platform I intend to actually deploy — not a toy demo. Treat every module as production-grade: proper error handling, input validation, typed interfaces, and no hardcoded secrets.

PROJECT SUMMARY
CrowdShield helps event organizers prevent crowd crushes/stampedes at large public events (festivals, pilgrimages, concerts). It has three deployable surfaces:
1. A citizen-facing MOBILE APP (Play Store) — safety status, live risk map, safer-route suggestions, incident reporting, emergency help.
2. A field-officer MOBILE APP surface (same app, different role) — assigned zone, task list, incident verification.
3. A CONTROL ROOM WEB APP — live monitoring dashboard, AI risk predictions with explainability, what-if simulation, approve/reject/dispatch actions, plus Event Admin (venue/gate/zone config) and System Admin (RBAC, audit logs, platform health) sub-modules.

CORE LOOP: Citizen reports incident → AI engine predicts risk trajectory → Control Room Operator sees explainable recommendation and runs a what-if simulation → Operator approves/modifies/rejects → dispatch fires to Field Officers (task) and Citizens (alert + rerouted map) → system verifies outcome (before/after risk numbers) → logged to audit trail.

FIVE ROLES: Citizen, Field Officer, Control-Room Operator, Event Administrator, System Administrator. MVP priority order: Citizen > Control-Room Operator > Field Officer are the three roles to build and demo fully. Event Admin and System Admin exist as supporting config modules — functional but lower visual polish priority.

TECH STACK (do not deviate without telling me why):
- Mobile: React Native + Expo, TypeScript
- Web: Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui
- Backend: FastAPI (Python 3.11+), async endpoints
- AI: XGBoost + scikit-learn inside the FastAPI service (no separate ML microservice for MVP)
- Database + Auth + Realtime: Supabase (Postgres, Row Level Security, Realtime channels)
- Push notifications: Firebase Cloud Messaging
- Maps: Leaflet / OpenStreetMap (web) and react-native-maps (mobile)
- No Docker anywhere. Backend deploys to Railway/Render via native Python buildpack. Web deploys to Vercel. Mobile builds via Expo EAS.

WORKING STYLE:
- Before writing code for a module, first output a short plan: what files you'll create, what the data model touches, what API endpoints it needs. Wait for me to say "go" only if I ask for a plan explicitly — otherwise proceed but keep the plan visible in comments at the top of the main file.
- Every backend endpoint needs a Pydantic request/response schema, role-based access check, and a docstring stating who is allowed to call it.
- Every database table needs a migration file, not an ad-hoc `CREATE TABLE`.
- Explain, in plain language after each phase, what I need to do manually (e.g., create a Supabase project, add an API key to `.env`, enable a Play Console setting) — you cannot do these steps for me.
- Never invent fake data silently in production code paths — mock data only inside clearly labeled `/seed` or `/dev` scripts.

Confirm you've understood this context, then wait for my next message where I'll give you Phase 1.
```

---

## 2. Phase 1 — Backend Foundation: Schema, Auth, RBAC

Your agent needs this before touching UI. This is the phase most people skip and regret.

```
PHASE 1: Backend Foundation.

Set up the FastAPI backend project structure and the core data model. Do the following:

1. PROJECT STRUCTURE
Create a `/backend` folder with this layout:
   backend/
     app/
       main.py
       core/          (config, security, dependencies)
       models/        (SQLAlchemy or Supabase schema definitions)
       schemas/       (Pydantic request/response models)
       api/
         v1/
           citizens.py
           officers.py
           operator.py
           admin.py
           auth.py
       services/      (business logic, kept separate from routes)
       ai/            (risk model, explainability, simulation — empty for now, Phase 2 fills this)
     migrations/
     requirements.txt
     .env.example

2. DATABASE SCHEMA (Postgres, via Supabase)
Design and write SQL migration files for these tables at minimum:
   - users (id, role enum[citizen, field_officer, operator, event_admin, system_admin], name, phone/email, created_at)
   - events (id, name, date, venue, status)
   - zones (id, event_id, name, capacity, current_density, risk_score, geo_polygon)
   - gates (id, event_id, zone_id, type[entry/exit], capacity_per_min, status[open/restricted/closed])
   - incidents (id, reporter_id, zone_id, type, description, media_url, status[reported/verified/false_alarm/resolved], created_at)
   - officer_assignments (id, officer_id, zone_id, task_description, status, created_at)
   - ai_recommendations (id, zone_id, risk_score, predicted_risk_5min, recommended_actions jsonb, status[pending/approved/modified/rejected], created_at)
   - audit_log (id, actor_id, action, target, before_state jsonb, after_state jsonb, created_at)
Explain your foreign key choices and add indexes on any column you expect to be queried by zone_id or event_id frequently (that will be constantly, given the live dashboard).

3. AUTH + RBAC
Use Supabase Auth for identity (phone/email + password, or magic link for MVP). Implement a FastAPI dependency `get_current_user()` that validates the Supabase JWT on every request and attaches `user.role`. Implement a `require_role(*roles)` dependency factory so each endpoint can declare exactly which roles may call it, e.g. `Depends(require_role("operator", "system_admin"))`. Write this in `core/security.py`.

4. SEED SCRIPT
Write a `/backend/scripts/seed.py` that creates one fake event, 4 zones, 6 gates, and one user of each role, purely for local development — clearly commented as dev-only.

5. WHAT I NEED TO DO MANUALLY
At the end, list the exact manual steps for me: creating the Supabase project, running the migration, copying the connection string and anon/service keys into `.env`, and installing dependencies locally.

Do not build any AI/ML logic yet — that's Phase 2. Do not build any frontend yet.
```

---

## 3. Phase 2 — AI Engine: Risk Prediction, Explainability, What-If Simulation

This is CrowdShield's actual differentiator — spend the most agent-iteration budget here.

```
PHASE 2: AI Risk Engine.

Building on the Phase 1 backend, implement the AI engine inside `backend/app/ai/`. This is the core differentiator of CrowdShield, so build it properly, not as a stub.

1. FEATURE PIPELINE
Write `ai/features.py` that computes, per zone, a feature vector from raw sensor/report inputs: current density (%), inflow rate, outflow rate, average pedestrian speed, direction-conflict score, gate capacity utilization, incident count in the last 10 minutes, a `reverse_flow_ratio` (share of tracked movement going against the designated flow direction for that zone/route), and a `blockage_score` (derived from a sustained speed-drop concentrated at a single sub-area rather than distributed across the zone, which distinguishes "route physically blocked" from "just generally congested"). Since I don't have real camera/sensor feeds yet, write a `simulate_sensor_reading(zone_id)` function that generates plausible synthetic values so the rest of the pipeline can be developed and demoed end-to-end — comment clearly that this gets replaced by real sensor ingestion later, and design the function signature so swapping it out doesn't touch any other file.

1b. ABNORMAL BEHAVIOR CLASSIFICATION
Add `ai/behavior.py` that classifies the current feature vector into one of a small fixed set of situation types, not just a single risk number: `NORMAL`, `SURGE` (density+inflow spiking), `REVERSE_FLOW` (blockage_score/reverse_flow_ratio high), `STAGNATION` (density high but speed near zero across the whole zone, distinct from a blockage), and `DISPERSED_INCIDENT_CLUSTER` (multiple incident reports clustered in time/location without a density spike — e.g. medical emergencies). This classification feeds both the explanation text and which recommended actions are relevant, since "restrict a gate" is the right call for SURGE but wrong for STAGNATION.

2. RISK MODEL
Write `ai/risk_model.py` using XGBoost (or a simple logistic/gradient-boosted regressor if XGBoost is overkill for the data volume) that outputs: current_risk_score (0-100) and predicted_risk_5min (0-100). Since there's no historical incident dataset yet, generate a synthetic training set with a documented, clearly-labeled function `generate_synthetic_training_data()` that encodes reasonable domain rules (e.g., risk rises sharply when inflow > outflow AND speed drops below a threshold). Train and pickle the model in a `train.py` script I can rerun. Explain in comments how I'd swap this for a model trained on real incident data later.

3. EXPLAINABLE AI
Write `ai/explain.py` that takes a risk score and its feature vector and returns a plain-language explanation, e.g. "Crowd inflow is exceeding outflow by 35% and pedestrian speed has dropped 24% in the last 3 minutes." Use SHAP values against the XGBoost model if feasible, falling back to a simple "which feature deviated most from its safe baseline" heuristic if SHAP adds too much complexity for MVP.

4. RECOMMENDATION ENGINE
Write `ai/recommend.py` that maps a risk state + behavior classification (from 1b) to a ranked list of recommended actions using rule-based logic keyed off which features are driving the risk. The action taxonomy must include at minimum: `RESTRICT_GATE`, `OPEN_ALTERNATE_GATE`, `REDIRECT_VISITORS`, `DEPLOY_OFFICERS(n)`, `ENFORCE_ONE_WAY_FLOW(route_id)`, and `ISSUE_PUBLIC_ANNOUNCEMENT`. `ENFORCE_ONE_WAY_FLOW` should be recommended specifically when `REVERSE_FLOW` is the dominant behavior classification, not offered generically. Keep this rule-based and interpretable — do not make this an opaque model, since Control Room Operators need to trust and audit it.

4b. ANNOUNCEMENT DRAFTING
Write `ai/announce.py` with a function `draft_announcement(situation_type, zone_name, recommended_action, language="en")` that generates the actual public-announcement text an operator would approve and broadcast (e.g., "Attention: Gate A is experiencing heavy congestion. Please proceed to Gate C. Do not push forward."). Start with template-based generation keyed off `situation_type` (fast, deterministic, no external API dependency for MVP) rather than calling an LLM live during an emergency — note in a comment that template-based is a deliberate reliability choice, not a shortcut. Support at least English + one additional language you and I agree on (e.g., Hindi) by keeping templates in a structured dict per language, not hardcoded strings, so more languages can be added without touching the function logic.

5. WHAT-IF SIMULATION
Write `ai/simulate.py` exposing a function `simulate_intervention(zone_id, proposed_action)` that re-runs the risk model with adjusted inputs (e.g., if "restrict Gate A" is proposed, reduce that gate's effective inflow in the feature vector; if `ENFORCE_ONE_WAY_FLOW` is proposed, reduce `reverse_flow_ratio` and `direction_conflict_score` in the feature vector) and returns projected_risk_after. This powers the "SIMULATE" button in the Control Room UI.

6. API ENDPOINTS
Expose these under `api/v1/operator.py`:
   - GET  /zones/{zone_id}/risk           → current + predicted risk + behavior classification + explanation
   - GET  /zones/{zone_id}/recommendation → ranked recommended actions (including drafted announcement text where relevant, in the requested language via a `?lang=` query param)
   - POST /zones/{zone_id}/simulate       → body: proposed action, returns projected risk
   - POST /recommendations/{id}/decide    → body: approve/modify/reject (operator can edit the drafted announcement text before approving), writes to audit_log and, if approved, fires dispatch (stub this as a TODO calling Phase 3's notification service)

7. TESTS
Write basic pytest tests for the feature pipeline, behavior classifier, risk model, and announcement drafter so I can verify the pipeline end-to-end without a frontend.

At the end, tell me plainly: which parts of this are production-ready today, and which parts are synthetic placeholders I MUST replace before a real deployment (be specific — I don't want to accidentally ship fake sensor data to a real event).
```

---

## 4. Phase 3 — Realtime Layer & Notifications

```
PHASE 3: Realtime + Notifications.

Building on Phases 1-2, add the realtime and push notification layer that connects the AI engine's output to actual devices.

1. REALTIME CHANNEL
Use Supabase Realtime (Postgres change data capture) so that whenever a row in `zones` (risk_score) or `ai_recommendations` or `incidents` changes, subscribed clients get pushed the update without polling. Write a small `services/realtime.py` helper documenting exactly which tables/channels the web dashboard and mobile app should subscribe to, and under what filter (e.g., mobile app only subscribes to its own event_id and nearby zones, not the whole platform).

2. DISPATCH SERVICE
Write `services/dispatch.py` with a function `dispatch_approved_action(recommendation_id)` that, when an Operator approves a recommendation:
   - creates rows in `officer_assignments` for the affected zone
   - creates a citizen-facing alert record (new table `alerts`: id, zone_id, message, severity, created_at)
   - triggers push notifications (see below)
   - writes to audit_log
Wire this into the `/recommendations/{id}/decide` endpoint from Phase 2.

3. PUSH NOTIFICATIONS (Firebase Cloud Messaging)
Write `services/push.py` using the Firebase Admin SDK to send FCM messages to Citizen devices in the affected zone and to assigned Field Officers. Add a `device_tokens` table (user_id, fcm_token, platform) and an endpoint `POST /devices/register` the mobile app calls on login to register its push token.

4. WHAT I NEED TO DO MANUALLY
List the manual steps: creating a Firebase project, downloading the service account JSON, enabling Cloud Messaging, and where the mobile app needs its `google-services.json` for Android.

Do not build mobile or web UI yet — that's Phases 4 and 5. This phase is backend-only.
```

---

## 5. Phase 4 — Mobile App (Citizen + Field Officer, Play Store target)

```
PHASE 4: Mobile App — Citizen and Field Officer surfaces.

Build the React Native (Expo, TypeScript) app that will eventually ship to the Play Store. It serves two roles from one codebase: Citizen and Field Officer, switching UI based on the logged-in user's role from Supabase Auth.

1. PROJECT SETUP
Initialize with `npx create-expo-app` (TypeScript template). Set up:
   - Navigation: React Navigation with a role-based root navigator (CitizenTabs vs OfficerTabs)
   - State: React Query for server state (fetching zones, incidents, tasks) + lightweight Zustand for local UI state
   - Supabase client configured for both REST calls and Realtime subscriptions
   - react-native-maps integration

2. CITIZEN SCREENS
   - Home: event safety status (color-coded SAFE/MODERATE/HIGH), current zone risk if location permission granted
   - Live Map: Interactive map (react-native-maps / tile grid canvas) with color-coded zone overlays (green/yellow/orange/red), gates, exits, recommended route — subscribe to Realtime zone updates so colors change live
   - Find Safe Route: input current location (or GPS), call backend for safest path considering current risk, render as a route line on the map
   - Report Incident: form with type (surge/medical/blocked path/other), description, photo/video upload (use Expo ImagePicker), auto-attaches GPS location, submits to `/incidents`
   - Emergency: static list of emergency contacts, nearest help point (from zones/gates data), one-tap call button
   - Push notification handling: foreground + background alert display using Expo Notifications wired to the FCM tokens from Phase 3, rendering the announcement text in the citizen's selected language

2b. MULTILINGUAL SUPPORT
Set up `expo-localization` + `i18n-js` (or `react-i18next`) with a language switcher in Settings, at minimum English + one additional language matching the backend's `ai/announce.py` languages from Phase 2. All static UI strings go through the i18n layer from day one, not hardcoded — retrofitting this later touches every screen. Server-sent content (alerts, announcements) should request the `?lang=` matching the user's selected app language when calling the backend.

3. FIELD OFFICER SCREENS
   - My Zone: assigned zone name + current risk level
   - Tasks: list of assigned tasks (from officer_assignments) with status checkboxes
   - Incident Verification: when an incident is routed to them, show a confirm/false-alarm/resolved flow with photo capture
   - Report: officer-side incident/status report form, same submission pipeline as citizen reports but tagged with officer role

4. AUTH FLOW
Phone or email + password login/signup via Supabase Auth. On successful login, register the device's FCM token via the Phase 3 endpoint. Store session securely using `expo-secure-store`, not AsyncStorage.

5. OFFLINE / DEGRADED NETWORK HANDLING
This app may be used in crowded venues with poor connectivity. Add basic offline queuing for incident reports (store locally, retry submission when connectivity returns) using a lightweight local queue — don't over-engineer this for MVP, but don't silently drop reports either.

Keep the UI clean and high-contrast — this app may be used in bright sunlight or by stressed users. Do not over-animate. After this phase, tell me exactly what's needed to test this on a real Android device (Expo Go vs a dev build) before we get to Play Store submission in the deployment phase.
```

---

## 6. Phase 5 — Web App: Control Room Operator Dashboard

```
PHASE 5: Web App — Control Room Operator Dashboard.

Build the Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui) web dashboard for the Control-Room Operator role — this is the most important screen in the whole product, build it with real care.

1. PROJECT SETUP
Initialize the Next.js app in `/web`. Set up Supabase client (server components use the service/anon key appropriately, never leak service key to client bundle), shadcn/ui components, Leaflet (react-leaflet / OpenStreetMap), and a `/lib/api.ts` wrapper around the FastAPI backend.

2. LAYOUT
Auth-gated layout that redirects non-operator/non-admin roles away. Sidebar navigation: Overview, Zone Detail, Incidents, Officers, Audit Log (Event Admin and System Admin sections come in Phase 6 but stub the nav links now).

3. OVERVIEW SCREEN
   - Overall risk summary banner
   - Grid of zone cards, color-coded by risk_score, live-updating via Supabase Realtime subscription (no polling)
   - Leaflet / OpenStreetMap view with zone polygons colored by risk, gates marked with open/restricted/closed state

4. ZONE DETAIL SCREEN
   - Current risk + 5-min predicted risk, trend sparkline
   - Feature breakdown (density, inflow, outflow, speed, direction-conflict, reverse-flow ratio, blockage score) as small stat cards, plus the current behavior classification (SURGE / REVERSE_FLOW / STAGNATION / etc.) as a labeled badge
   - Explainability text block pulled from the Phase 2 `/zones/{id}/risk` endpoint
   - Recommended actions list (from `/zones/{id}/recommendation`), including `ENFORCE_ONE_WAY_FLOW` as a selectable action when offered
   - If the recommendation includes a public announcement, show the drafted text in an editable textarea (operator can tweak wording before approving) with a language tab if multiple languages are configured
   - SIMULATE button: lets the operator pick a proposed action, calls `/zones/{id}/simulate`, shows current-risk vs projected-risk side by side (a simple bar or delta chart)
   - APPROVE / MODIFY / REJECT controls that call `/recommendations/{id}/decide`, with a confirmation step before dispatch since this triggers real notifications

5. INCIDENTS SCREEN
   Live table of incoming citizen/officer incident reports, filterable by zone and status, with a detail drawer showing photo/video, and status update controls.

6. OFFICERS SCREEN
   Live roster of officers with their assigned zone and current task status, so the operator has situational awareness of ground resources.

7. VERIFY / RESULT SCREEN
   For a recently-approved action, show the before/after risk numbers a few minutes later (poll or Realtime-subscribe to the zone's risk_score) confirming intervention effectiveness — this closes the operator's decision loop and matters a lot for trust in the system.

Use loading skeletons, not blank screens, for every data-fetching component — this is a control room, not a toy demo. After this phase, tell me what environment variables I need to set in Vercel.
```

---

## 7. Phase 6 — Web App: Event Admin + System Admin Modules

```
PHASE 6: Web App — Event Administrator and System Administrator modules.

Extend the Phase 5 Next.js app with the two lower-priority-but-necessary admin roles.

1. EVENT ADMINISTRATOR MODULE
   - Event settings: name, date, venue, status toggle
   - Venue configuration: CRUD for zones (name, capacity, draw polygon on Leaflet / OpenStreetMap), gates (type, capacity, status), exits, routes
   - Officer management: assign officers to the event, view availability
   - Notification policy config: simple rule editor mapping risk level → notification behavior (inform citizen / notify operator / require approval), stored as a JSON config the AI recommendation engine can read

2. SYSTEM ADMINISTRATOR MODULE
   - User management table: list users, change role, disable/enable account, reset access — calling into Supabase Auth admin APIs from the FastAPI backend (never expose the Supabase service key to the browser; route this through a protected backend endpoint)
   - RBAC view: read-only visualization of what each role can access, generated from the `require_role` declarations in the backend for consistency (don't hand-maintain a duplicate permissions list that can drift from the real backend logic)
   - System health: API health, AI service health, database connection status, notification service status — each as a simple green/red indicator hitting a `/health` endpoint you add to the backend
   - Audit log viewer: searchable/filterable table over the `audit_log` table from Phase 1, showing actor, action, before/after state, timestamp

Both modules should be functional and honest, not decorative — but you can keep the visual polish lighter than the Operator dashboard, consistent with the MVP priority order.
```

---

## 8. Phase 7 — Integration Pass & End-to-End Test

```
PHASE 7: Integration and end-to-end verification.

Do not add new features in this phase. Instead:

1. Walk the full core loop end-to-end using the seed data from Phase 1: simulate a citizen incident report → confirm the AI engine's risk score updates → confirm the Operator dashboard shows it live via Realtime → run a what-if simulation → approve it → confirm a Field Officer task is created AND a citizen alert fires AND push notifications attempt to send AND the audit log records it.
2. Fix any broken links between phases — this is where gaps between agent sessions usually surface (mismatched field names, forgotten endpoint, wrong role check).
3. Add basic rate limiting to the incident-report and simulate endpoints so the demo/production system can't be trivially spammed.
4. Write a short `RUNBOOK.md` at the repo root: how to run backend, web, and mobile locally, in what order, with what env vars, so I (or anyone else) can pick this project up cold.
5. List every remaining TODO/placeholder in the codebase (synthetic sensor data, synthetic training data, stubbed integrations) in one consolidated `KNOWN_LIMITATIONS.md` file so nothing fake accidentally ships as if it were real.
```

---

## How to use this

1. Paste the **Master Context Prompt** first in a fresh agent session.
2. Paste each phase prompt one at a time, in order — let the agent finish and actually run/test each phase before moving to the next. Skipping ahead is the #1 way these builds fall apart silently.
3. Whenever the agent's plan for a phase looks off, correct it in that phase before proceeding — don't try to fix Phase 1 mistakes from inside a Phase 5 prompt.
4. Phases 4, 5, and 6 (mobile, operator web, admin web) can be built in parallel by three separate agent sessions once Phases 1–3 are solid, since they all just consume the same backend API.


# CrowdShield — Addendum Prompts (Patch, not Rebuild)

You're already past Phase 7 (integration). These four prompts close specific gaps against the official objective statement without touching anything already working. Paste them one at a time, in order — each tells your agent to extend existing files, not rewrite them. Run your Phase 7 end-to-end test again after all four are applied.

---

## Addendum A — Reverse-Flow & Blockage Detection + Behavior Classification

```
This is an addendum to the existing CrowdShield backend, not a rebuild. Locate the existing feature pipeline in `backend/app/ai/features.py` and extend it — do not rewrite it from scratch, preserve all existing fields and function signatures used elsewhere in the codebase.

1. Add two new fields to the feature vector this pipeline already produces:
   - `reverse_flow_ratio`: share of tracked movement going against the zone's designated flow direction
   - `blockage_score`: a sustained, spatially-concentrated speed drop in one sub-area of the zone (as opposed to congestion spread evenly across the whole zone) — this is what distinguishes "route physically blocked" from "just generally crowded"
   Update `simulate_sensor_reading()` (the existing synthetic data generator) to produce plausible values for both, and keep it clearly commented as a placeholder for real sensor ingestion, consistent with how the rest of that function is already documented.

2. Create a new file `backend/app/ai/behavior.py` with a function `classify_behavior(feature_vector) -> BehaviorType` that returns one of: `NORMAL`, `SURGE`, `REVERSE_FLOW`, `STAGNATION`, `DISPERSED_INCIDENT_CLUSTER`. Use simple, explainable thresholds (not a black-box model) — I need to be able to justify these thresholds to a reviewer. Wire this into wherever the existing `/zones/{zone_id}/risk` endpoint assembles its response, adding a `behavior_classification` field to that response without breaking its existing shape.

3. Update the existing explanation generator (`ai/explain.py`) so its plain-language output references the behavior classification when relevant, e.g. "Movement is flowing against the designated direction near Gate A" for REVERSE_FLOW, rather than only describing raw density/speed numbers as it does now.

4. Add tests for `classify_behavior` covering all five categories with clearly-labeled synthetic inputs.

Show me a diff-style summary of what changed in each file, not just the new code, so I can review against what's already deployed.
```

---

## Addendum B — One-Way Flow Action + Announcement Drafting

```
This is an addendum to the existing CrowdShield AI engine. Extend `backend/app/ai/recommend.py` and the existing action taxonomy — do not remove or rename existing action types (`RESTRICT_GATE`, `OPEN_ALTERNATE_GATE`, `REDIRECT_VISITORS`, `DEPLOY_OFFICERS`, `ISSUE_PUBLIC_ANNOUNCEMENT`) since the web dashboard and mobile app already depend on those exact names.

1. Add a new action type `ENFORCE_ONE_WAY_FLOW(route_id)` to the recommendation engine. Wire it in specifically when `classify_behavior()` (from Addendum A) returns `REVERSE_FLOW` as the dominant condition — it should not appear as a generic suggestion for other situation types.

2. Update `backend/app/ai/simulate.py` so `simulate_intervention()` handles this new action type: when proposed, reduce `reverse_flow_ratio` and `direction_conflict_score` in the feature vector before re-scoring, the same way existing action types already adjust other features. Follow the existing pattern in that file exactly.

3. Create `backend/app/ai/announce.py` with `draft_announcement(situation_type, zone_name, recommended_action, language="en")` returning ready-to-broadcast public announcement text (e.g., "Attention: Gate A is experiencing heavy congestion. Please proceed to Gate C. Do not push forward."). Use template dictionaries keyed by situation_type and language — deterministic and fast, no live LLM call during an active incident. Support English plus one additional language (tell me which one you want to start with if I haven't specified — Hindi is the sensible default given the pilgrimage/festival use case in our original scope).

4. Update the existing `/zones/{zone_id}/recommendation` endpoint to accept an optional `?lang=` query param and include drafted announcement text in its response whenever `ISSUE_PUBLIC_ANNOUNCEMENT` is among the recommended actions.

5. Update the existing `/recommendations/{id}/decide` endpoint so that if the operator is approving an action that includes an announcement, the request body can carry operator-edited announcement text that overrides the drafted version — store both the original draft and the final approved text in the audit log so we can see whether operators are editing the AI's drafts.

Show me a diff-style summary, and list every existing frontend call site (web dashboard, mobile app) that will need to change because of the new response fields — don't leave that discovery to me.
```

---

## Addendum C — Control Room UI: One-Way Flow + Editable Announcements

```
This is an addendum to the existing Next.js Control Room dashboard (Zone Detail screen). Do not rebuild the screen — extend the existing components.

1. In the recommended actions list component, add support for rendering `ENFORCE_ONE_WAY_FLOW` as a selectable option in the SIMULATE flow, using whatever pattern the existing action list already uses for the other action types (RESTRICT_GATE, etc.) so it's visually and behaviorally consistent.

2. Add a labeled badge near the risk score showing the current `behavior_classification` value (SURGE / REVERSE_FLOW / STAGNATION / NORMAL / DISPERSED_INCIDENT_CLUSTER) returned by the now-updated `/zones/{id}/risk` endpoint, using a distinct color per type — reuse the existing risk-color palette conventions rather than introducing a new color scheme.

3. When the recommendation includes drafted announcement text, render it in an editable textarea above the APPROVE/MODIFY/REJECT controls. If more than one language is configured on the backend, show a simple tab or dropdown to preview/edit each language's version before approving. Wire the APPROVE action to send any edited text back through the updated `/recommendations/{id}/decide` endpoint from Addendum B.

4. Confirm the Realtime subscription this screen already has for zone updates also picks up the new `behavior_classification` field without requiring a new subscription — it should just be part of the same row update.

Show me a diff-style summary of the changed components.
```

---

## Addendum D — Mobile App: Multilingual Support

```
This is an addendum to the existing React Native/Expo app. Do not restructure navigation or existing screens beyond what's needed for i18n — this is a wrapping pass, not a redesign.

1. Add `expo-localization` and `react-i18next`. Create a `locales/en.json` and `locales/hi.json` (or whichever second language we've settled on in the backend's `ai/announce.py`) containing every static UI string currently hardcoded across the Citizen and Field Officer screens. Go screen by screen and replace hardcoded strings with `t('key')` calls — list every file you touch so I can spot-check nothing broke.

2. Add a language switcher in the app's Settings/Profile screen (create one now if it doesn't exist yet) that persists the choice using `expo-secure-store` (consistent with how the app already stores the auth session) and updates `i18next`'s active language immediately without requiring an app restart.

3. Update every existing API call that hits the backend's `/zones/{id}/recommendation` or receives push-notification announcement text to pass the user's selected language as the `?lang=` param added in Addendum B, so citizens see alerts and announcements in their chosen language, not just the UI chrome.

4. For incoming push notifications (Expo Notifications handler), confirm the displayed alert body uses the already-localized text coming from the backend rather than re-translating client-side.

Show me a diff-style summary and flag any screen where a string was ambiguous to extract (e.g. text built by string concatenation) so I can review those by hand.
```

---

## After applying all four

Re-run your existing Phase 7 end-to-end test, plus specifically:
- Force a `REVERSE_FLOW` condition via seed/synthetic data and confirm `ENFORCE_ONE_WAY_FLOW` appears as a recommendation, simulates correctly, and dispatches.
- Confirm an approved `ISSUE_PUBLIC_ANNOUNCEMENT` action produces the operator-edited (not just AI-drafted) text in the audit log.
- Switch the mobile app's language and confirm both static UI and a live push notification render in the selected language.



# CrowdShield — Going Live: Real Data, Real Model, Real Testing

Everything up to now ran on synthetic sensor data and a synthetic-trained model — fine for demos, not safe for a real event. This phase replaces both, then tests the result like safety software, not like a web app. Four prompts, paste in order. Read the "What I must decide myself" section before Prompt 1 — the agent cannot make these calls for you.

---

## What I must decide before starting (agent can't do this part)

1. **Sensing method** — how will CrowdShield actually see the crowd? Options, roughly in order of cost/complexity:
   - Existing venue CCTV feeds + computer vision (density/flow estimation from video) — needs camera access/API from the venue, decent compute (GPU) for real-time inference
   - Dedicated people-counting sensors at gates (thermal/IR beam counters) — cheaper, less rich data, no video privacy concerns
   - Wi-Fi/Bluetooth probe-request counting for rough density — cheap, privacy-sensitive, less accurate
   - Crowdsourced from the Citizen app itself (GPS density of active app users) — free but only sees app users, not the whole crowd, so it undercounts and needs disclosure to users
   - A hybrid: CCTV for zone-level density/flow + Citizen app GPS as a cheap cross-check
   You need to pick this before Prompt 1, because it changes what the ingestion pipeline actually does. If you're unsure, tell me your budget/venue access and I can help you weigh it before you brief the agent.

2. **Historical/training data source** — a risk model needs labeled examples of "this crowd state led to a near-miss/incident" and "this didn't." You likely don't have this yet. Realistic options: partner with a venue/event authority for anonymized historical footage or sensor logs, use published crowd-crush case studies and academic crowd-dynamics datasets (e.g., research literature on the Hajj, Love Parade, Itaewon incidents contains density/speed thresholds you can encode as rules even without raw data), or run a low-stakes pilot event first purely to collect real baseline data before trusting the model at a high-risk event.

3. **Legal/privacy review** — CCTV-based crowd analytics and location-based citizen tracking are regulated (varies by country/state). You need a real privacy policy, likely a data protection impact assessment, and venue/authority sign-off before any camera feed or citizen GPS data is processed live. This is not something to skip even for a pilot.

4. **Who has final human authority** — confirm with the actual event authority who is legally allowed to approve gate closures/officer deployment through this system, and what happens if CrowdShield is wrong. This shapes the fallback behavior in Prompt 4.

---

## Prompt 1 — Real Sensing Ingestion Pipeline

```
This replaces the synthetic sensor layer in the existing CrowdShield backend. My chosen sensing method is: [FILL IN — e.g. "CCTV feeds via RTSP from venue cameras, processed with a computer-vision density/flow model" or "IR people-counters at each gate reporting via HTTP" or "Citizen app GPS aggregation"]. Do not touch the AI risk model, behavior classifier, or recommendation engine — only replace what feeds them.

1. Design and implement `backend/app/ingestion/` as a new module responsible for turning raw input (camera frames / sensor pings / GPS pings, per my chosen method above) into the exact same feature vector shape the existing `ai/features.py` already expects (density, inflow, outflow, speed, direction-conflict, reverse_flow_ratio, blockage_score). This is critical: the ingestion layer's job is to match the existing interface, not to redesign it.

2. If the method involves computer vision: use a pretrained crowd-density/person-detection model (e.g. a density-estimation model like CSRNet, or a person-detector like YOLO with tracking for flow/speed) — do not train a CV model from scratch, that's a much bigger project than this needs. Tell me the realistic hardware requirement (GPU needed? Can it run on the same backend host, or does it need a separate inference service?) honestly, don't understate it.

3. Write an adapter interface `ingestion/base.py` (abstract class or protocol) so that `simulate_sensor_reading()` from earlier phases and this new real ingestion source are interchangeable behind a feature flag/config value (`SENSOR_MODE=synthetic|live`), so I can fall back to synthetic instantly if live ingestion breaks during an event — this fallback matters more than almost anything else in this prompt.

4. Add basic data-quality checks: what happens if a camera feed drops, a sensor stops reporting, or GPS data is sparse (few app users in a zone)? Define and implement a `confidence_score` per feature-vector reading so the AI engine and the UI can show "risk score based on low-confidence data" rather than silently presenting stale or degraded readings as if they were solid.

5. Tell me explicitly what I need to provision outside the codebase: camera/API access agreements, sensor hardware and network wiring, or (if GPS-based) exact consent/disclosure text needed in the Citizen app before location tracking for this purpose is legal to run.
```

---

## Prompt 2 — Real Model Training Pipeline

```
This replaces the synthetic training data in `backend/app/ai/risk_model.py` and `ai/behavior.py` with a real, retrainable pipeline. Do not change the model's input/output shape — anything downstream (explain.py, recommend.py, simulate.py, the API endpoints, the dashboards) depends on that shape staying stable.

1. Build `backend/app/ai/training/` as a proper pipeline, not a one-off script:
   - `data_loader.py`: ingests real historical data from whatever source I provide (CSV/logs of past events, published crowd-dynamics research thresholds, or pilot-event data collected via Prompt 1's ingestion layer) into the same feature-vector schema used everywhere else
   - `label_strategy.py`: since true "this became a crush" labels will be extremely rare (that's good — it means fewer disasters — but bad for training data), document and implement a sensible strategy: e.g. treating officer-verified high-severity incidents as positive labels, using domain-encoded thresholds from crowd-safety research (density > X people/m² + speed < Y m/s sustained for Z seconds is a well-documented crowd-crush precursor in the literature) as weak/rule-based labels to supplement sparse real incidents, and clearly document this as a class-imbalance problem, not pretend the model is more data-driven than it honestly is
   - `train.py`: retrains and validates the model against a held-out set, logs metrics (precision/recall on the rare positive class matters far more than raw accuracy here — a model that's 99% accurate by never predicting risk is useless and dangerous)
   - `evaluate.py`: a report comparing the new real-data model's predictions against the old synthetic model's predictions on the same inputs, so I can see concretely what changed before swapping it into production

2. Add a versioned model registry (even a simple one: timestamped pickle files + a `current_model.txt` pointer) so I can roll back to a previous model version if a retrained one performs worse — do not let deployment silently overwrite the only working model.

3. Be explicit in your output about the model's real limitations given realistic data volume: state plainly whether the trained model is likely to generalize beyond the specific venue/event type it was trained on, and recommend whether I should keep meaningful rule-based fallback in `recommend.py` (from earlier phases) as a permanent safety net rather than something to eventually remove.
```

---

## Prompt 3 — Safety-Critical Testing

```
Treat this as safety-critical software testing, not standard web-app QA — a false negative here (missed real risk) or a bad false positive pattern (alert fatigue causing operators to ignore real warnings) has real consequences. Build out `backend/tests/` and a `/testing` plan covering:

1. UNIT + INTEGRATION (extend existing tests, don't duplicate)
   Confirm the ingestion adapter, feature pipeline, behavior classifier, risk model, and recommendation engine each have tests using both synthetic and (once available) sampled-real inputs, including edge cases: sensor dropout mid-event, sudden gate status change, zero app users in a zone (GPS-based method), conflicting signals from different sensor types if hybrid.

2. LOAD / STRESS TESTING
   Simulate the concurrency profile of a real event: thousands of Citizen app clients hitting the API and subscribing to Realtime channels simultaneously, dozens of zones updating risk scores every few seconds, spike load during a simulated mass-incident-report scenario (many citizens reporting at once, which is exactly what happens right before a real crush). Report at what concurrency the backend degrades and what the degradation looks like (slow responses vs dropped connections vs errors) so I know the real capacity ceiling before an event, not during one.

3. MODEL VALIDATION AGAINST KNOWN SCENARIOS
   Build a `scenarios/` test suite that replays feature-vector sequences matching documented real-world crowd-crush precursor patterns from public crowd-safety research (rising density + falling speed + reverse-flow onset) and confirms the model flags rising risk with enough lead time to be actionable — define and report the actual lead time in minutes, since "predicts risk 10 seconds before it happens" is not useful even if technically correct.

4. FAILOVER TESTING
   Explicitly test: what happens if the AI/ML service crashes entirely — does the Control Room dashboard show a clear "AI engine offline, manual monitoring only" state, or does it silently show stale/wrong data? What happens if Realtime/websocket connectivity drops — do operators get a visible "reconnecting" indicator? This must fail loud, never fail silent.

5. HUMAN-IN-THE-LOOP TESTING
   With real operator users (even 2-3 people unfamiliar with the system) run a tabletop exercise: present them a simulated escalating scenario through the actual dashboard and time how long it takes them to understand the risk, evaluate the recommendation, and approve/reject — this tells you if the explainability and simulation UI actually works under time pressure, which automated tests can't tell you.

Give me a written test report template so I can document results for each category before I'd consider deploying this at a real event, including which categories are pass/fail/needs-more-data.
```

---

## Prompt 4 — Go-Live Readiness & Fallback Behavior

```
Final production-readiness pass before any real event. Do not add new features — audit and harden what exists.

1. FALLBACK / DEGRADED-MODE BEHAVIOR
   Explicitly implement and document what CrowdShield does when: the AI risk model is unavailable, sensor ingestion confidence is low (per Prompt 1's confidence_score), or network connectivity to a zone drops. In every case the Control Room dashboard must clearly tell the operator "you are now relying on manual judgment for this zone" — never silently degrade to guesses presented as confident numbers.

2. MONITORING & ALERTING (for the platform itself, not the crowd)
   Set up uptime monitoring on the backend `/health` endpoint (from earlier phases) and the ingestion pipeline specifically, with alerts to me/the on-call operator if either goes down during a live event — this needs to notify a human within seconds, not show up in a dashboard nobody's watching.

3. INCIDENT RESPONSE RUNBOOK
   Write `INCIDENT_RESPONSE.md`: what the operator team does if CrowdShield itself fails during an active event (who reverts to manual radio/PA procedures, how fast, who's accountable) — this needs input from the actual event authority, not just engineering.

4. PRIVACY & COMPLIANCE CHECKLIST
   Produce a checklist (not implement — flag for my/legal review) covering: what personal data is collected (location, incident report media, possibly CCTV-derived data), how long it's retained, whether citizens are clearly informed before the app tracks location, and whether the sensing method chosen in Prompt 1 requires venue/authority disclosure to attendees (e.g. signage for CCTV-based crowd analytics).

5. FINAL PRE-EVENT CHECKLIST
   Consolidate into one `GO_LIVE_CHECKLIST.md`: model version confirmed and rollback path tested, fallback modes tested, load test results reviewed, operator team trained on the dashboard, incident response runbook signed off by the actual authority, privacy/compliance items cleared, and a named on-call engineer for the event window.
```

---

## Order of operations

1. Fill in your sensing-method decision, then run **Prompt 1**.
2. Once real (or pilot) data is flowing, run **Prompt 2** to retrain the model — keep the synthetic model as the rollback version.
3. Run **Prompt 3** before trusting the new model or ingestion pipeline with anything real.
4. Run **Prompt 4** only once 1–3 are genuinely passing, not as a formality.

Nothing here should touch a real event until the Prompt 3 test report and Prompt 4 checklist are both clean — that's the actual bar for "live," not just "the code runs."



# CrowdShield — Addendum Prompts: CV Pipeline, Calibration, Multi-Horizon Risk

These patch the existing codebase to match the detection/prediction engineering details from your reference document. Paste one at a time, in order — each extends existing files/interfaces from earlier phases, it does not replace them. None of these change the AI engine's public API response shape more than explicitly noted, so double-check the noted call sites after each one.

---

## Prompt 1 — Computer Vision Detection Pipeline (Person Detection + Tracking + Dual Strategy)

```
This addendum implements the actual computer-vision detection pipeline referenced but not fully specified in the existing ingestion module. Extend `backend/app/ingestion/` (created in the earlier "real sensing" addendum) — do not rebuild ingestion's adapter interface, plug this in behind it.

1. FRAME SAMPLING
   Cameras run at native ~30 FPS. Do not process every frame — implement configurable frame sampling (default: process 5–10 FPS, expose as a config value `FRAME_SAMPLE_RATE`) in `ingestion/cv/frame_sampler.py`. Document the tradeoff explicitly in code comments: higher sample rate = smoother tracking and lower latency detection of fast-changing conditions, but proportionally higher GPU/CPU cost — I need this number to be a single config change, not a code change, so I can tune it per-venue based on available compute.

2. PERSON DETECTION (moderate/sparse crowd)
   Implement `ingestion/cv/detector.py` using a pretrained YOLO-family model (YOLOv8 or newer, person class only) for person detection when crowd density is below a configurable occlusion threshold. Output format per frame: list of `{bbox, confidence, frame_timestamp}`. Do not train this model — use pretrained weights, fine-tuning is out of scope for now.

3. PERSON TRACKING
   Implement `ingestion/cv/tracker.py` using ByteTrack (preferred for speed) to assign persistent IDs across frames, so the same person is trackable frame-to-frame: `{track_id, bbox, frame_timestamp}` sequences per person. If ByteTrack integration proves difficult in our stack, DeepSORT is the fallback — tell me which one you actually implemented and why, don't silently substitute without telling me.

4. DENSE-CROWD FALLBACK (density estimation model)
   Implement `ingestion/cv/density_estimator.py` using a pretrained crowd-counting/density-estimation model (CSRNet or an equivalent pretrained density-map model) for use when the venue/zone is known to run at high density (heavy occlusion breaks individual detection). This outputs an estimated headcount per zone directly from the density map, without individual bounding boxes or track IDs.

5. STRATEGY SWITCH
   Implement `ingestion/cv/strategy.py` with a function `select_detection_strategy(zone_id, recent_density_estimate) -> "detection_tracking" | "density_estimation"` that automatically switches between steps 2-3 (moderate/sparse) and step 4 (dense) per zone, based on the zone's own recent density history — not a single global switch, since different zones at the same event can be at very different densities simultaneously. Log every strategy switch (zone, timestamp, reason) so I can audit whether the switching logic is behaving sensibly during a real event, not just flapping back and forth.

6. OUTPUT CONTRACT
   Whichever strategy is active, `ingestion/cv/` must produce the same downstream shape: per-zone person count and, when tracking is available (strategy = detection_tracking), the raw track sequences needed by the next two addendum prompts (gate crossing counts, speed calculation). When strategy = density_estimation, downstream flow/speed features should degrade gracefully to a lower `confidence_score` (using the confidence mechanism from the earlier real-sensing addendum) since we don't have individual tracks to compute flow/speed from in dense-crowd mode — document this limitation clearly rather than fabricating flow/speed numbers we don't actually have data for.

Show me a diff-style summary and confirm this still satisfies the ingestion adapter interface from the earlier addendum without changes to that interface's signature.
```

---

## Prompt 2 — Zone Calibration & Real-World Density Mapping

```
This addendum solves the pixel-vs-meters problem: raw person counts and pixel-based speed are not physically meaningful without camera calibration. Extend the Event Administrator's venue configuration module (from the existing web app admin phase) and the ingestion pipeline together — this genuinely spans both.

1. ADMIN-SIDE CALIBRATION UI
   Add a camera calibration step to the existing Event Administrator zone-configuration screen: when an admin draws a zone polygon (already supported), let them also mark it with its known real-world area in square meters (measured/estimated from venue floor plans) OR, for better accuracy, let them mark 4+ reference points in the camera image whose real-world coordinates are known (e.g. corners of a known-size floor tile grid, or GPS-surveyed markers), and compute a homography transform from those correspondences. Support both: simple area-only for a fast MVP setup, and full homography for venues where I can get precise reference points. Store whichever calibration method was used per zone/camera, don't force one approach everywhere.

2. HOMOGRAPHY COMPUTATION
   Implement `ingestion/cv/calibration.py` with a function `compute_homography(image_points, world_points) -> transform_matrix` (standard 4-point-or-more homography, OpenCV's `findHomography` is fine) and `pixel_to_world(point, transform_matrix) -> (x_meters, y_meters)`. Store the computed transform matrix per zone/camera in the database (new table or column on the existing `zones`/camera config table — tell me which you chose and why).

3. APPLY CALIBRATION TO DENSITY
   Update the density calculation (wherever raw person-count → density conversion currently happens, or is currently missing, in `ai/features.py`'s pipeline) to use the calibrated real-world area for that zone (`density = person_count / zone_area_m2`), not raw pixel-based estimates. For zones with only area-only calibration (no full homography), density is straightforward division; for zones with homography, also enable per-region density variation within a zone (useful for spotting a localized bottleneck within a larger zone) by dividing the zone into a grid and computing density per grid cell using the transform.

4. APPLY CALIBRATION TO SPEED
   Update wherever pixel-based track displacement is currently converted to speed (or flag if this doesn't exist yet) to transform each tracked point through `pixel_to_world()` before computing displacement, so speed output is in actual m/s, not pixels/frame. Note explicitly in comments that this depends on the tracking module from Prompt 1.

5. VALIDATION
   Add a simple calibration sanity-check tool (`scripts/validate_calibration.py`) an admin can run after setting up a zone: feed it a test point pair (a known real-world distance visible in the camera view, e.g. "these two floor markings are 5 meters apart") and have it report the calibrated system's estimated distance so I can catch a bad calibration before an event, not during one.

Show me a diff-style summary, and list which existing feature-pipeline call sites now depend on calibration data existing for a zone — flag clearly what happens if an admin forgets to calibrate a zone (must degrade gracefully with a low confidence_score and a visible warning in the admin UI, not silently produce wrong density numbers).
```

---

## Prompt 3 — Gate Virtual-Line Inflow/Outflow Counting

```
This addendum implements real inflow/outflow computation from tracked movement, replacing whatever placeholder currently produces those feature values. Depends on Prompt 1 (tracking) and benefits from Prompt 2 (calibration) but can be built with pixel coordinates if calibration isn't done yet for a given zone — just flag pixel-based flow counts as lower confidence.

1. VIRTUAL LINE DEFINITION
   Extend the existing gate configuration (Event Administrator module) so each gate can have a virtual line defined as two points across its physical opening, drawn on the camera view the same way zone polygons are already drawn. Store this per gate.

2. LINE-CROSSING DETECTION
   Implement `ingestion/cv/line_crossing.py` with a function that, given a tracked person's sequence of positions across frames (from Prompt 1's tracker) and a gate's virtual line, determines whether and in which direction that track crossed the line between consecutive frames (standard line-segment-intersection + side-of-line test comparing consecutive positions). Each crossing increments either `inflow_count` or `outflow_count` for that gate depending on direction, tagged with a timestamp.

3. RATE AGGREGATION
   Implement rolling-window aggregation (`ingestion/cv/flow_rate.py`) that converts raw crossing counts into the `inflow`/`outflow` rate-per-minute values the existing feature pipeline expects — use a sliding window (e.g. last 60 seconds) rather than a simple cumulative counter, since the AI engine needs current rate, not all-time total. Also compute and expose `net_accumulation = inflow - outflow` as its own explicit feature if not already present, since the reference material treats this as a distinct predictive signal from either raw rate alone.

4. DEDUPLICATION / EDGE CASES
   Handle the case where a track briefly straddles the line without truly crossing (jitter near the boundary causing false double-counts) with a minimum-displacement-past-the-line threshold before confirming a crossing. Handle track loss right at a gate (person detected crossing but track ID lost immediately after, common in dense doorways) — document how undercounting risk in this scenario is flagged via confidence_score rather than presented as exact.

5. WIRE INTO EXISTING FEATURE PIPELINE
   Update `ai/features.py` so `inflow`/`outflow`/`net_accumulation` are populated from this real pipeline when `SENSOR_MODE=live` (the flag from the earlier real-sensing addendum), falling back to the existing synthetic generator otherwise, using the same adapter pattern already established — don't create a second, parallel way of setting these fields.

Show me a diff-style summary and a short manual test procedure I can use to verify a single test walk-through of a gate produces exactly one inflow or outflow count, before trusting it at scale.
```

---

## Prompt 4 — Multi-Horizon Risk Forecasting (2 / 5 / 10 Minutes)

```
This addendum extends the existing risk model to forecast at three horizons simultaneously instead of a single 5-minute prediction, matching the reference design: "current risk, and forecast at 2, 5, and 10 minutes."

1. MODEL OUTPUT SHAPE CHANGE
   Update `ai/risk_model.py` so its prediction function returns `{current_risk, risk_2min, risk_5min, risk_10min}` instead of just `{current_risk, predicted_risk_5min}`. Decide and tell me which approach you used: (a) three separate models/heads trained on the same features with different forecast-horizon labels, or (b) one model with horizon-minutes as an additional input feature, called three times. Prefer (b) for maintainability unless you have a specific reason to prefer (a) — explain your reasoning either way.

2. RETRAIN WITH MULTI-HORIZON LABELS
   Update the training pipeline (`ai/training/` from the earlier real-model-training addendum) so synthetic and/or real training data includes labels at all three horizons, not just one. For the synthetic scenario generator, this means simulating full trajectories (as in the reference document's example table) and deriving 2/5/10-minute-ahead labels from points further along the same simulated trajectory, not three independently-generated scenarios.

3. UPDATE DOWNSTREAM CONSUMERS
   Update every existing call site that currently reads `predicted_risk_5min` (explainability module, recommendation engine, `/zones/{id}/risk` API response, Control Room dashboard risk display, mobile app if it surfaces predicted risk) to use the new three-horizon shape. List every file you touch — this is exactly the kind of response-shape change that breaks frontend code silently if a call site is missed.

4. UI PRESENTATION
   Update the Control Room Zone Detail screen's risk display (existing component) to show current + all three forecast horizons together, ideally as a small trend line (current → 2min → 5min → 10min) rather than four disconnected numbers, so an operator can see the trajectory at a glance, not just isolated snapshots.

5. EXPLAINABILITY UPDATE
   Update `ai/explain.py` so its generated text can reference the trajectory shape, not just a single number, e.g. distinguishing "risk is rising quickly and expected to reach critical within 5 minutes" from "risk is elevated now but stabilizing" — these are very different operational situations that a single-horizon number can't distinguish, and operators need to react differently to each.

Show me a diff-style summary and confirm the API response shape change is reflected in any API documentation/OpenAPI schema the backend already generates.
```

---

## Prompt 5 — Standardized Risk Buckets Across the Whole System

```
This addendum introduces a single, consistently-used risk bucket taxonomy (LOW / MODERATE / HIGH / CRITICAL) so the raw 0-100 risk score isn't interpreted differently in different parts of the system.

1. SINGLE SOURCE OF TRUTH
   Create one shared definition (e.g. `backend/app/core/risk_levels.py`, and mirror it as a shared TypeScript constant/type for the web and mobile apps so the three codebases can't drift apart) mapping score ranges to buckets: 0–24 LOW, 25–49 MODERATE, 50–74 HIGH, 75–100 CRITICAL. Include an explicit, prominent comment/docstring stating these are prototype thresholds, not clinically or safety-validated real-world limits, and must be reviewed against real incident data or domain-expert/authority input before being trusted at an actual event — I don't want this comment lost in a later refactor.

2. APPLY EVERYWHERE
   Update every place a raw risk number is currently shown or acted on to also carry/derive its bucket label, using this shared definition rather than any ad-hoc thresholding that may have crept into individual components: the Control Room dashboard's zone cards and Zone Detail screen, the citizen mobile app's safety status display, the `ai/recommend.py` logic (if any action recommendations currently key off hardcoded score thresholds rather than bucket names, refactor them to use bucket names instead so a future threshold tuning happens in exactly one file), push notification severity levels, and the audit log's recorded risk values.

3. VISUAL CONSISTENCY
   Confirm the color mapping for each bucket (already established somewhere in the existing dashboard — green/yellow/orange/red per the original plan) is defined once, alongside the numeric thresholds in the same shared module concept, and consumed consistently by both the web dashboard's existing color scheme and the mobile app's existing status colors, rather than each frontend maintaining its own separate color-to-risk mapping.

4. MULTI-HORIZON INTERACTION
   Given the multi-horizon forecasting from the previous addendum, decide and implement how bucket labels apply across horizons — e.g. a zone showing LOW now but CRITICAL at the 5-minute horizon needs a UI treatment that clearly communicates "currently fine, about to become critical," not just a single current-moment bucket badge that ignores the forecast entirely. This is one of the most operationally important details in the whole system — a badge that only reflects the current instant defeats the purpose of prediction.

Show me a diff-style summary across backend, web, and mobile, and list any place you found hardcoded threshold numbers duplicated outside the new shared definition so I know what technical debt this addendum actually cleaned up.
```

---

## Suggested order and why

Run **1 → 2 → 3** first (detection → calibration → flow counting) since 2 and 3 both depend on 1's tracking output, and 3 benefits from 2's calibration. Run **4** next since multi-horizon forecasting is independent of the CV pipeline and can proceed in parallel if you want to split agent sessions. Run **5** last, since it's a cross-cutting cleanup that touches whatever the first four prompts just changed — doing it earlier means redoing it after each subsequent change.

After all five, re-run your existing end-to-end integration test (Phase 7) plus: walk a single person through a real gate camera and confirm exactly one inflow/outflow count registers, confirm a zone with no calibration shows a visible "uncalibrated, estimate only" warning instead of a confident-looking wrong number, and confirm the dashboard visibly distinguishes a zone that's fine now but forecast to become critical from one that's simply fine.

---

# CrowdShield — Auth & Design System Refactoring Addendum Prompts

These addendum prompts detail the complete authentication implementation (signup, invite system, sessions, verification), role-gated web and mobile flows, central design system specification (`DESIGN_SYSTEM.md`), and the comprehensive visual restyle pass across Next.js Web and Expo Mobile applications.

---

## Prompt 1 — Backend: Complete Auth, Sessions, and Staff Provisioning

```
This addendum builds out the complete authentication system on top of the existing Supabase Auth + RBAC foundation from Phase 1. The existing get_current_user() and require_role() dependencies stay as-is — this prompt fills in everything around them that was never actually built: real signup/login flows, session lifecycle, and staff account provisioning.

1. CITIZEN SELF-SIGNUP (public)
   Implement POST /auth/signup (citizen role only, open to anyone) accepting email or phone + password, creating the Supabase Auth user and a corresponding row in the app's users table with role="citizen". Trigger Supabase's built-in email/OTP verification flow — the account should be created but flagged unverified until confirmed, and sensitive actions (incident reporting) should be blocked until verified. Implement POST /auth/login returning access + refresh tokens via Supabase Auth, POST /auth/refresh for silent token renewal, and POST /auth/verify-email / POST /auth/resend-verification.

2. STAFF PROVISIONING (invite-only)
   Staff accounts (field_officer, operator, event_admin, system_admin) CANNOT self-signup. Implement POST /auth/invite callable ONLY by event_admin or system_admin, accepting email, full name, assigned role, and optional default zone assignment (for field officers). This creates a pre-provisioned row in users with status="invited" and triggers a Supabase invite email containing a single-use token. Staff members click the link, arrive at an accept-invite screen, set their password via POST /auth/accept-invite, and their account transitions to status="active".

3. SESSION LIFECYCLE & SECURITY
   Implement POST /auth/logout revoking the current session / refresh token. Implement password reset endpoints: POST /auth/forgot-password (triggers Supabase reset email) and POST /auth/reset-password (accepts token + new password). Ensure all auth endpoints return standard HTTP error responses (400 for bad input, 401 for invalid credentials/unverified, 403 for insufficient role) with descriptive error messages.

4. VERIFICATION GATING MIDDLEWARE
   Update the get_current_user() dependency to check the user's email/phone verification status. Unverified citizens can view public data (live map, safe routes) but receive HTTP 403 when trying to submit incident reports or trigger emergency alerts.
```

---

## Prompt 2 — Web App: Auth Screens, Protected Routes, Session Handling

```
This addendum builds the actual login/signup/invite UI for the Next.js web app (Control Room / Event Admin / System Admin surfaces), replacing placeholder auth layouts with real screens and secure session handling.

1. AUTH SCREENS
   - /login: email/password form calling the backend's /auth/login, storing tokens securely (httpOnly cookie via a Next.js route handler / SSR helper, not raw localStorage — critical for XSS resistance in safety control applications), redirecting by role after success (Operator → dashboard /overview, Event Admin → /admin/event, System Admin → /admin/system).
   - /accept-invite?token=...: for staff members arriving via an invite link, showing their pre-assigned role (read-only) and a set-password form calling /auth/accept-invite.
   - /forgot-password and /reset-password?token=...: calling backend password reset endpoints.
   - Visible error handling: inline form validation and toast/alert feedback for expired tokens or invalid credentials.

2. PROTECTED ROUTES & MIDDLEWARE
   Implement Next.js middleware (middleware.ts) enforcing role-based route protection server-side:
   - Unauthenticated requests to /overview, /zones/*, /incidents, /officers, /verify, or /admin/* redirect immediately to /login?redirectTo=...
   - Citizens attempting to access /overview or /admin/* redirect to an "Unauthorized" notice screen.
   - Operators can access /overview, /zones/*, /incidents, /officers, /verify but are blocked from /admin/*.
   - Event Admins and System Admins have access to /admin/event and /admin/system respectively.

3. SESSION LIFECYCLE & REFRESH
   - Implement silent token renewal via POST /auth/refresh before access tokens expire.
   - Global logout button in the header calling POST /auth/logout, clearing httpOnly session cookies, and redirecting to /login.
```

---

## Prompt 3 — Mobile App: Auth Screens and Secure Session

```
This addendum builds the actual signup/login UI for the Citizen + Field Officer mobile app (Expo / React Native), providing secure token storage, onboarding flows, and role-gated navigation.

1. CITIZEN ONBOARDING & AUTH
   - Welcome/intro screens (brief, skippable) explaining what CrowdShield does and what permissions it requires (location, camera, notifications) before requesting them — explaining context first avoids cold permission denials.
   - Signup screen: email or phone + password, calling /auth/signup.
   - Verification screen: OTP / confirmation step before the app unlocks incident reporting capabilities.
   - Login screen: standard email/phone + password, with "Forgot Password" link opening a reset flow.

2. FIELD OFFICER LOGIN & BIOMETRIC UNLOCK
   - Field Officers arrive via the staff invite flow. Login screen includes a surface/role switch toggle (📱 CITIZEN vs 👮 FIELD OFFICER).
   - Biometric Unlock Option: For logged-in Field Officers, enable Face ID / Touch ID authentication via expo-local-authentication to quickly unlock the app during high-pressure field operations without typing passwords.

3. SECURE SESSION STORAGE & AUTO-REFRESH
   - Store access and refresh tokens using expo-secure-store (EncryptedSharedPreferences on Android, Keychain on iOS).
   - Implement automatic background token refresh via POST /auth/refresh on app resume or 401 response interception.
   - Handle offline state gracefully: cached session tokens allow logged-in users to access cached maps and queue incident reports offline (useOfflineStore).
```

---

## Prompt 4 — Define the Design System (do this once, before touching any screen)

```
Before changing any existing screen's styling, define a proper design system for CrowdShield that every future style change will reference — a public-safety command-and-alert product should feel authoritative, clear, and calm under pressure, not like a generic template. Deliver this as actual config (DESIGN_SYSTEM.md + mobile/src/config/theme.ts + web/src/lib/constants.ts):

1. TYPOGRAPHY SCALE
   Define distinct font sizes and weights for: Page Titles, Section Headers, Card Titles, Body Text, Captions/Metadata, and Data/Numeric Display (risk scores, occupancy counts require tabular monospace font treatment so numbers don't visually jitter as they update live).

2. COLOR PALETTE & RISK SEVERITY TAXONOMY
   - Primary Brand / Backgrounds: Deep Slate/Zinc dark mode command-center theme (bgPage: #0f172a, bgSurface: #1e293b, borderSubtle: #334155, brandPrimary: #0284c7).
   - Risk Severity Buckets (Unified single source of truth):
     - LOW (0–24.99): Emerald Green (#10b981, #064e3b bg) — Shape: Circle ●
     - MODERATE (25–49.99): Amber Yellow (#f59e0b, #78350f bg) — Shape: Triangle ▲
     - HIGH (50–74.99): Orange (#f97316, #7c2d12 bg) — Shape: Diamond ◆
     - CRITICAL (75–100.0): Crimson/Rose Red (#ef4444, #7f1d1d bg) — Shape: Octagon 🛑
   - Every color must satisfy WCAG AA contrast against dark backgrounds for high visibility under daylight or low-light field conditions.

3. SPACING & DENSITY PROFILES
   - Citizen Profile (spacious): Generous padding (16-20px), rounded corners (14-16px), lower information density for quick readability during emergency situations.
   - Field Officer & Control Room Profile (compact): Higher density padding (10-12px), tighter grid gaps (8-10px) to maximize visible telemetry per screen without scrolling.

4. TOUCH TARGET SIZING (MOBILE)
   - All interactive elements (buttons, inputs, status selectors, camera triggers) on mobile must have a minimum tap target height of 48dp to ensure reliable operation by field personnel wearing gloves or operating under stress.
```

---

## Prompt 5 — Apply Design System to the Web App

```
Apply the design system from DESIGN_SYSTEM.md and theme tokens across the existing Next.js web application. This is a restyle pass over existing screens: Login/signup screens, Control Room Overview, Zone Detail, Incidents Stream, Field Officers Roster, Event Admin config screens, and System Admin screens.

1. SCREEN RESTYLING
   - Overview & Sector Grid: Standardize card backgrounds, section headers, and grid spacing using theme tokens.
   - Zone Detail & Simulation: Render 4-horizon trajectory prediction cards (Current -> +2m -> +5m -> +10m) with tabular numeric displays so live risk values don't visually jitter.
   - Incidents & Officers Roster: Apply cohesive table borders, filter tabs, and dark command surface styling.
   - Admin Surfaces: Restyle Event Admin venue CRUD and System Admin RBAC/Audit Log screens to match the command design language.

2. UNIFIED RISK BADGE COMPONENT
   - Refactor web/src/components/ui/RiskBadge.tsx to consume the central RiskBucket taxonomy.
   - Include colorblind-accessible shape indicators (●, ▲, ◆, 🛑) alongside numerical risk values.

3. BEFORE/AFTER AUDIT
   - Verify zero inline hardcoded hex values remain across dashboard components.
   - Confirm layout structure supports consistent section spacing across widescreen and laptop displays.
```

---

## Prompt 6 — Apply Design System to the Mobile App

```
Apply the design system (DESIGN_SYSTEM.md, translated to React Native theme constants in theme.ts) across the Expo React Native app — Citizen and Field Officer screens, including the onboarding and auth flows.

1. DENSITY & LAYOUT POLICIES
   - Citizen Screens (HomeScreen, LiveMapScreen, FindSafeRouteScreen, ReportIncidentScreen, EmergencyScreen): Use theme.spacing.spacious for calm, low-density readability.
   - Field Officer Screens (MyZoneScreen, TasksScreen, VerifyIncidentScreen, OfficerReportScreen): Use theme.spacing.compact for high data-density telemetry views while maintaining minimum 48dp touch targets.

2. ACCESSIBLE TOUCH TARGETS & RISK BADGES
   - Standardize HighContrastButton, text inputs, and action tiles to guarantee minimum touch height of 48–56dp across all mobile screens.
   - Refactor mobile/src/components/UI/RiskBadge.tsx to consume theme.colors.risk tokens with tabular font (fontMono) and shape indicators (●, ▲, ◆, 🛑), matching the web dashboard's visual language exactly.

3. SINGLE SOURCE OF TRUTH VERIFICATION
   - Confirm shared risk-badge and status-color logic is imported from mobile/src/config/theme.ts and mobile/src/config/constants.ts rather than redefined per screen.
```

---

# CrowdShield — Addendum Prompts: Panic Propagation, Barricade Config, Heat Maps & Trend Analytics

These four prompts address the final remaining functional requirements from the official problem statement. They build directly on the existing mapping stack:
- Web: `LeafletMap.tsx` (Geographic view via Leaflet + OpenStreetMap) and `VectorMap.tsx` (custom SVG stadium schematic with real-time "Density Heatmap" layer toggle).
- Mobile: `react-native-maps` + `LiveMapScreen.tsx` (Supabase Realtime grid canvas layer).
- Mapbox remains an unused dependency unless explicitly specified later.

---

## Addendum E / Prompt 1 — Panic Propagation Modeling

```markdown
Prompt 1 — Panic Propagation Modeling

This addendum adds panic propagation prediction — currently every zone's risk is scored independently, but the problem statement explicitly requires modeling how panic/risk spreads from one zone into adjacent zones, which is a distinct capability from single-zone forecasting.

1. ZONE ADJACENCY GRAPH
   Extend the existing Event Administrator venue-configuration module (where zones and gates are already defined) so adjacency between zones is captured — not just each zone's own polygon, but which zones physically connect to which others, and through what (a shared gate, an open walkway, a corridor). Store this as a new `zone_adjacency` table: `zone_a_id, zone_b_id, connection_type[gate/open_path/corridor], connection_capacity`. If this can be inferred automatically from existing zone polygon geometry (shared boundary edges) plus gate placement, implement that as a default and let the admin manually override/add non-geometric adjacencies (e.g. a covered walkway between non-adjacent polygons).

2. DIFFUSION-BASED PROPAGATION MODEL
   In `backend/app/ai/propagation.py` (or extending `predict_risk`), implement a graph-based diffusion model. When Zone A's risk score rises (especially into HIGH or CRITICAL), calculate how much risk bleeds into connected Zone B over 2/5/10 min. The bleed rate must depend on: connection_type (gates bottleneck flow faster -> higher panic bleed), connection_capacity, Zone B's current occupancy/density (an already-full zone propagates panic faster than an empty one), and vector direction (if Zone A is flushing people towards Zone B, risk flows forward; if Zone B is blocked, backpressure risk flows backward). Output a per-zone `propagated_risk_score` distinct from `independent_risk_score`, plus a `risk_source` (`independent` vs `propagated_from:zone_id`).

3. EXPLAINABLE PROPAGATION METADATA
   Extend the XAI response in `/zones/{zone_id}/risk` so when a zone's risk is elevated because of an adjacent zone, the operator sees an explicit, human-readable breakdown: e.g. "Independent Risk: 42.0 (MODERATE). Incoming Panic Risk: +38.4 from Zone A (Main Stage) via Gate 1 bottleneck -> Combined Effective Risk: 80.4 (CRITICAL)". Don't hide the source — operators must know whether to intervene in Zone B directly or clear the bottleneck at Zone A/Gate 1.

4. VISUAL INDICATORS IN CONTROL ROOM
   On the frontend dashboard (`web/src/app/zones/[id]/page.tsx` and the main map component):
   - Draw directional surge/panic propagation indicators (animated vectors or directional arrows) between connected adjacent zones when risk is actively propagating.
   - Show a "Source" badge on zone cards: `INDEPENDENT` vs `PROPAGATED FROM [ZONE NAME]`.
   - In the zone detail view, show an inline alert banner when incoming panic risk from a neighbor is the primary driver of a zone's escalation.

5. VERIFICATION
   Add a test case in `backend/tests/` demonstrating a worked example: Zone A reaches CRITICAL risk -> within the 2/5/10 min forecast horizon, Zone B's score escalates via propagation even if Zone B's own telemetry hasn't spiked yet.

Paste the diffs for the extended files. Ensure the full test suite passes.
```

---

## Addendum F — Dynamic Barricade & Choke-Point Routing Configuration

```
This is an addendum to the CrowdShield gate/barricade management and routing engine. Extend existing components without rewriting.

1. BACKEND GATE & BARRICADE CONTROL:
   - Extend `backend/app/models/gate.py` and `app/schemas/gate.py` to support `is_barricaded` (boolean) and `flow_direction` (`entry`, `exit`, `bidirectional`, `reversed`).
   - Add `PATCH /api/v1/operator/gates/{gate_id}/barricade` endpoint in `app/api/v1/operator.py` allowing operators to toggle physical barricades, restrict choke points, or reverse flow direction during evacuations.
   - Update `app/ai/recommend.py` and `services/dispatch.py` so safe routing algorithms instantly bypass barricaded gates and reroute crowd flows to open escape choke points.

2. CONTROL ROOM INTERACTIVE BARRICADE OVERLAY:
   - Extend `web/src/components/dashboard/VectorMap.tsx` so operators can click any choke-point gate icon or barricade segment directly on the SVG schematic to toggle status (`OPEN`, `RESTRICTED`, `BARRICADED`, `REVERSED`).
   - Extend `web/src/components/dashboard/LeafletMap.tsx` to display interactive barricade markers with real-time status badges and one-tap status toggles for field operators.

3. MOBILE ROUTE ADJUSTMENT:
   - Update `mobile/src/screens/citizen/FindSafeRouteScreen.tsx` and `LiveMapScreen.tsx` to listen to Supabase Realtime gate CDC updates, immediately redrawing route lines around newly barricaded areas.

Show a diff-style summary of the extended files.
```

---

## Addendum G — Multi-Layer Real-Time Density Heat Maps

```
This is an addendum to the CrowdShield density mapping layer. Wire real-time telemetry into the existing heat map toggles on web and mobile maps.

1. BACKEND DENSITY MATRIX STREAM:
   - Extend `backend/app/services/realtime.py` and `app/ai/features.py` to stream sub-zone grid-cell density intensity matrices (0.0 to 1.0) calculated from camera detection tracking / IoT sensor feeds.
   - Expose `GET /api/v1/operator/zones/{zone_id}/heatmap` returning a grid array of spatial density points.

2. WEB DENSITY HEATMAP INTEGRATION:
   - Wire real backend telemetry into the existing "Density Heatmap" layer toggle in `web/src/components/dashboard/VectorMap.tsx`, interpolating color gradients (Emerald -> Yellow -> Orange -> Crimson) across SVG grid cells.
   - Extend `web/src/components/dashboard/LeafletMap.tsx` to include a canvas heatmap overlay (`leaflet.heat` or standard Canvas tile overlay) toggleable via map layer controls.

3. MOBILE REALTIME GRID CANVAS:
   - Update `mobile/src/screens/citizen/LiveMapScreen.tsx` to bind the Supabase Realtime grid canvas directly to sub-zone density matrices, giving citizens a high-contrast visual density heat map overlay.

Show a diff-style summary of the updated map components.
```

---

## Addendum H / Prompt 4 — Crowd Trend Analytics

```markdown
Prompt 4 — Crowd Trend Analytics

This addendum adds historical trend analytics — the existing multi-horizon forecast shows current + near-future risk, but nothing currently stores or surfaces how a zone's density/risk/flow actually behaved over the past hour or across the event, which the problem statement's "Crowd trend analytics" dashboard requirement calls for distinctly from live monitoring.

1. TIME-SERIES STORAGE
   Confirm whether zone feature-vector snapshots (density, inflow, outflow, speed, risk_score, behavior_classification) are currently being persisted over time anywhere, or only kept as the latest live value. If only the latest value is stored, add a `zone_metrics_history` table (or a time-series-appropriate storage choice if the data volume justifies it — tell me which you chose and why) capturing a snapshot every time the feature pipeline runs, retained for at least the duration of an event.

2. ANALYTICS API
   Add `GET /events/{event_id}/analytics/zone-trends?zone_id=&from=&to=` returning time-series data suitable for charting: risk_score, density, and inflow/outflow over the requested window, plus simple derived stats (peak risk and when it occurred, longest sustained HIGH/CRITICAL period, number of distinct risk escalation events). Add `GET /events/{event_id}/analytics/summary` for an event-wide view: which zones spent the most time at elevated risk, correlation between approved interventions and risk drops (using the existing before/after verification data from the Control Room's Verify screen) — this is what actually tells you whether the system's interventions are working across a whole event, not just one incident at a time.

3. CONTROL ROOM ANALYTICS SCREEN
   Add a new "Analytics" section to the existing Control Room web app navigation (alongside Overview, Zone Detail, Incidents, Officers, Audit Log). Build: a zone-selector time-series chart (risk/density/flow over time, using the existing design-system chart color conventions), an event-wide summary view (highest-risk zones ranked, intervention-effectiveness comparison), and make this genuinely useful during a live event too (not just post-event review) by defaulting the time window to "last hour, live-updating" rather than requiring the operator to manually pick a historical range every time.

4. EVENT ADMIN / POST-EVENT REPORT
   Add a simple exportable post-event summary (PDF or structured report) for the Event Administrator role, covering the event-wide analytics from step 2 — this is the kind of artifact that would actually get handed to an authority/oversight body after a real event, so make it clear and non-technical in its language even though the underlying data is detailed.
```



