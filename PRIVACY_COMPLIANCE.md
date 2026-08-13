# 🔒 CrowdShield — Privacy & Regulatory Compliance Checklist

**Document Owner**: Legal & Data Protection Compliance Officer  
**Scope**: CrowdShield Mobile App, Control Room Dashboard, and CCTV/GPS Telemetry Pipeline  
**Compliance Target**: GDPR / Local Public Data Protection Directives  
**Last Updated**: 2026-08-11  

---

## 1. Personal Data Inventory & Anonymization Strategy

| Data Type | Source | PII Status | Anonymization / Protection Measure |
| :--- | :--- | :--- | :--- |
| **GPS Coordinates** | Citizen Mobile App | Sensitive PII | Aggregated immediately into 50m zone density counts ($peds/m^2$). Raw individual coordinates are **never** logged to disk. |
| **CCTV Camera Streams** | Venue RTSP Video | Visual PII | Processed in edge GPU RAM for optical flow/density estimation. **No facial recognition or video recording** is stored by CrowdShield. |
| **Incident Reports** | Citizen Mobile App | User Account ID | User ID linked for verification; text & media stored securely with encrypted database connection (TLS 1.3). |
| **Push Notification Tokens** | Expo / FCM Device Token | Device ID | Stored in `device_tokens` table for emergency announcements; deleted upon app uninstall or opt-out. |

---

## 2. Retention Limits & Data Lifecycle

```
[GPS Pings] --------> (In-Memory Processing) --------> Expired & Purged (< 60 Minutes)
[Raw CCTV Frames] ---> (GPU Edge RAM Stream) ----------> Immediate Frame Drop (0 Retention)
[Incident Reports] --> (Encrypted DB Audit Log) ------> Auto-Anonymized after 30 Days
```

* **GPS Telemetry**: Maximum retention of **60 minutes** in active spatial index buffer.
* **CCTV Analytics**: **0 seconds** raw frame retention (optical flow density vectors only).
* **Audit Logs & Incident Reports**: Retained for **30 days** post-event for statutory safety reporting, then anonymized.

---

## 3. Citizen Mobile App Disclosure & Opt-In Requirements

> **Mandatory In-App Permission Modal Text (Displayed on First Launch)**:
> 
> *"CrowdShield uses your location while using the app to calculate crowd density and send you real-time emergency safety announcements during events. Your individual location is aggregated anonymously and is never sold or shared. You may disable location sharing in Settings at any time."*

### Compliance Verification Checklist:
* [x] In-app explicit consent modal implemented prior to location access (`expo-location`).
* [x] Settings screen toggle allowing citizen users to instantly disable background location updates.
* [x] Privacy Policy accessible via link in App Settings (`locales/en.json` & `locales/hi.json`).

---

## 4. Venue Signage & Regulatory Public Notices

When utilizing **CCTV-based Computer Vision Density Analytics**, local regulations require physical notice to event attendees at venue entry gates.

### Mandatory Physical Signage Template (Minimum Size: A2 / 420x594mm at Entry Gates):

```
+------------------------------------------------------------------+
|                  NOTICE: CROWD SAFETY ANALYTICS                  |
|                                                                  |
|  This venue uses automated computer vision sensors to monitor    |
|  crowd density and movement flow in real time for safety and    |
|  stampede prevention purposes.                                    |
|                                                                  |
|  - NO FACIAL RECOGNITION IS PERFORMED.                            |
|  - NO VIDEO RECORDINGS ARE STORED BY CROWDSHIELD.                |
|                                                                  |
|  For details on our privacy policy, visit: https://crowdshield.ai|
+------------------------------------------------------------------+
```

---

## 5. Compliance Sign-Off

* [x] **Data Protection Officer (DPO) Approval**: `APPROVED`
* [x] **Venue Legal Counsel Approval**: `APPROVED`
* [x] **Citizen App Consent Dialog Verified**: `VERIFIED`
