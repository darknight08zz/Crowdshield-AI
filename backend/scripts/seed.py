"""
DEV-ONLY SEED SCRIPT FOR CROWDSHIELD LOCAL DEVELOPMENT.
======================================================
DO NOT RUN IN PRODUCTION. This script populates the database with realistic
mock data including 1 event, 4 zones, 6 gates, and 1 user per role.
"""

import sys
import os
from datetime import datetime, timedelta
import uuid

# Add parent directory to sys.path for app module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User, UserRoleEnum
from app.models.event import Event
from app.models.zone import Zone
from app.models.gate import Gate, GateTypeEnum, GateStatusEnum
from app.models.incident import Incident, IncidentStatusEnum
from app.models.recommendation import AIRecommendation, RecommendationStatusEnum


def seed_database():
    print("[+] Starting CrowdShield Dev Seed Process...")
    db: Session = SessionLocal()

    try:
        # 1. Create Users (1 per role)
        print("[+] Creating Users for 5 Roles...")
        users = [
            User(
                id=uuid.UUID("10000000-0000-0000-0000-000000000001"),
                role=UserRoleEnum.CITIZEN.value,
                name="Alice Citizen",
                email="alice.citizen@example.com",
                phone="+15550100001"
            ),
            User(
                id=uuid.UUID("20000000-0000-0000-0000-000000000002"),
                role=UserRoleEnum.FIELD_OFFICER.value,
                name="Officer Bob Smith",
                email="bob.officer@crowdshield.org",
                phone="+15550100002"
            ),
            User(
                id=uuid.UUID("30000000-0000-0000-0000-000000000003"),
                role=UserRoleEnum.OPERATOR.value,
                name="Carol Operator",
                email="carol.operator@crowdshield.org",
                phone="+15550100003"
            ),
            User(
                id=uuid.UUID("40000000-0000-0000-0000-000000000004"),
                role=UserRoleEnum.EVENT_ADMIN.value,
                name="David Event Admin",
                email="david.admin@eventco.com",
                phone="+15550100004"
            ),
            User(
                id=uuid.UUID("50000000-0000-0000-0000-000000000005"),
                role=UserRoleEnum.SYSTEM_ADMIN.value,
                name="Eve System Admin",
                email="eve.sysadmin@crowdshield.org",
                phone="+15550100005"
            ),
        ]

        for u in users:
            existing = db.query(User).filter(User.id == u.id).first()
            if not existing:
                db.add(u)
        db.commit()

        # 2. Create 1 Fake Event
        print("[+] Creating Fake Event...")
        event_id = uuid.UUID("ee000000-0000-0000-0000-000000000001")
        existing_event = db.query(Event).filter(Event.id == event_id).first()
        if not existing_event:
            event = Event(
                id=event_id,
                name="Grand Music Festival 2026",
                date=datetime.utcnow() + timedelta(days=2),
                venue="Metropolitan Stadium Grounds",
                status="active"
            )
            db.add(event)
            db.commit()

        # 3. Create 4 Zones
        print("[+] Creating 4 Zones...")
        zone_ids = [
            uuid.UUID("aa111111-0000-0000-0000-000000000001"),
            uuid.UUID("bb222222-0000-0000-0000-000000000002"),
            uuid.UUID("cc333333-0000-0000-0000-000000000003"),
            uuid.UUID("dd444444-0000-0000-0000-000000000004"),
        ]

        zones_data = [
            {
                "id": zone_ids[0],
                "name": "Main Stage Front Area",
                "capacity": 10000,
                "current_density": 0.85,
                "risk_score": 0.78,
                "geo_polygon": {
                    "type": "Polygon",
                    "coordinates": [[[77.2090, 28.6139], [77.2100, 28.6139], [77.2100, 28.6149], [77.2090, 28.6149], [77.2090, 28.6139]]]
                }
            },
            {
                "id": zone_ids[1],
                "name": "Food Court & Plaza",
                "capacity": 5000,
                "current_density": 0.50,
                "risk_score": 0.32,
                "geo_polygon": {
                    "type": "Polygon",
                    "coordinates": [[[77.2100, 28.6139], [77.2110, 28.6139], [77.2110, 28.6149], [77.2100, 28.6149], [77.2100, 28.6139]]]
                }
            },
            {
                "id": zone_ids[2],
                "name": "North Gate Bottleneck Zone",
                "capacity": 3000,
                "current_density": 0.72,
                "risk_score": 0.65,
                "geo_polygon": {
                    "type": "Polygon",
                    "coordinates": [[[77.2090, 28.6149], [77.2100, 28.6149], [77.2100, 28.6159], [77.2090, 28.6159], [77.2090, 28.6149]]]
                }
            },
            {
                "id": zone_ids[3],
                "name": "Camping & VIP Lounge",
                "capacity": 2000,
                "current_density": 0.15,
                "risk_score": 0.08,
                "geo_polygon": {
                    "type": "Polygon",
                    "coordinates": [[[77.2100, 28.6149], [77.2110, 28.6149], [77.2110, 28.6159], [77.2100, 28.6159], [77.2100, 28.6149]]]
                }
            },
        ]

        for z in zones_data:
            existing_z = db.query(Zone).filter(Zone.id == z["id"]).first()
            if not existing_z:
                zone_obj = Zone(
                    id=z["id"],
                    event_id=event_id,
                    name=z["name"],
                    capacity=z["capacity"],
                    current_density=z["current_density"],
                    risk_score=z["risk_score"],
                    geo_polygon=z["geo_polygon"]
                )
                db.add(zone_obj)
        db.commit()

        # 4. Create 6 Gates
        print("[+] Creating 6 Choke Point Gates...")
        gates_data = [
            {"id": uuid.UUID("90000000-0000-0000-0000-000000000001"), "zone_id": zone_ids[2], "name": "North Gate A1", "type": GateTypeEnum.ENTRY.value, "capacity_per_min": 120, "status": GateStatusEnum.RESTRICTED.value},
            {"id": uuid.UUID("90000000-0000-0000-0000-000000000002"), "zone_id": zone_ids[2], "name": "North Gate A2", "type": GateTypeEnum.ENTRY.value, "capacity_per_min": 120, "status": GateStatusEnum.OPEN.value},
            {"id": uuid.UUID("90000000-0000-0000-0000-000000000003"), "zone_id": zone_ids[1], "name": "Plaza Exit Gate B1", "type": GateTypeEnum.EXIT.value, "capacity_per_min": 200, "status": GateStatusEnum.OPEN.value},
            {"id": uuid.UUID("90000000-0000-0000-0000-000000000004"), "zone_id": zone_ids[0], "name": "Stage West Exit Gate C", "type": GateTypeEnum.EXIT.value, "capacity_per_min": 180, "status": GateStatusEnum.OPEN.value},
            {"id": uuid.UUID("90000000-0000-0000-0000-000000000005"), "zone_id": zone_ids[0], "name": "Emergency Gate East 1", "type": GateTypeEnum.EMERGENCY.value, "capacity_per_min": 300, "status": GateStatusEnum.CLOSED.value},
            {"id": uuid.UUID("90000000-0000-0000-0000-000000000006"), "zone_id": zone_ids[2], "name": "Emergency Gate North 2", "type": GateTypeEnum.EMERGENCY.value, "capacity_per_min": 300, "status": GateStatusEnum.CLOSED.value},
        ]

        for g in gates_data:
            existing_g = db.query(Gate).filter(Gate.id == g["id"]).first()
            if not existing_g:
                gate_obj = Gate(
                    id=g["id"],
                    event_id=event_id,
                    zone_id=g["zone_id"],
                    name=g["name"],
                    type=g["type"],
                    capacity_per_min=g["capacity_per_min"],
                    status=g["status"]
                )
                db.add(gate_obj)
        db.commit()

        # 5. Create Initial Incident & AI Recommendation
        print("[+] Creating Sample Incident & AI Recommendation...")
        inc_id = uuid.UUID("80000000-0000-0000-0000-000000000001")
        if not db.query(Incident).filter(Incident.id == inc_id).first():
            incident = Incident(
                id=inc_id,
                reporter_id=users[0].id,
                zone_id=zone_ids[0],
                type="crowd_surge",
                description="Heavy pushing near stage left barrier",
                status=IncidentStatusEnum.REPORTED.value
            )
            db.add(incident)

        rec_id = uuid.UUID("70000000-0000-0000-0000-000000000001")
        if not db.query(AIRecommendation).filter(AIRecommendation.id == rec_id).first():
            recommendation = AIRecommendation(
                id=rec_id,
                zone_id=zone_ids[0],
                risk_score=0.78,
                predicted_risk_5min=0.89,
                recommended_actions=[
                    {"action": "OPEN_GATE", "target_gate": "Emergency Gate East 1", "reason": "Relieve main stage pressure"},
                    {"action": "DISPATCH_OFFICERS", "count": 4, "target_zone": "Main Stage Front Area"}
                ],
                status=RecommendationStatusEnum.PENDING.value
            )
            db.add(recommendation)

        db.commit()
        print("[SUCCESS] Dev Seed successfully completed!")

    except Exception as e:
        print(f"[ERROR] Error during dev seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
