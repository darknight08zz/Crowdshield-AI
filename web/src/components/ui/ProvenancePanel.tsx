import React from 'react';
import { AlertTriangle, Cpu } from 'lucide-react';
import { ModelProvenance } from '@/lib/api';

interface ProvenancePanelProps {
  provenance?: ModelProvenance | any;
  disclaimer?: string;
  className?: string;
}

export const ProvenancePanel: React.FC<ProvenancePanelProps> = ({
  provenance,
  disclaimer = 'AI Early Warning — Prototype. Physics-defined proxy model, not operationally validated.',
  className = '',
}) => {
  const modelVersion = provenance?.model_version || 'v2.0.0';
  const target = provenance?.target || 'EARLY_ESCALATION_5M';
  const horizon = provenance?.horizon_seconds || 300;
  const status = provenance?.model_status || 'PROTOTYPE';
  const labelType = provenance?.label_type || 'PHYSICS_DEFINED_PROXY';

  return (
    <div className={`p-4 rounded-xl bg-amber-950/40 border border-amber-500/40 text-amber-200/90 leading-normal space-y-2.5 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="font-extrabold text-xs text-amber-300 flex items-center gap-1.5 uppercase tracking-wider">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          <span>AI PROTOTYPE PROVENANCE & SAFETY DISCLAIMER</span>
        </div>
        <span className="px-2 py-0.5 text-[9px] font-black rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 uppercase tracking-widest font-mono-nums">
          {status}
        </span>
      </div>

      <p className="text-[11px] text-amber-200/90 leading-relaxed font-sans">
        {disclaimer}
      </p>

      <div className="pt-2 border-t border-amber-500/20 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px] font-mono-nums">
        <div>
          <span className="text-amber-400/60 block">MODEL VERSION</span>
          <span className="font-extrabold text-amber-300">{modelVersion}</span>
        </div>
        <div>
          <span className="text-amber-400/60 block">PREDICTION TARGET</span>
          <span className="font-extrabold text-amber-300">{target}</span>
        </div>
        <div>
          <span className="text-amber-400/60 block">HORIZON</span>
          <span className="font-extrabold text-amber-300">{horizon} seconds</span>
        </div>
        <div>
          <span className="text-amber-400/60 block">LABEL CLASSIFICATION</span>
          <span className="font-extrabold text-amber-300">{labelType}</span>
        </div>
      </div>
    </div>
  );
};
