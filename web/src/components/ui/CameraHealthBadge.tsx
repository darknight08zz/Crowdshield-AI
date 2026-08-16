import React from 'react';
import { Camera, AlertCircle, VideoOff } from 'lucide-react';

export type CameraHealthStatus = 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'CV_UNAVAILABLE';

interface CameraHealthBadgeProps {
  status?: CameraHealthStatus | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const CameraHealthBadge: React.FC<CameraHealthBadgeProps> = ({
  status = 'ONLINE',
  size = 'sm',
  className = '',
}) => {
  const normStatus = (status || 'ONLINE').toUpperCase() as CameraHealthStatus;

  let bgClass = 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400';
  let Icon = Camera;
  let label = 'Camera Online';

  switch (normStatus) {
    case 'ONLINE':
      bgClass = 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400';
      Icon = Camera;
      label = 'Camera Online';
      break;
    case 'DEGRADED':
      bgClass = 'bg-amber-950/60 border-amber-500/40 text-amber-400';
      Icon = AlertCircle;
      label = 'Camera Degraded';
      break;
    case 'OFFLINE':
      bgClass = 'bg-rose-950/60 border-rose-500/40 text-rose-400';
      Icon = VideoOff;
      label = 'Camera Offline';
      break;
    case 'CV_UNAVAILABLE':
      bgClass = 'bg-slate-900 border-slate-700 text-slate-400';
      Icon = AlertCircle;
      label = 'CV Unavailable';
      break;
    default:
      bgClass = 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400';
      Icon = Camera;
      label = 'Camera Online';
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] gap-1 rounded border font-semibold font-mono-nums',
    md: 'px-2.5 py-1 text-xs gap-1.5 rounded-lg border font-bold font-mono-nums',
  };

  return (
    <div
      className={`inline-flex items-center risk-transition ${sizeClasses[size]} ${bgClass} ${className}`}
      title={`Camera Health: ${label}`}
    >
      <Icon size={size === 'sm' ? 11 : 13} className="shrink-0" />
      <span>{label}</span>
    </div>
  );
};
