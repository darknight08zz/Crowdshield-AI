# CrowdShield — Known Limitations & Formal Validation Boundaries

## 1. Prototype AI & Scientific Provenance

```text
model_status:         PROTOTYPE
label_type:           PHYSICS_DEFINED_PROXY
ground_truth_status:  NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED
generalization_status: INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION
```

Mandatory Disclaimer:
> **"AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated."**

---

## 2. Explicit Certification Disclaimers

CrowdShield does **NOT** claim or certify:
1. **Real-world stampede prediction** or prevention efficacy.
2. **Real-world crowd-disaster prediction** in live, uncontrolled environments.
3. **Clinical validity** or safety efficacy for emergency evacuation management.
4. **Operational safety efficacy** for life-safety compliance without active human operator oversight.
5. **Cross-event generalization** across arbitrary venue geometries or uncalibrated camera topologies.
6. **Production responder effectiveness** or field officer dispatch response time guarantees.

The software is **Engineering Validated** and **End-to-End Software Pipeline Validated** as an operational prototype.

---

## 3. Hardware & Benchmark Dependence

Performance metrics reported in project benchmarks are **empirical measurements of the specific validation host environment**:

### Validation Host Configuration
- **CPU**: AMD Ryzen 5 5500U (6 cores / 12 threads @ 2.1 GHz base)
- **GPU**: Integrated AMD Radeon Graphics (NVIDIA CUDA Unavailable)
- **RAM**: 16 GB DDR4
- **OS**: Windows 11 Home (x64)

### Measured Performance
- **640x640 Input Resolution**: ~11.69 FPS (85.52 ms average latency | 91.10 ms P95 latency)
- **320x320 Input Resolution**: ~20.27 FPS (49.33 ms average latency | 51.11 ms P95 latency)

Performance is highly hardware-, model-, input-resolution-, and workload-dependent.

---

## 4. Input Resolution Trade-Offs

- **320x320 Resolution**: Higher frame throughput (~20.27 FPS on CPU), but potentially lower spatial detection precision for small or distant targets.
- **640x640 Resolution**: Higher spatial input resolution and detection accuracy, but lower throughput (~11.69 FPS on CPU).

*Note: 320x320 is an operational trade-off for resource-constrained hardware, NOT automatically the production configuration.*

---

## 5. Telemetry & Ingestion Boundaries

RTSP, video file, and live webcam performance depend on:
- Camera source frame rate (FPS) and video stream stability
- Local network latency and bandwidth congestion
- Frame drops and temporal frame jitter
- Camera height, tilt angle, and perspective calibration
- Scene geometry, occlusion, and low-light conditions

---

## 6. Native Deployment Boundary

Docker is **not required** for the CrowdShield deployment configuration. All server components run natively on Windows via PowerShell process orchestration (`.\scripts\start_crowdshield.ps1`, `.\scripts\stop_crowdshield.ps1`, `.\scripts\status_crowdshield.ps1`).
