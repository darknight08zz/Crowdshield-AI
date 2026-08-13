import { cn } from '@/lib/utils';

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-slate-800/60 border border-slate-700/40', className)}
      {...props}
    />
  );
}

export function ZoneCardSkeleton() {
  return (
    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
      <div className="flex justify-between items-center">
        <Skeleton className="h-5 w-36" />
        <Skeleton className="h-6 w-20 rounded-full" />
      </div>
      <div className="flex justify-between items-end">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-4 w-16" />
      </div>
      <Skeleton className="h-2 w-full rounded" />
      <div className="grid grid-cols-2 gap-2 pt-2">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
      </div>
    </div>
  );
}

export function MapSkeleton() {
  return (
    <div className="relative w-full h-[480px] rounded-xl bg-slate-950 border border-slate-800 overflow-hidden flex flex-col items-center justify-center space-y-3">
      <Skeleton className="h-10 w-48 rounded-lg" />
      <Skeleton className="h-4 w-64" />
      <div className="absolute bottom-4 right-4 flex space-x-2">
        <Skeleton className="h-8 w-8 rounded" />
        <Skeleton className="h-8 w-8 rounded" />
      </div>
    </div>
  );
}
