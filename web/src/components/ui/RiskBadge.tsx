import React from 'react';
import { CheckCircle2, AlertTriangle, ShieldAlert, Siren } from 'lucide-react';
import { getRiskCategory, RiskBucket } from '@/lib/constants';

interface RiskBadgeProps {
  score?: number;
  category?: RiskBucket | string;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  score,
  category,
  size = 'md',
  showScore = true,
  className = '',
}) => {
  const cat = (category as RiskBucket) || (score !== undefined ? getRiskCategory(score) : 'LOW');

  let bgClass = 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400';
  let Icon = CheckCircle2;
  let label = 'LOW';

  switch (cat) {
    case 'LOW':
    case 'SAFE':
      bgClass = 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400';
      Icon = CheckCircle2;
      label = 'LOW';
      break;
    case 'MODERATE':
      bgClass = 'bg-amber-500/15 border-amber-500/40 text-amber-400';
      Icon = AlertTriangle;
      label = 'MODERATE';
      break;
    case 'HIGH':
      bgClass = 'bg-orange-500/15 border-orange-500/40 text-orange-400';
      Icon = ShieldAlert;
      label = 'HIGH';
      break;
    case 'CRITICAL':
      bgClass = 'bg-rose-500/20 border-rose-500/60 text-rose-400 animate-pulse';
      Icon = Siren;
      label = 'CRITICAL';
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs gap-1.5 rounded-md border',
    md: 'px-2.5 py-1 text-xs gap-1.5 rounded-lg border font-semibold',
    lg: 'px-3.5 py-1.5 text-sm gap-2 rounded-lg border-2 font-bold',
  };

  const iconSizes = {
    sm: 13,
    md: 15,
    lg: 18,
  };

  return (
    <div
      className={`inline-flex items-center risk-transition ${sizeClasses[size]} ${bgClass} ${className}`}
      title={`Risk Category: ${label}${score !== undefined ? ` (${score.toFixed(1)}/100)` : ''}`}
    >
      <Icon size={iconSizes[size]} className="shrink-0" />
      <span className="tracking-wider uppercase">{label}</span>
      {showScore && score !== undefined && (
        <span className="font-mono-nums font-bold border-l border-current/30 pl-1.5 ml-0.5">
          {score.toFixed(0)}
        </span>
      )}
    </div>
  );
};
