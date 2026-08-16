/**
 * CrowdShield Phase 6C.4 — Canonical Geospatial Data Types
 * Strict separation of Static Location Configuration vs Dynamic Realtime Telemetry.
 */

export interface GeoCamera {
  camera_id: string;
  name: string;
  event_id: string;
  latitude: number | null;
  longitude: number | null;
  zone_id: string;
  status: 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'CV_UNAVAILABLE' | 'LOCATION_UNAVAILABLE';
}

export interface GeoZone {
  zone_id: string;
  event_id: string;
  name: string;
  geometry?: {
    type: 'Polygon';
    coordinates: [number, number][]; // Array of [lat, lng]
  } | null;
}

export interface GeoEvent {
  event_id: string;
  name: string;
  latitude: number | null;
  longitude: number | null;
  venue?: string;
  cameras: GeoCamera[];
  zones: GeoZone[];
}

/**
 * Validates coordinate bounds.
 * Latitude must be within [-90, +90]
 * Longitude must be within [-180, +180]
 */
export function isValidCoordinate(lat?: number | null, lng?: number | null): boolean {
  if (lat === null || lat === undefined || lng === null || lng === undefined) {
    return false;
  }
  if (typeof lat !== 'number' || typeof lng !== 'number') {
    return false;
  }
  if (isNaN(lat) || isNaN(lng)) {
    return false;
  }
  return lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
}

/**
 * Composite key helper for multi-camera / zone isolation.
 */
export function buildCompositeCameraKey(eventId: string, cameraId: string, zoneId: string): string {
  return `${eventId}::${cameraId}::${zoneId}`;
}
