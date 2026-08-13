# CrowdShield Design System Specification

## Overview
CrowdShield is a mission-critical public safety and crowd intelligence platform. The visual and interaction design must convey **authoritative trust, rapid scanability, and calm clarity under pressure**. It avoids generic admin dashboard aesthetics in favor of a high-contrast, data-dense, and purposeful system-wide design language.

---

## 1. Typography Scale

### Typeface Selection
* **Primary UI & Body**: `Plus Jakarta Sans` (Fallback: `system-ui, -apple-system, sans-serif`)
* **Numeric & Telemetry Display**: `JetBrains Mono` with `tabular-nums` enabled.

> **Typeface Justification**: *Plus Jakarta Sans delivers high x-height legibility and authoritative geometric structure for rapid scanability during crisis response, while JetBrains Mono tabular numbers ensure live risk scores, telemetry counts, and timestamp counters remain visually stable without horizontal layout jitter.*

### Type Hierarchy
| Scale Name | Size (px / rem) | Weight | Line Height | Letter Spacing | Target Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Display Title** | 32px / 2.0rem | 800 (Bold) | 1.2 | `-0.02em` | Main Command Headers, Emergency Banner |
| **Page Title** | 24px / 1.5rem | 700 (Bold) | 1.3 | `-0.01em` | View Headers (e.g. Zone Overview, Incident Hub) |
| **Section Header**| 18px / 1.125rem | 700 (Bold) | 1.4 | `0.0em` | Card Group Headings, Modal Titles |
| **Card Title** | 15px / 0.9375rem | 600 (SemiBold)| 1.4 | `0.0em` | Zone Card Titles, Officer Names |
| **Body Text** | 14px / 0.875rem | 400 / 500 | 1.5 | `0.0em` | Descriptions, Audit Log Messages |
| **Caption / Metadata**| 12px / 0.75rem| 500 (Medium)| 1.4 | `0.01em` | Timestamps, Coordinates, Labels |
| **Numeric Display**| 20-30px | 700 (Mono) | 1.1 | `0.02em` (Tabular) | Risk Scores, Density Ratios, Outflow Speeds |

---

## 2. Color System

### Primary Brand Colors
* **Primary Sky**: `#0284C7` (Sky-600) — Main action buttons, active navigation indicators.
* **Primary Hover**: `#0369A1` (Sky-700)
* **Primary Active**: `#075985` (Sky-800)
* **Primary Tint**: `rgba(2, 132, 199, 0.15)` (Sky Glow)

### Neutral Scale (9-Step Slate)
* `slate-950` (`#020617`): Deepest page background (Control Room & Dark Mode)
* `slate-900` (`#0F172A`): Surface / Card background
* `slate-800` (`#1E293B`): Elevated Card / Secondary Surface
* `slate-700` (`#334155`): Subtle Component Borders & Dividers
* `slate-600` (`#475569`): Strong Borders, Disabled State
* `slate-500` (`#64748B`): Secondary Icons, Label Text
* `slate-400` (`#94A3B8`): Muted Body & Helper Text
* `slate-200` (`#E2E8F0`): Primary Content Text
* `slate-50` (`#F8FAFC`): High Contrast Headings & Emphasized Text

### Standardized Risk Bucket Taxonomy (Color + Icon Shape Accessibility)
To ensure accessibility for colorblind operators, every risk level is paired with a distinct geometric icon shape alongside color coding:

| Risk Level | Color (Hex) | Dark BG Fill | Border Color | Icon Shape | Symbol |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LOW** (0-39) | `#10B981` (Emerald) | `rgba(16,185,129,0.12)` | `#059669` | Circle | `CheckCircle2` |
| **MODERATE** (40-69)| `#F59E0B` (Amber) | `rgba(245,158,11,0.12)` | `#D97706` | Triangle | `AlertTriangle` |
| **HIGH** (70-84) | `#F97316` (Orange) | `rgba(249,115,22,0.15)` | `#EA580C` | Diamond | `ShieldAlert` |
| **CRITICAL** (85-100)| `#EF4444` (Crimson) | `rgba(239,68,68,0.20)` | `#DC2626` | Octagon | `Siren` |

### System & Form State Colors (Isolated from Risk Taxonomy)
* **Form Success**: `#06B6D4` (Cyan-500)
* **System Warning**: `#EAB308` (Yellow-500)
* **System Error**: `#E11D48` (Rose-600)
* **System Info**: `#3B82F6` (Blue-500)

---

## 3. Information Density & Surface Profiles

### Control Room & Staff Operator Surface (High Density)
* **Padding & Margins**: Compact (`p-3`, `p-3.5`, `gap-3`).
* **Grid Layouts**: 3-column / 4-column tight dashboard cards.
* **Objective**: Displays up to 12 zones, active AI recommendations, and officer dispatches on single 1080p/4K views without scrolling.

### Citizen Mobile & Public Surface (Low Density / Calm)
* **Padding & Margins**: Spacious (`p-5`, `p-6`, `gap-5`).
* **Touch Targets**: Minimum 48px height for all interactive buttons.
* **Objective**: Reduces cognitive fatigue and prevents panic during high-stress evacuations or emergency reporting.

---

## 4. Component Baseline

### Buttons
* **Primary Button**: Solid `#0284C7` with `#0369A1` hover state, 8px border-radius, font-semibold.
* **Secondary Button**: Semi-transparent `#1E293B` background with `#334155` border.
* **Emergency / SOS Button**: Solid `#DC2626` with red glow shadow (`shadow-red-950/50`).

### Risk Badges
* Standardized component rendering: `[Icon Shape] + [LEVEL NAME] + [SCORE (Mono)]`.
* Uses semi-transparent background fill with high-contrast text to ensure legibility across both dark and light modes.

### Card Elevation & Borders
* **Flat Border-First Approach**: `bg-slate-900/90 border border-slate-800/80 rounded-xl backdrop-blur-md`.
* Eliminates heavy drop shadows that cause visual clutter in multi-zone monitoring dashboards.

---

## 5. Motion Guidelines
* **Live Risk Transitions**: `transition-colors duration-200 ease-in-out` on risk badge background and border updates.
* **Telemetry Pulse**: Subtle 1.5s opacity pulse (`animate-pulse`) on real-time stream status indicators.
* **Zero Gratuitous Motion**: Avoid page transitions or bouncy animations that distract operators during active incidents.
