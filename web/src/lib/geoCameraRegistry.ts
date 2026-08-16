import { GeoEvent, GeoCamera, GeoZone, isValidCoordinate } from './geoMapTypes';

/**
 * CrowdShield Phase 6C.4 — Static Camera Location Registry
 * Represents known CCTV camera installation coordinates and monitored zone mappings.
 * Strictly static configuration — no dynamic telemetry stored here.
 */

export const DEFAULT_VENUE_EVENT: GeoEvent = {
  event_id: 'evt_01',
  name: 'Grand Music Festival 2026',
  latitude: 37.7745,
  longitude: -122.4174,
  venue: 'San Francisco Central Arena Park',
  cameras: [
    {
      camera_id: 'CAM-01',
      name: 'Main Entrance Gate CCTV',
      event_id: 'evt_01',
      latitude: 37.7752,
      longitude: -122.4189,
      zone_id: 'z-1',
      status: 'ONLINE',
    },
    {
      camera_id: 'CAM-02',
      name: 'North Concourse CCTV',
      event_id: 'evt_01',
      latitude: 37.7758,
      longitude: -122.4179,
      zone_id: 'z-2',
      status: 'ONLINE',
    },
    {
      camera_id: 'CAM-03',
      name: 'East Corridor CCTV',
      event_id: 'evt_01',
      latitude: 37.7748,
      longitude: -122.4169,
      zone_id: 'z-3',
      status: 'ONLINE',
    },
    {
      camera_id: 'CAM-04',
      name: 'Stage Front Pit CCTV',
      event_id: 'evt_01',
      latitude: 37.7738,
      longitude: -122.4159,
      zone_id: 'z-4',
      status: 'ONLINE',
    },
  ],
  zones: [
    {
      zone_id: 'z-1',
      event_id: 'evt_01',
      name: 'Main Gate',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [37.7749, -122.4194],
          [37.7755, -122.4184],
          [37.7745, -122.4174],
          [37.7739, -122.4184],
        ],
      },
    },
    {
      zone_id: 'z-2',
      event_id: 'evt_01',
      name: 'North Concourse',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [37.7755, -122.4184],
          [37.7761, -122.4174],
          [37.7751, -122.4164],
          [37.7745, -122.4174],
        ],
      },
    },
    {
      zone_id: 'z-3',
      event_id: 'evt_01',
      name: 'East Corridor',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [37.7739, -122.4184],
          [37.7745, -122.4174],
          [37.7735, -122.4164],
          [37.7729, -122.4174],
        ],
      },
    },
    {
      zone_id: 'z-4',
      event_id: 'evt_01',
      name: 'Stage Front',
      geometry: {
        type: 'Polygon',
        coordinates: [
          [37.7745, -122.4174],
          [37.7751, -122.4164],
          [37.7741, -122.4154],
          [37.7735, -122.4164],
        ],
      },
    },
  ],
};

/**
 * Filter cameras with valid coordinates for map rendering.
 */
export function getValidCamerasForMap(cameras: GeoCamera[]): GeoCamera[] {
  return cameras.filter((cam) => {
    if (!isValidCoordinate(cam.latitude, cam.longitude)) {
      return false;
    }
    return cam.status !== 'LOCATION_UNAVAILABLE';
  });
}
