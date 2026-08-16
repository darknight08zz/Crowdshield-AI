'use client';

import React from 'react';
import { IncidentProvenanceData } from '@/types/incident';
import { ShieldAlert, Info, Cpu, CheckCircle } from 'lucide-react';

interface IncidentProvenancePanelProps {
  provenance: IncidentProvenanceData;
}

export function IncidentProvenancePanel({ provenance }: IncidentProvenancePanelProps) {
  const p = provenance || {
    model_version: 'v2.0.0',
    prediction_target: 'EARLY_ESCALATION_5M',
    label_type: 'PHYSICS_DEFINED_PROXY',
    model_status: 'PROTOTYPE',
    ground_truth_status: 'NOT_CLINICALLY_OR_OPERATIONALLY_VALIDATED',
    generalization_status: 'INSUFFICIENT_INDEPENDENT_EVENTS_FOR_GENERALIZATION',
    disclaimer: 'AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.',
  };

  return (
    <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <h4 className="text-xs font-extrabold text-white tracking-wider uppercase">
            AI PROVENANCE & MODEL METADATA
          </h4>
        </div>
        <span className="px-2 py-0.5 text-[9px] font-black rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 uppercase">
          {p.model_status || 'PROTOTYPE'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[10px] text-slate-500 font-bold uppercase">MODEL VERSION</div>
          <div className="font-semibold text-slate-200 font-mono-nums">{p.model_version}</div>
        </div>
        <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[10px] text-slate-500 font-bold uppercase">PREDICTION TARGET</div>
          <div className="font-semibold text-slate-200 font-mono-nums">{p.prediction_target}</div>
        </div>
        <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[10px] text-slate-500 font-bold uppercase">PREDICTION HORIZON</div>
          <div className="font-semibold text-slate-200 font-mono-nums">300 seconds (5m)</div>
        </div>
        <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
          <div className="text-[10px] text-slate-500 font-bold uppercase">LABEL CLASSIFICATION</div>
          <div className="font-semibold text-slate-200 font-mono-nums">{p.label_type}</div>
        </div>
      </div>

      {/* Mandatory Disclaimer Box */}
      <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30 text-[11px] text-rose-300 flex items-start gap-2.5">
        <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold">MANDATORY OPERATIONAL DISCLAIMER</div>
          <div className="text-slate-300 leading-relaxed">
            {p.disclaimer || 'AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.'}
          </div>
        </div>
      </div>
    </div>
  );
}
