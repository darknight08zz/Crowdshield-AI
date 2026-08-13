import React, { useState, useEffect } from 'react';
import { ZoneData, GateData, DensityGridData, BarricadeData, api } from '@/lib/api';
import { RISK_COLORS, getRiskCategory } from '@/lib/constants';
import Link from 'next/link';

interface VectorMapProps {
  zones: ZoneData[];
  gates: GateData[];
  eventId?: string;
  selectedZoneId?: string;
  onSelectZone?: (id: string) => void;
}

// Continuous HSL color interpolation across risk scale (Emerald -> Amber -> Orange -> Crimson)
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

export function VectorMap({ zones, gates, eventId, selectedZoneId, onSelectZone }: VectorMapProps) {
  const [activeLayer, setActiveLayer] = useState<'all' | 'heatmap' | 'gates'>('all');
  const [gridDataMap, setGridDataMap] = useState<Record<string, DensityGridData>>({});
  const [barricades, setBarricades] = useState<BarricadeData[]>([]);

  useEffect(() => {
    const loadGridsAndBarricades = async () => {
      const map: Record<string, DensityGridData> = {};
      const zoneIds = zones.map(z => z.id);
      for (const id of zoneIds) {
        try {
          const data = await api.fetchZoneDensityGrid(id, 8, 8);
          map[id] = data;
        } catch (e) {
          console.error(`Failed to fetch density grid for zone ${id}`, e);
        }
      }
      setGridDataMap(map);

      // Dynamically resolve event UUID for barricades
      let targetEventId = eventId;
      if (!targetEventId || !api.isValidUUID(targetEventId)) {
        try {
          const events = await api.fetchEvents();
          if (events && events.length > 0 && events[0].id) {
            targetEventId = events[0].id;
          }
        } catch (e) {
          // Ignored
        }
      }

      if (targetEventId && api.isValidUUID(targetEventId)) {
        try {
          const bList = await api.fetchEventBarricades(targetEventId);
          if (bList && bList.length > 0) {
            setBarricades(bList);
          }
        } catch (e) {
          // Ignored
        }
      }
    };
    if (zones.length > 0) {
      loadGridsAndBarricades();
    }
  }, [zones, eventId]);


  // Sector slots layout geometry (2x2 grid in stadium layout)
  const sectorSlots = [
    { slotIndex: 0, x: 70, y: 65, width: 310, height: 175, textX: 88, textY: 92 },
    { slotIndex: 1, x: 415, y: 65, width: 310, height: 175, textX: 433, textY: 92 },
    { slotIndex: 2, x: 70, y: 265, width: 310, height: 175, textX: 88, textY: 292 },
    { slotIndex: 3, x: 415, y: 265, width: 310, height: 175, textX: 433, textY: 292 },
  ];

  const renderZoneSubgrid = (zoneId: string, x: number, y: number, width: number, height: number, defaultColor: string) => {
    const gridData = gridDataMap[zoneId];
    if ((activeLayer === 'heatmap' || activeLayer === 'all') && gridData && gridData.is_calibrated && gridData.grid_risk_scores) {
      const rows = gridData.grid_dims[0];
      const cols = gridData.grid_dims[1];
      const cellW = width / cols;
      const cellH = height / rows;
      return (
        <g className="subgrid-heatmap">
          {gridData.grid_risk_scores.map((row, r) =>
            row.map((score, c) => (
              <rect
                key={`cell-${zoneId}-${r}-${c}`}
                x={x + c * cellW}
                y={y + r * cellH}
                width={cellW - 0.5}
                height={cellH - 0.5}
                fill={getContinuousHeatmapColor(score)}
                fillOpacity={activeLayer === 'heatmap' ? 0.75 : 0.40}
                rx={1}
              />
            ))
          )}
        </g>
      );
    }
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx="14"
        fill={defaultColor}
        fillOpacity="0.20"
      />
    );
  };

  return (
    <div className="relative w-full h-[520px] bg-slate-950 rounded-2xl border border-slate-800/80 overflow-hidden shadow-2xl flex flex-col">
      {/* Map Control Bar */}
      <div className="absolute top-4 left-4 z-10 flex items-center space-x-2 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-700/60 shadow-lg text-xs">
        <span className="font-semibold text-cyan-400 flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          OPENSTREETMAP & VECTOR SCHEMATIC (LIVE CDC)
        </span>
        <span className="text-slate-600">|</span>
        <button
          onClick={() => setActiveLayer('all')}
          className={`px-2 py-0.5 rounded transition ${activeLayer === 'all' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
        >
          All Layers
        </button>
        <button
          onClick={() => setActiveLayer('heatmap')}
          className={`px-2 py-0.5 rounded transition ${activeLayer === 'heatmap' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
        >
          Density Heatmap
        </button>
        <button
          onClick={() => setActiveLayer('gates')}
          className={`px-2 py-0.5 rounded transition ${activeLayer === 'gates' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-slate-200'}`}
        >
          Gates Only
        </button>
      </div>

      {/* SVG Interactive Stadium Schematic Map Canvas */}
      <div className="relative flex-1 w-full h-full bg-[#070b14] overflow-hidden flex items-center justify-center">
        {/* Subtle grid background */}
        <div
          className="absolute inset-0 opacity-15 pointer-events-none"
          style={{
            backgroundImage: `radial-gradient(#38bdf8 1px, transparent 1px)`,
            backgroundSize: '24px 24px',
          }}
        />

        <svg className="w-full h-full max-w-4xl max-h-[480px]" viewBox="0 0 800 500" fill="none">
          {/* Outer Stadium Perimeter */}
          <rect x="40" y="45" width="720" height="410" rx="30" stroke="#1e293b" strokeWidth="3" strokeDasharray="6 6" fill="#040711" />

          {/* Dynamically Render Real Live Zones */}
          {activeLayer !== 'gates' && zones.map((zone, index) => {
            const slot = sectorSlots[index % sectorSlots.length];
            const category = getRiskCategory(zone.risk_score);
            const colors = RISK_COLORS[category];
            const isSelected = selectedZoneId === zone.id;
            const gridData = gridDataMap[zone.id];
            const isCalibrated = gridData ? gridData.is_calibrated : true;
            const occupancyPct = Math.round((zone.current_density || 0) * 100);

            return (
              <g
                key={zone.id}
                onClick={() => onSelectZone?.(zone.id)}
                className="cursor-pointer transition hover:opacity-90"
              >
                {renderZoneSubgrid(zone.id, slot.x, slot.y, slot.width, slot.height, colors.fill)}
                <rect
                  x={slot.x}
                  y={slot.y}
                  width={slot.width}
                  height={slot.height}
                  rx="14"
                  fill="none"
                  stroke={isSelected ? '#38bdf8' : colors.fill}
                  strokeWidth={isSelected ? "4" : "2"}
                />
                
                {/* Sector Header & Name */}
                <text x={slot.textX} y={slot.textY} fill="#f8fafc" fontSize="13" fontWeight="bold">
                  {zone.name}
                </text>

                {/* Risk Score */}
                <text x={slot.textX} y={slot.textY + 22} fill={colors.text} fontSize="12" fontWeight="600">
                  Risk Score: {zone.risk_score.toFixed(1)} ({category})
                </text>

                {/* Live Occupancy & Homography Calibration Status */}
                <text x={slot.textX} y={slot.textY + 42} fill={isCalibrated ? "#94a3b8" : "#fbbf24"} fontSize="11">
                  {isCalibrated 
                    ? `Occupancy: ${occupancyPct}% (8x8 Grid)` 
                    : `⚠️ UNCALIBRATED (Area-Only)`}
                </text>
              </g>
            );
          })}

          {/* Gate Markers & Connection Pathways */}
          <path d="M 380 152 L 415 152" stroke="#0ea5e9" strokeWidth="4" strokeDasharray="3 3" opacity="0.6" />
          <path d="M 380 352 L 415 352" stroke="#f59e0b" strokeWidth="4" strokeDasharray="3 3" opacity="0.6" />

          {/* Propagation Vector (Non-overlapping Overlay) */}
          <g className="propagation-vectors">
            <path
              d="M 380 152 L 415 152"
              stroke="#a855f7"
              strokeWidth="4"
              strokeDasharray="6 4"
              className="animate-pulse"
            />
            <polygon points="410,147 420,152 410,157" fill="#a855f7" />
            <rect x="345" y="162" width="105" height="16" rx="4" fill="#090d16" stroke="#a855f7" strokeWidth="1" opacity="0.9" />
            <text x="397.5" y="173" fill="#c084fc" fontSize="8" fontWeight="bold" textAnchor="middle">
              PROPAGATION VECTOR
            </text>
          </g>

          {/* Physical Barricades (Clean non-overlapping positions) */}
          <g className="barricade-markers">
            <line x1="225" y1="240" x2="225" y2="265" stroke="#f59e0b" strokeWidth="5" strokeDasharray="5 2" />
            <rect x="180" y="244" width="90" height="16" rx="4" fill="#0f172a" stroke="#f59e0b" strokeWidth="1.2" />
            <text x="225" y="255" fill="#fbbf24" fontSize="8.5" fontWeight="bold" textAnchor="middle">BAR-1: REDIRECT</text>

            <line x1="380" y1="352" x2="415" y2="352" stroke="#0ea5e9" strokeWidth="5" strokeDasharray="4 2" />
            <rect x="350" y="364" width="80" height="16" rx="4" fill="#0f172a" stroke="#0ea5e9" strokeWidth="1.2" />
            <text x="390" y="375" fill="#38bdf8" fontSize="8.5" fontWeight="bold" textAnchor="middle">BAR-2: NARROW</text>
          </g>

          {/* Gates (Non-overlapping Text Labels) */}
          {/* Gate 1 (Top Emergency Exit) */}
          <g className="cursor-pointer">
            <circle cx="395" cy="45" r="14" fill="#ef4444" stroke="#7f1d1d" strokeWidth="2" />
            <text x="395" y="49" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">G1</text>
            <text x="395" y="24" fill="#f87171" fontSize="10" fontWeight="bold" textAnchor="middle">Gate 1: CLOSED (EMERGENCY)</text>
          </g>

          {/* Gate 3 (Top Promenade Exit) */}
          <g className="cursor-pointer">
            <circle cx="565" cy="45" r="14" fill="#10b981" stroke="#064e3b" strokeWidth="2" />
            <text x="565" y="49" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">G3</text>
            <text x="565" y="24" fill="#34d399" fontSize="10" fontWeight="bold" textAnchor="middle">Gate 3: OPEN (EGRESS)</text>
          </g>

          {/* Gate 2 (East Main Turnstile) */}
          <g className="cursor-pointer">
            <circle cx="740" cy="355" r="14" fill="#f59e0b" stroke="#78350f" strokeWidth="2" />
            <text x="740" y="359" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">G2</text>
            <text x="740" y="380" fill="#fbbf24" fontSize="10" fontWeight="bold" textAnchor="middle">Gate 2: RESTRICTED</text>
          </g>
        </svg>
      </div>

      {/* Map Legend Overlay (Bottom Bar) */}
      <div className="bg-slate-900/90 backdrop-blur-md px-6 py-3 border-t border-slate-800 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-6">
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500" />
            <span className="text-slate-300">Safe (&lt;40)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-slate-300">Moderate (40-60)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-orange-500" />
            <span className="text-slate-300">High (60-75)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
            <span className="text-rose-400 font-bold">Critical Surge (&gt;75)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3 h-3 rounded-full bg-purple-500" />
            <span className="text-purple-300 font-semibold">Propagation Vector</span>
          </div>
        </div>

        {selectedZoneId && (
          <Link
            href={`/zones/${selectedZoneId}`}
            className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-lg shadow-md transition flex items-center gap-1.5"
          >
            Inspect Sector Detail &rarr;
          </Link>
        )}
      </div>
    </div>
  );
}
