'use client';

import React, { useState } from 'react';
import dynamic from 'next/dynamic';
import { VectorMap } from './VectorMap';
import { ZoneData, GateData } from '@/lib/api';
import { Layers, MapPin } from 'lucide-react';
import { Skeleton } from '@/components/ui/Skeleton';

// Dynamically import Leaflet CrowdShieldMap with SSR disabled
const CrowdShieldMap = dynamic(() => import('./CrowdShieldMap'), {
  ssr: false,
  loading: () => <Skeleton className="w-full h-[480px] rounded-2xl" />,
});

interface InteractiveMapProps {
  zones: ZoneData[];
  gates: GateData[];
  selectedZoneId?: string;
  onSelectZone: (zoneId: string) => void;
}

export function InteractiveMap({ zones, gates, selectedZoneId, onSelectZone }: InteractiveMapProps) {
  const [mapType, setMapType] = useState<'svg' | 'leaflet'>('leaflet');

  return (
    <div className="space-y-3">
      {/* View Mode Toggle Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center space-x-2 bg-slate-950/80 p-1 rounded-xl border border-slate-800 text-xs">
          <button
            onClick={() => setMapType('leaflet')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              mapType === 'leaflet'
                ? 'bg-cyan-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <MapPin className="w-3.5 h-3.5" />
            GEOSPATIAL CCTV MAP (LEAFLET)
          </button>
          <button
            onClick={() => setMapType('svg')}
            className={`px-3 py-1 rounded-lg font-bold transition flex items-center gap-1.5 ${
              mapType === 'svg'
                ? 'bg-cyan-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            STADIUM SCHEMATIC (SVG)
          </button>
        </div>

        <span className="text-[10px] text-slate-400 font-mono">
          MODE: <strong className="text-cyan-400">{mapType.toUpperCase()}</strong> (OPENSTREETMAP / ZERO API COST)
        </span>
      </div>

      {/* Map Content */}
      {mapType === 'leaflet' ? (
        <CrowdShieldMap
          selectedZoneId={selectedZoneId}
          onSelectZone={onSelectZone}
        />
      ) : (
        <VectorMap
          zones={zones}
          gates={gates}
          selectedZoneId={selectedZoneId}
          onSelectZone={onSelectZone}
        />
      )}
    </div>
  );
}
