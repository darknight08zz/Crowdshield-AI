import React from 'react';
import { ConnectionStatus } from '@/lib/realtimeInferenceClient';
import { Wifi, RefreshCw, WifiOff } from 'lucide-react';

interface ConnectionStatusBadgeProps {
  status?: ConnectionStatus | string;
  size?: 'sm' | 'md';
  className?: string;
}

export const ConnectionStatusBadge: React.FC<ConnectionStatusBadgeProps> = ({
  status = 'DISCONNECTED',
  size = 'sm',
  className = '',
}) => {
  const normStatus = (status || 'DISCONNECTED').toUpperCase() as ConnectionStatus;

  let bgClass = 'text-cyan-300 bg-cyan-950/50 border-cyan-500/40';
  let Icon = Wifi;
  let label = 'LIVE STREAM ACTIVE';

  switch (normStatus) {
    case 'CONNECTED':
      bgClass = 'text-cyan-300 bg-cyan-950/50 border-cyan-500/40';
      Icon = Wifi;
      label = 'LIVE STREAM ACTIVE';
      break;
    case 'CONNECTING':
      bgClass = 'text-amber-300 bg-amber-950/50 border-amber-500/40 animate-pulse';
      Icon = RefreshCw;
      label = 'CONNECTING...';
      break;
    case 'RECONNECTING':
      bgClass = 'text-amber-300 bg-amber-950/50 border-amber-500/40 animate-pulse';
      Icon = RefreshCw;
      label = 'RECONNECTING...';
      break;
    case 'DISCONNECTED':
    case 'ERROR':
    default:
      bgClass = 'text-rose-400 bg-rose-950/50 border-rose-500/40';
      Icon = WifiOff;
      label = 'STREAM OFFLINE';
      break;
  }

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-[10px] gap-1 rounded border font-semibold font-mono-nums',
    md: 'px-2.5 py-1 text-xs gap-1.5 rounded-lg border font-bold font-mono-nums',
  };

  return (
    <div
      className={`inline-flex items-center risk-transition ${sizeClasses[size]} ${bgClass} ${className}`}
      title={`WebSocket Stream Status: ${label}`}
    >
      <Icon size={size === 'sm' ? 11 : 13} className={`shrink-0 ${normStatus === 'CONNECTING' || normStatus === 'RECONNECTING' ? 'animate-spin' : ''}`} />
      <span>{label}</span>
    </div>
  );
};
