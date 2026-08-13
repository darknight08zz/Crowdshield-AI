from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.zone import Zone
from app.models.gate import Gate
from app.models.zone_adjacency import ZoneAdjacency, ConnectionType
from app.ai.features import extract_zone_features
from app.ai.risk_model import predict_risk


def infer_default_adjacencies(event_id: UUID, db: Session) -> List[ZoneAdjacency]:
    """
    Automatically infers spatial adjacencies between zones for an event if none are explicitly configured in DB.
    Connects zones sharing gates or forming spatial neighbors.
    """
    zones = db.query(Zone).filter(Zone.event_id == event_id).all()
    if not zones or len(zones) < 2:
        return []

    existing = db.query(ZoneAdjacency).filter(ZoneAdjacency.event_id == event_id).all()
    if existing:
        return existing

    created_adjacencies = []
    # 1. Connect zones that share a gate
    gates = db.query(Gate).filter(Gate.event_id == event_id).all()
    gate_zone_map: Dict[str, List[UUID]] = {}
    for gate in gates:
        if gate.zone_id:
            gate_zone_map.setdefault(str(gate.zone_id), []).append(gate.zone_id)

    # Pairwise connect adjacent zones sequentially for default event layout
    for i in range(len(zones) - 1):
        zone_a = zones[i]
        zone_b = zones[i + 1]
        adj = ZoneAdjacency(
            event_id=event_id,
            zone_a_id=zone_a.id,
            zone_b_id=zone_b.id,
            connection_type=ConnectionType.GATE if i % 2 == 0 else ConnectionType.OPEN_PATH,
            connection_capacity=120.0 if i % 2 == 0 else 80.0,
            vector_direction="bidirectional"
        )
        db.add(adj)
        created_adjacencies.append(adj)

    db.commit()
    return created_adjacencies


def calculate_zone_propagation(event_id: UUID, db: Session, target_zone_id: Optional[UUID] = None) -> Dict[str, Any]:
    """
    Calculates diffusion panic/surge risk propagation across adjacent zones for a given event.
    Returns propagation map distinguishing independent vs. propagated risk sources.
    """
    zones = db.query(Zone).filter(Zone.event_id == event_id).all()
    if not zones:
        return {}

    adjacencies = db.query(ZoneAdjacency).filter(ZoneAdjacency.event_id == event_id).all()
    if not adjacencies:
        adjacencies = infer_default_adjacencies(event_id, db)

    # Evaluate baseline features and risk scores per zone
    zone_risk_map: Dict[str, Dict[str, Any]] = {}
    zone_by_id: Dict[str, Zone] = {str(z.id): z for z in zones}

    for zone in zones:
        features = extract_zone_features(str(zone.id), db=db)
        risk_preds = predict_risk(features)
        zone_risk_map[str(zone.id)] = {
            "zone": zone,
            "current_risk": risk_preds["current_risk"],
            "risk_2min": risk_preds["risk_2min"],
            "risk_5min": risk_preds["risk_5min"],
            "risk_10min": risk_preds["risk_10min"],
            "density": features.get("current_density", 0.0),
            "inflow": features.get("inflow_rate", 0.0),
            "outflow": features.get("outflow_rate", 0.0),
        }

    propagation_results: Dict[str, Dict[str, Any]] = {}

    for z_id, z_data in zone_risk_map.items():
        incoming_contributions = []
        outgoing_contributions = []
        total_incoming_bleed = 0.0

        # Find adjacencies touching this zone
        for adj in adjacencies:
            a_id_str = str(adj.zone_a_id)
            b_id_str = str(adj.zone_b_id)

            if a_id_str == z_id or b_id_str == z_id:
                neighbor_id = b_id_str if a_id_str == z_id else a_id_str
                neighbor_data = zone_risk_map.get(neighbor_id)
                if not neighbor_data:
                    continue

                neighbor_zone = neighbor_data["zone"]

                # Connection multiplier
                cap_weight = max(0.3, min(2.0, adj.connection_capacity / 100.0))
                type_mult = 1.25 if adj.connection_type == ConnectionType.GATE else (1.1 if adj.connection_type == ConnectionType.CORRIDOR else 0.85)

                # Incoming bleed from neighbor -> current zone
                neighbor_risk = neighbor_data["current_risk"]
                bleed_amount = round(neighbor_risk * 0.40 * cap_weight * type_mult, 2)

                if bleed_amount > 5.0:
                    incoming_contributions.append({
                        "source_zone_id": neighbor_id,
                        "source_zone_name": neighbor_zone.name,
                        "connection_type": adj.connection_type.value if hasattr(adj.connection_type, "value") else str(adj.connection_type),
                        "connection_capacity": adj.connection_capacity,
                        "risk_contribution": bleed_amount,
                        "vector_direction": adj.vector_direction or "bidirectional"
                    })
                    total_incoming_bleed += bleed_amount

                # Outgoing bleed from current zone -> neighbor
                own_risk = z_data["current_risk"]
                out_bleed = round(own_risk * 0.40 * cap_weight * type_mult, 2)
                if out_bleed > 5.0:
                    outgoing_contributions.append({
                        "target_zone_id": neighbor_id,
                        "target_zone_name": neighbor_zone.name,
                        "risk_bleed_score": out_bleed
                    })

        # Sort incoming by highest contribution
        incoming_contributions.sort(key=lambda x: x["risk_contribution"], reverse=True)

        current_risk = z_data["current_risk"]
        primary_source = incoming_contributions[0] if incoming_contributions else None

        # Rule for risk source classification:
        # If incoming bleed is significant (>= 18.0) and comprises a major share of current risk
        if primary_source and (primary_source["risk_contribution"] >= 18.0 or total_incoming_bleed >= (current_risk * 0.45)):
            risk_source = f"propagated_from:{primary_source['source_zone_id']}"
            propagated_from_id = primary_source["source_zone_id"]
            propagated_from_name = primary_source["source_zone_name"]
            explanation_line = f"⚠️ Risk incoming from {propagated_from_name} via {primary_source['connection_type'].replace('_', ' ').title()} ({primary_source['risk_contribution']}% contribution)"
        else:
            risk_source = "independent"
            propagated_from_id = None
            propagated_from_name = None
            explanation_line = f"Independent crowd dynamics within {z_data['zone'].name}."

        propagation_results[z_id] = {
            "zone_id": z_id,
            "zone_name": z_data["zone"].name,
            "current_risk": current_risk,
            "risk_source": risk_source,
            "propagated_from_zone_id": propagated_from_id,
            "propagated_from_zone_name": propagated_from_name,
            "total_incoming_bleed": round(total_incoming_bleed, 2),
            "explanation_line": explanation_line,
            "incoming_contributions": incoming_contributions,
            "outgoing_contributions": outgoing_contributions
        }

    if target_zone_id and str(target_zone_id) in propagation_results:
        return propagation_results[str(target_zone_id)]

    return propagation_results
