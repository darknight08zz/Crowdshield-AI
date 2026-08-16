import React from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle2, Eye, Cog, AlertCircle } from 'lucide-react';

export type OperationalWarningState = 
  | 'HIGH_RISK'
  | 'EARLY_WARNING'
  | 'WATCH'
  | 'NORMAL'
  | 'WARMING_UP'
  | 'DEGRADED';

interface OperationalWarningBadgeProps {
  state?: OperationalWarningState | string;
  size?: 'sm' | 'md' | 'lg';
  showSubtitle?: boolean;
  className?: string;
}

export const OperationalWarningBadge: React.FC<OperationalWarningBadgeProps> = ({
  state = 'NORMAL',
  size = 'md',
  showSubtitle = false,
  className = '',
}) => {
  const normState = (state || 'NORMAL').toUpperCase() as OperationalWarningState;

  let bgClass = 'bg-emerald-950/80 border-emerald-500/60 text-emerald-300';
  let Icon = CheckCircle2;
  let label = 'NORMAL';
  let subtitle = 'Sectors within safe operational density';

  switch (normState) {
    case 'HIGH_RISK':
      bgClass = 'bg-rose-950/90 border-rose-500/80 text-rose-300 animate-pulse shadow-lg shadow-rose-950/50';
      Icon = ShieldAlert;
      label = 'HIGH RISK';
      subtitle = 'Immediate tactical intervention required';
      break;
    case 'EARLY_WARNING':
      bgClass = 'bg-amber-950/90 border-amber-500/80 text-amber-300 animate-pulse shadow-lg shadow-amber-950/50';
      Icon = AlertTriangle;
      label = 'EARLY WARNING';
      subtitle = 'AI early-warning threshold reached';
      break;
    case 'WATCH':
      bgClass = 'bg-yellow-950/70 border-yellow-500/60 text-yellow-300';
      Icon = Eye;
      label = 'WATCH';
      subtitle = 'Elevated crowd density build-up';
      break;
    case 'WARMING_UP':
      bgClass = 'bg-slate-900 border-cyan-500/50 text-cyan-300 animate-pulse';
      Icon = Cog;
      label = 'WARMING UP';
      subtitle = 'AI Analysis Warming Up — Collecting temporal history...';
      break;
    case 'DEGRADED':
      bgClass = 'bg-slate-900 border-amber-500/50 text-amber-400';
      Icon = AlertCircle;
      label = 'DEGRADED';
      subtitle = 'CV or AI Pipeline Degraded — Reduced confidence';
      break;
    case 'NORMAL':
    default:
      bgClass = 'bg-emerald-950/80 border-emerald-500/60 text-emerald-300';
      Icon = CheckCircle2;
      label = 'NORMAL';
      subtitle = 'Sectors within safe operational density';
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] gap-1 rounded font-bold border uppercase tracking-wider',
    md: 'px-2.5 py-1 text-xs gap-1.5 rounded-lg font-black border uppercase tracking-wider',
    lg: 'px-3.5 py-1.5 text-sm gap-2 rounded-xl font-extrabold border-2 uppercase tracking-wider',
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 18,
  };

  return (
    <div className={`inline-flex flex-col ${className}`}>
      <div
        className={`inline-flex items-center risk-transition ${sizeClasses[size]} ${bgClass}`}
        title={`Operational Warning State: ${label} - ${subtitle}`}
      >
        <Icon size={iconSizes[size]} className="shrink-0" />
        <span className="font-mono-nums">{label}</span>
      </div>
      {showSubtitle && (
        <span className="text-[10px] text-slate-400 mt-1 font-medium">{subtitle}</span>
      )}
    </div>
  );
};
