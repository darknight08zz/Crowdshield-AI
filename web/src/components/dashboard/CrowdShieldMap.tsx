'use client';

import React, { useState, useMemo } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import Link from 'next/link';
import { Layers, MapPin, AlertTriangle, Clock, Activity, ExternalLink, ShieldAlert } from 'lucide-react';
import { GeoEvent, GeoCamera, GeoZone, isValidCoordinate } from '@/lib/geoMapTypes';
import { DEFAULT_VENUE_EVENT, getValidCamerasForMap } from '@/lib/geoCameraRegistry';
import { useRealtimeInference } from '@/lib/useRealtimeInference';
import { RealtimeInferenceResultData } from '@/lib/api';

interface CrowdShieldMapProps {
  geoEvent?: GeoEvent;
  selectedZoneId?: string;
  onSelectZone?: (zoneId: string) => void;
}

// Custom DivIcon generator based on camera health and operational warning state
function createCameraMarkerIcon(
  warningState: string = 'NORMAL',
  healthStatus: string = 'ONLINE',
  isStale: boolean = false
) {
  let bgColor = '#10b981'; // Green (NORMAL)
  let borderColor = '#059669';
  let isPulse = false;

  if (healthStatus === 'OFFLINE') {
    bgColor = '#64748b'; // Gray
    borderColor = '#334155';
  } else if (healthStatus === 'DEGRADED' || healthStatus === 'CV_UNAVAILABLE') {
    bgColor = '#94a3b8';
    borderColor = '#475569';
  } else {
    switch (warningState) {
      case 'HIGH_RISK':
        bgColor = '#ef4444'; // Red
        borderColor = '#991b1b';
        isPulse = true;
        break;
      case 'EARLY_WARNING':
        bgColor = '#f97316'; // Orange
        borderColor = '#c2410c';
        isPulse = true;
        break;
      case 'WATCH':
        bgColor = '#eab308'; // Yellow
        borderColor = '#a16207';
        break;
      case 'WARMING_UP':
        bgColor = '#a855f7'; // Purple
        borderColor = '#7e22ce';
        break;
      case 'DEGRADED':
        bgColor = '#64748b';
        borderColor = '#475569';
        break;
      default:
        bgColor = '#10b981';
        borderColor = '#059669';
    }
  }

  const pulseClass = isPulse ? 'animate-ping opacity-75' : '';

  return L.divIcon({
    className: 'custom-camera-marker',
    html: `
      <div style="position: relative; width: 28px; height: 28px;">
        ${isPulse ? `<div style="position: absolute; inset: 0; background-color: ${bgColor}; border-radius: 50%;" class="${pulseClass}"></div>` : ''}
        <div style="
          position: relative;
          background-color: ${bgColor};
          width: 28px;
          height: 28px;
          border-radius: 50%;
          border: 2px ${isStale ? 'dashed #fbbf24' : 'solid #ffffff'};
          box-shadow: 0 0 12px rgba(0,0,0,0.6);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-weight: bold;
          font-size: 11px;
        ">
          📹
        </div>
      </div>
    `,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

// Zone polygon color mapping based on warning state
function getZonePolygonColor(warningState?: string): { fill: string; stroke: string } {
  switch (warningState) {
    case 'HIGH_RISK':
      return { fill: '#ef4444', stroke: '#b91c1c' };
    case 'EARLY_WARNING':
      return { fill: '#f97316', stroke: '#c2410c' };
    case 'WATCH':
      return { fill: '#eab308', stroke: '#a16207' };
    case 'WARMING_UP':
      return { fill: '#a855f7', stroke: '#7e22ce' };
    default:
      return { fill: '#06b6d4', stroke: '#0284c7' };
  }
}

export default function CrowdShieldMap({
  geoEvent = DEFAULT_VENUE_EVENT,
  selectedZoneId,
  onSelectZone,
}: CrowdShieldMapProps) {
  const [filterState, setFilterState] = useState<string>('ALL');

  const subscriptionKey = useMemo(
    () => ({
      eventId: geoEvent.event_id,
      cameraId: 'CAM-01',
      zoneId: 'z-1',
    }),
    [geoEvent.event_id]
  );

  // Connect to live WebSocket telemetry stream (Phase 6C.1 - 6C.3 integration)
  const { data: latestResult, connectionStatus } = useRealtimeInference(subscriptionKey);
  const isConnected = connectionStatus === 'CONNECTED';

  // Scope event center
  const center: [number, number] = useMemo(() => {
    if (isValidCoordinate(geoEvent.latitude, geoEvent.longitude)) {
      return [geoEvent.latitude!, geoEvent.longitude!];
    }
    return [37.7745, -122.4174];
  }, [geoEvent]);

  // Valid camera markers
  const validCameras = useMemo(() => getValidCamerasForMap(geoEvent.cameras), [geoEvent.cameras]);

  // Filtered camera list for display
  const displayCameras = useMemo(() => {
    if (filterState === 'ALL') return validCameras;
    return validCameras.filter((cam) => {
      const matchResult = Boolean(latestResult && (latestResult.camera_id === cam.camera_id || latestResult.zone_id === cam.zone_id));
      const currentState = (matchResult && latestResult) ? latestResult.operational_warning_state : 'NORMAL';
      const currentHealth = (matchResult && latestResult) ? (latestResult.camera_health_status || 'ONLINE') : cam.status;

      if (filterState === 'OFFLINE') return currentHealth === 'OFFLINE';
      return currentState === filterState;
    });
  }, [validCameras, filterState, latestResult]);

  return (
    <div className="w-full space-y-3">
      {/* Map Control Header & Filter Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-950/90 p-2.5 rounded-xl border border-slate-800 text-xs">
        <div className="flex items-center space-x-2">
          <span className="font-bold text-cyan-400 flex items-center gap-1.5 uppercase tracking-wider text-[11px]">
            <MapPin className="w-3.5 h-3.5 text-cyan-400" />
            {geoEvent.name} — CCTV GEOSPATIAL MAP
          </span>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${isConnected ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' : 'bg-amber-950 text-amber-400 border border-amber-800'}`}>
            {isConnected ? 'LIVE WEBSOCKET' : 'CONNECTING...'}
          </span>
        </div>

        {/* State Filter Buttons */}
        <div className="flex items-center space-x-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
          <span className="text-[10px] font-semibold text-slate-400 px-1">FILTER:</span>
          {['ALL', 'NORMAL', 'WATCH', 'EARLY_WARNING', 'HIGH_RISK', 'OFFLINE'].map((st) => (
            <button
              key={st}
              onClick={() => setFilterState(st)}
              className={`px-2 py-0.5 rounded text-[10px] font-bold transition ${
                filterState === st ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Map Container */}
      <div className="w-full h-[480px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl relative bg-slate-950">
        <MapContainer
          center={center}
          zoom={16}
          scrollWheelZoom={false}
          className="w-full h-full z-0 bg-slate-950"
        >
          {/* 100% Free OpenStreetMap Tile Layer */}
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {/* Zone Geometry Polygons */}
          {geoEvent.zones.map((zone) => {
            if (!zone.geometry || !zone.geometry.coordinates || zone.geometry.coordinates.length === 0) {
              return null;
            }
            const isMatch = latestResult && latestResult.zone_id === zone.zone_id;
            const zoneWarningState = isMatch ? latestResult.operational_warning_state : 'NORMAL';
            const colors = getZonePolygonColor(zoneWarningState);
            const isSelected = selectedZoneId === zone.zone_id;

            return (
              <Polygon
                key={`zone-poly-${zone.zone_id}`}
                positions={zone.geometry.coordinates}
                pathOptions={{
                  color: isSelected ? '#38bdf8' : colors.stroke,
                  fillColor: colors.fill,
                  fillOpacity: isSelected ? 0.55 : 0.30,
                  weight: isSelected ? 3 : 2,
                }}
                eventHandlers={{
                  click: () => onSelectZone?.(zone.zone_id),
                }}
              >
                <Popup className="text-xs font-sans">
                  <div className="font-bold text-slate-900">{zone.name} (Zone {zone.zone_id})</div>
                  <div className="text-[11px] text-slate-700 font-semibold mt-0.5">
                    Operational State: <strong>{zoneWarningState}</strong>
                  </div>
                  <div className="mt-2 pt-1 border-t border-slate-200">
                    <Link
                      href={`/zones/${zone.zone_id}`}
                      className="text-cyan-700 hover:text-cyan-900 font-bold flex items-center gap-1 text-[11px]"
                    >
                      Inspect Zone Detail &rarr;
                    </Link>
                  </div>
                </Popup>
              </Polygon>
            );
          })}

          {/* Camera Geospatial Markers */}
          {displayCameras.map((cam) => {
            const hasCoords = isValidCoordinate(cam.latitude, cam.longitude);
            if (!hasCoords) return null;

            const coords: [number, number] = [cam.latitude!, cam.longitude!];

            // Join static camera config with latest realtime inference stream payload
            const isMatch = latestResult && (latestResult.camera_id === cam.camera_id || latestResult.zone_id === cam.zone_id);
            const telemetry: RealtimeInferenceResultData | null = isMatch ? latestResult : null;

            const warningState = telemetry ? telemetry.operational_warning_state : 'NORMAL';
            const healthStatus = telemetry ? (telemetry.camera_health_status || 'ONLINE') : cam.status;
            const isStale = Boolean(telemetry?.is_stale);
            const isAiUnavailable = telemetry?.ai_status === 'AI_UNAVAILABLE';
            const isWarmingUp = warningState === 'WARMING_UP';

            // Metrics (Strict physics vs AI separation with safe payload property access)
            const telemObj = (telemetry as any)?.telemetry || {};
            const personCount = telemObj.person_count ?? (telemetry as any)?.person_count;
            const density = telemObj.density ?? (telemetry as any)?.density;
            const physicsRisk = telemetry?.current_physics_risk ?? telemetry?.current_risk_score;
            const aiProb = telemetry?.ai_probability;
            const timestamp = telemetry?.telemetry_timestamp || (telemetry as any)?.timestamp;

            return (
              <Marker
                key={`cam-marker-${cam.camera_id}`}
                position={coords}
                icon={createCameraMarkerIcon(warningState, healthStatus, isStale)}
                eventHandlers={{
                  click: () => onSelectZone?.(cam.zone_id),
                }}
              >
                <Popup className="text-xs font-sans max-w-[280px]">
                  <div className="space-y-2 p-1">
                    {/* Header */}
                    <div className="border-b border-slate-200 pb-1.5">
                      <div className="font-extrabold text-slate-900 text-sm flex items-center justify-between">
                        <span>{cam.name}</span>
                        <span className="text-[10px] font-mono text-slate-500">{cam.camera_id}</span>
                      </div>
                      <div className="text-[11px] text-slate-600 font-semibold">
                        Zone: <strong>{cam.zone_id}</strong>
                      </div>
                    </div>

                    {/* Status Badges */}
                    <div className="flex flex-wrap gap-1">
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${healthStatus === 'ONLINE' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'}`}>
                        Camera: {healthStatus}
                      </span>
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded ${warningState === 'HIGH_RISK' ? 'bg-rose-100 text-rose-800 animate-pulse' : warningState === 'EARLY_WARNING' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-800'}`}>
                        State: {warningState}
                      </span>
                      {isStale && (
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-900 border border-amber-300">
                          ⚠️ STALE DATA
                        </span>
                      )}
                    </div>

                    {/* Telemetry Metrics */}
                    {telemetry ? (
                      <div className="bg-slate-50 p-2 rounded-lg space-y-1 text-[11px] font-mono-nums">
                        {personCount !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-slate-500">People Count:</span>
                            <span className="font-bold text-slate-900">{personCount}</span>
                          </div>
                        )}
                        {density !== undefined && (
                          <div className="flex justify-between">
                            <span className="text-slate-500">Density:</span>
                            <span className="font-bold text-slate-900">{typeof density === 'number' ? density.toFixed(2) : density} p/m²</span>
                          </div>
                        )}

                        {/* Strict Physics vs AI Separation */}
                        <div className="pt-1 mt-1 border-t border-slate-200 space-y-1">
                          <div className="flex justify-between">
                            <span className="text-slate-600 font-semibold">Physics Risk:</span>
                            <span className="font-extrabold text-cyan-700">
                              {physicsRisk !== undefined && physicsRisk !== null ? `${typeof physicsRisk === 'number' ? physicsRisk.toFixed(1) : physicsRisk} / 100` : 'N/A'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-600 font-semibold">AI Probability:</span>
                            <span className="font-extrabold text-purple-700">
                              {isAiUnavailable ? 'UNAVAILABLE' : isWarmingUp ? 'WARMING UP' : aiProb !== null && aiProb !== undefined ? `${Math.round(aiProb * 100)}%` : 'N/A'}
                            </span>
                          </div>
                        </div>

                        {timestamp && (
                          <div className="text-[9px] text-slate-400 pt-1 flex items-center gap-1">
                            <Clock className="w-2.5 h-2.5" /> Updated: {new Date(timestamp).toLocaleTimeString()}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="bg-slate-100 p-2 rounded text-[10px] text-slate-500 italic">
                        WAITING FOR LIVE STREAM TELEMETRY...
                      </div>
                    )}

                    {/* Navigation Link */}
                    <div className="pt-1.5 border-t border-slate-200">
                      <Link
                        href={`/zones/${cam.zone_id}`}
                        className="w-full px-3 py-1.5 bg-cyan-600 hover:bg-cyan-700 text-white font-bold rounded text-[11px] flex items-center justify-center gap-1.5 shadow transition"
                      >
                        <ExternalLink className="w-3 h-3" />
                        VIEW ZONE DETAIL
                      </Link>
                    </div>

                    <p className="text-[8px] text-slate-400 leading-tight italic mt-1">
                      AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.
                    </p>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>

        {/* Legend Overlay */}
        <div className="absolute bottom-3 left-3 z-10 bg-slate-950/90 backdrop-blur-md p-2.5 rounded-xl border border-slate-800 text-[10px] space-y-1 shadow-xl">
          <div className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-cyan-400" /> CAMERA GEOLOCATION LEGEND
          </div>
          <div className="flex flex-wrap items-center gap-3 text-slate-400 font-medium">
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> NORMAL</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> WATCH</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-orange-500" /> EARLY WARNING</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" /> HIGH RISK</span>
            <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-full bg-slate-500" /> OFFLINE</span>
          </div>
        </div>
      </div>
    </div>
  );
}
