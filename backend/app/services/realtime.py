"""
CROWDSHIELD SUPABASE REALTIME CONFIGURATION & CHANNEL HELPER
==========================================================
Provides client subscription schemas for Supabase Realtime Postgres Change Data Capture (CDC).
Clients (Web Dashboard, Field Officer App, Citizen App) connect via WebSocket to receive
pushed updates without polling.
"""

from typing import Dict, Any, List
from uuid import UUID


def get_web_control_room_channels(event_id: UUID) -> List[Dict[str, Any]]:
    """
    Returns channel configuration for the Control Room Web Dashboard.
    Subscribes to all real-time table mutations for a specific event.

    JS/TS Client Usage Example:
    ---------------------------
    const channel = supabase
      .channel('control-room-event')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'zones', filter: `event_id=eq.${eventId}` }, payload => handleZone(payload))
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'incidents' }, payload => handleIncident(payload))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'ai_recommendations' }, payload => handleAI(payload))
      .subscribe();
    """
    event_str = str(event_id)
    return [
        {
            "channel_name": f"control-room-zones-{event_str}",
            "table": "zones",
            "event": "*",
            "filter": f"event_id=eq.{event_str}",
            "description": "Live crowd density & risk score updates per zone"
        },
        {
            "channel_name": f"control-room-incidents-{event_str}",
            "table": "incidents",
            "event": "*",
            "filter": None,
            "description": "Real-time incident reports submitted by citizens or field officers"
        },
        {
            "channel_name": f"control-room-ai-{event_str}",
            "table": "ai_recommendations",
            "event": "*",
            "filter": None,
            "description": "Pushed AI risk engine recommendations awaiting operator decision"
        },
        {
            "channel_name": f"control-room-assignments-{event_str}",
            "table": "officer_assignments",
            "event": "*",
            "filter": None,
            "description": "Field officer dispatch tracking and status progress updates"
        }
    ]


def get_citizen_app_channels(event_id: UUID, zone_id: UUID) -> List[Dict[str, Any]]:
    """
    Returns filtered channel configuration for the Citizen Mobile App.
    Subscribes ONLY to safety risk changes and alerts for their active zone to minimize bandwidth.

    JS/TS Client Usage Example:
    ---------------------------
    const channel = supabase
      .channel('citizen-zone-feed')
      .on('postgres_changes', { event: 'UPDATE', schema: 'public', table: 'zones', filter: `id=eq.${zoneId}` }, payload => updateZoneRisk(payload))
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'alerts', filter: `zone_id=eq.${zoneId}` }, payload => showSafetyAdvisory(payload))
      .subscribe();
    """
    zone_str = str(zone_id)
    return [
        {
            "channel_name": f"citizen-zone-{zone_str}",
            "table": "zones",
            "event": "UPDATE",
            "filter": f"id=eq.{zone_str}",
            "description": "Localized zone density & safety status indicator"
        },
        {
            "channel_name": f"citizen-alerts-{zone_str}",
            "table": "alerts",
            "event": "INSERT",
            "filter": f"zone_id=eq.{zone_str}",
            "description": "Emergency advisory alerts & safer route recommendations"
        }
    ]


def get_field_officer_channels(officer_id: UUID) -> List[Dict[str, Any]]:
    """
    Returns channel configuration for the Field Officer App.
    Subscribes to assigned task dispatches specifically targeting this officer.
    """
    officer_str = str(officer_id)
    return [
        {
            "channel_name": f"officer-tasks-{officer_str}",
            "table": "officer_assignments",
            "event": "*",
            "filter": f"officer_id=eq.${officer_str}",
            "description": "Assigned crowd management tasks & incident dispatch orders"
        }
    ]
