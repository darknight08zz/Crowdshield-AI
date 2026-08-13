'use client';

import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Polygon, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { ZoneData, GateData, DensityGridData, api } from '@/lib/api';
import { RISK_COLORS, getRiskCategory } from '@/lib/constants';

// Fix default leaflet marker icon path issue in Next.js
const customGateIcon = (status: GateData['status']) =>
  L.divIcon({
    className: 'custom-gate-marker',
    html: `<div style="
      background-color: ${status === 'open' ? '#10b981' : status === 'restricted' ? '#f59e0b' : '#ef4444'};
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 2px solid #ffffff;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
    "></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });

function getContinuousHeatmapColor(riskScore: number): string {
  const score = Math.max(0, Math.min(100, riskScore));
  if (score < 25) {
    const t = score / 25;
    const hue = 140 - t * 85;
    return `hsl(${hue}, 85%, 45%)`;
  } else if (score < 50) {
    const t = (score - 25) / 25;
    const hue = 55 - t * 30;
    return `hsl(${hue}, 90%, 50%)`;
  } else if (score < 75) {
    const t = (score - 50) / 25;
    const hue = 25 - t * 25;
    return `hsl(${hue}, 95%, 50%)`;
  } else {
    const t = (score - 75) / 25;
    const hue = Math.max(0, 0 - t * 10);
    return `hsl(${hue}, 100%, 45%)`;
  }
}

// Sample coordinates for Grand Music Festival 2026 venue
const ZONE_POLYGONS: Record<string, [number, number][]> = {
  'z-1': [
    [37.7749, -122.4194],
    [37.7755, -122.4184],
    [37.7745, -122.4174],
    [37.7739, -122.4184],
  ],
  'z-2': [
    [37.7755, -122.4184],
    [37.7761, -122.4174],
    [37.7751, -122.4164],
    [37.7745, -122.4174],
  ],
  'z-3': [
    [37.7739, -122.4184],
    [37.7745, -122.4174],
    [37.7735, -122.4164],
    [37.7729, -122.4174],
  ],
  'z-4': [
    [37.7745, -122.4174],
    [37.7751, -122.4164],
    [37.7741, -122.4154],
    [37.7735, -122.4164],
  ],
};

const GATE_COORDS: Record<string, [number, number]> = {
  'g-1': [37.7752, -122.4189],
  'g-2': [37.7742, -122.4179],
  'g-3': [37.7758, -122.4179],
  'g-4': [37.7748, -122.4169],
  'g-5': [37.7736, -122.4179],
  'g-6': [37.7738, -122.4159],
};

interface LeafletMapProps {
  zones: ZoneData[];
  gates: GateData[];
  selectedZoneId?: string;
  onSelectZone: (zoneId: string) => void;
}

export default function LeafletMap({ zones, gates, selectedZoneId, onSelectZone }: LeafletMapProps) {
  const center: [number, number] = [37.7745, -122.4174];
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [gridMap, setGridMap] = useState<Record<string, DensityGridData>>({});

  useEffect(() => {
    const fetchGrids = async () => {
      const result: Record<string, DensityGridData> = {};
      const ids = zones.length > 0 ? zones.map(z => z.id) : ['z-1', 'z-2', 'z-3', 'z-4'];
      for (const id of ids) {
        try {
          const g = await api.fetchZoneDensityGrid(id, 6, 6);
          result[id] = g;
        } catch (e) {
          console.error(`Leaflet grid fetch error for ${id}:`, e);
        }
      }
      setGridMap(result);
    };
    fetchGrids();
  }, [zones]);

  // Projects subgrid cell index into geographic lat/lng bounding polygon
  const renderGeographicSubgrid = (zoneId: string, polygonCoords: [number, number][]) => {
    const grid = gridMap[zoneId];
    if (!showHeatmap || !grid || !grid.is_calibrated || !grid.grid_risk_scores) {
      return null;
    }

    const lats = polygonCoords.map(p => p[0]);
    const lngs = polygonCoords.map(p => p[1]);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);

    const rows = grid.grid_dims[0];
    const cols = grid.grid_dims[1];
    const dLat = (maxLat - minLat) / rows;
    const dLng = (maxLng - minLng) / cols;

    const cells: React.ReactNode[] = [];
    grid.grid_risk_scores.forEach((row, r) => {
      row.forEach((score, c) => {
        const cellMinLat = maxLat - (r + 1) * dLat;
        const cellMaxLat = maxLat - r * dLat;
        const cellMinLng = minLng + c * dLng;
        const cellMaxLng = minLng + (c + 1) * dLng;

        const cellBounds: [number, number][] = [
          [cellMaxLat, cellMinLng],
          [cellMaxLat, cellMaxLng],
          [cellMinLat, cellMaxLng],
          [cellMinLat, cellMinLng],
        ];

        cells.push(
          <Polygon
            key={`geo-cell-${zoneId}-${r}-${c}`}
            positions={cellBounds}
            pathOptions={{
              color: 'transparent',
              fillColor: getContinuousHeatmapColor(score),
              fillOpacity: 0.60,
              weight: 0,
            }}
          />
        );
      });
    });

    return <g key={`subgrid-group-${zoneId}`}>{cells}</g>;
  };

  return (
    <div className="w-full h-[480px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl relative">
      {/* Map Control Overlay */}
      <div className="absolute top-3 left-3 z-10 flex items-center space-x-2 bg-slate-950/85 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-xs shadow-lg">
        <button
          onClick={() => setShowHeatmap(!showHeatmap)}
          className={`px-2.5 py-1 rounded font-semibold transition ${showHeatmap ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40' : 'bg-slate-800 text-slate-400'}`}
        >
          {showHeatmap ? '🔥 Heatmap Grid ON' : '🗺️ Standard Zones'}
        </button>
      </div>

      <MapContainer
        center={center}
        zoom={16}
        scrollWheelZoom={false}
        className="w-full h-full z-0 bg-slate-950"
      >
        {/* 100% Free OpenStreetMap Tiles */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Zone Polygons & Continuous Subgrid Density Overlay */}
        {zones.map((zone) => {
          const coords = ZONE_POLYGONS[zone.id] || ZONE_POLYGONS['z-1'];
          const category = getRiskCategory(zone.risk_score);
          const colors = RISK_COLORS[category];
          const isSelected = selectedZoneId === zone.id;
          const gridInfo = gridMap[zone.id];

          return (
            <React.Fragment key={zone.id}>
              {/* Geographic Subgrid Continuous Heatmap Overlay for Calibrated Zones */}
              {renderGeographicSubgrid(zone.id, coords)}

              <Polygon
                positions={coords}
                pathOptions={{
                  color: isSelected ? '#38bdf8' : colors.fill,
                  fillColor: (showHeatmap && gridInfo?.is_calibrated) ? 'transparent' : colors.fill,
                  fillOpacity: isSelected ? 0.65 : 0.35,
                  weight: isSelected ? 3 : 2,
                }}
                eventHandlers={{
                  click: () => onSelectZone(zone.id),
                }}
              >
                <Popup className="text-xs font-sans">
                  <div className="font-bold text-slate-900">{zone.name}</div>
                  <div>Risk Score: <strong>{zone.risk_score.toFixed(1)} / 100</strong></div>
                  <div>Density: <strong>{Math.round((zone.current_density || 0) * 100)}%</strong></div>
                  {gridInfo && (
                    <div className="mt-1 text-[10px] text-slate-600 font-semibold">
                      {gridInfo.is_calibrated
                        ? `✅ Calibrated Grid (${gridInfo.grid_dims[0]}x${gridInfo.grid_dims[1]})`
                        : `⚠️ ${gridInfo.warning_banner || 'Uncalibrated Area-Only Fill'}`}
                    </div>
                  )}
                </Popup>
              </Polygon>
            </React.Fragment>
          );
        })}

        {/* Gate Markers */}
        {gates.map((gate) => {
          const coords = GATE_COORDS[gate.id] || GATE_COORDS['g-1'];
          return (
            <Marker key={gate.id} position={coords} icon={customGateIcon(gate.status)}>
              <Popup className="text-xs font-sans">
                <div className="font-bold text-slate-900">{gate.name}</div>
                <div>Status: <strong className="uppercase">{gate.status}</strong></div>
                <div>Type: <strong className="uppercase">{gate.type}</strong></div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Map Overlay Badge */}
      <div className="absolute bottom-3 left-3 z-10 px-3 py-1 bg-slate-950/80 backdrop-blur-md rounded-lg border border-slate-800 text-[10px] text-slate-400 font-semibold flex items-center gap-1.5 shadow-lg">
        <span className="w-2 h-2 rounded-full bg-emerald-400" />
        <span>OpenStreetMap Geographic Grid Layer</span>
      </div>
    </div>
  );
}

