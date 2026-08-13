# 📱 CrowdShield — Mobile Application (Citizen & Field Officer)

A unified **React Native (Expo SDK 54, TypeScript)** mobile application shipping to Android & iOS. It serves dual operational roles from a single codebase—**Citizen Safety Surface** and **Field Officer Surface**—switching UI automatically based on the authenticated Supabase user's role.

---

## 🚀 Technologies Used

- **Framework**: Expo SDK 54 (`~54.0.36`), React Native 0.81, TypeScript
- **Navigation**: React Navigation 7 (Native Stack + Bottom Tabs)
- **State Management**: Zustand 5 (Local UI state), TanStack React Query 5 (Server data & caching)
- **Database & Auth**: Supabase JS Client with `ExpoSecureStoreAdapter`
- **Push Notifications**: `expo-notifications` (with automatic Expo Go sandbox fallback handling)
- **Hardware Integrations**: `expo-location`, `expo-image-picker`, `expo-haptics`, `expo-secure-store`

---

## 📂 Project Structure

```text
mobile/
├── src/
│   ├── navigation/
│   │   └── RootNavigator.tsx       # Role-based root router (CitizenTabs vs OfficerTabs)
│   ├── screens/
│   │   ├── auth/
│   │   │   └── LoginScreen.tsx      # Email/Phone login + Role surface toggle
│   │   ├── citizen/
│   │   │   ├── HomeScreen.tsx      # Event safety status & current zone risk
│   │   │   ├── LiveMapScreen.tsx   # Interactive map with Realtime zone overlays
│   │   │   ├── FindSafeRouteScreen.tsx # Egress pathfinder avoiding congestion
│   │   │   ├── ReportIncidentScreen.tsx # Incident report + GPS tag & photo picker
│   │   │   └── EmergencyScreen.tsx # One-tap emergency dispatch dialer
│   │   └── officer/
│   │       ├── MyZoneScreen.tsx    # Deployed zone density & control room directives
│   │       ├── TasksScreen.tsx     # Assigned task checkboxes (in_progress/completed)
│   │       ├── VerifyIncidentScreen.tsx # Incident triage & photo verification
│   │       └── OfficerReportScreen.tsx  # High-priority observation report
│   ├── services/
│   │   ├── push.ts                 # FCM Push registration & Expo Go protection
│   │   ├── offlineQueue.ts         # Persistent offline report queue (SecureStore)
│   │   └── supabase.ts             # Mobile Supabase client setup
├── app.json                        # Expo SDK 54 configuration & Android package
└── package.json
```

---

## 🛠️ Setup & Local Running Instructions

### 1. Prerequisites
- Install [Node.js](https://nodejs.org/) (v18 or v20 recommended)
- Install **Expo Go** on your physical Android/iOS phone (from Play Store or App Store)

### 2. Install Dependencies
```bash
cd mobile
npm install
```

### 3. Start Expo Metro Bundler
```bash
npx expo start
```

### 4. Running on Your Physical Phone
- **Expo Go App**: Scan the QR code displayed in the terminal using your phone's camera (iOS) or the Expo Go app (Android).
- **Press `a`**: To open in Android Emulator (if Android Studio is installed).
- **Press `i`**: To open in iOS Simulator (macOS only).

---

## 🔑 Operating Role Switching

When launching the app, the **Login Screen** allows switching between operational surfaces:

1. **📱 CITIZEN MODE**:
   - Access live event status (SAFE / MODERATE / HIGH).
   - View live zone density map subscribed to Supabase Realtime WebSocket changes.
   - Access step-by-step safe egress navigation routing.
   - Report crowd bottlenecks with attached photos and auto-tagged GPS coordinates.

2. **👮 FIELD OFFICER MODE**:
   - View assigned venue sector telemetry and AI directives dispatched from the Control Room.
   - Manage task assignments with interactive status checkboxes.
   - Conduct incident triage and capture photo evidence.

---

## 🌐 Offline Resilience

If network connection drops while submitting an incident report:
1. Reports are saved securely into local phone storage via `expo-secure-store`.
2. The `useOfflineStore` queue retries transmission automatically as soon as internet connectivity returns.

---

## 🛠️ Building Standalone APK / App Bundle

To generate a production Android `.apk` or `.aab`:
```bash
npm run build:android
```
*(Requires free [Expo Application Services (EAS)](https://expo.dev/) account)*.
