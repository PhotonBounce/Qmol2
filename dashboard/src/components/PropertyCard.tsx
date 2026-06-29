import { CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';
import type { PropertyDisplay } from '@/types/api';

interface PropertyCardProps {
  property: PropertyDisplay;
  compact?: boolean;
}

const statusConfig = {
  good: {
    icon: CheckCircle,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-50 dark:bg-emerald-950/30',
    border: 'border-emerald-200 dark:border-emerald-800',
    bar: 'bg-emerald-500',
  },
  warning: {
    icon: AlertTriangle,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    border: 'border-amber-200 dark:border-amber-800',
    bar: 'bg-amber-500',
  },
  alert: {
    icon: AlertCircle,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-950/30',
    border: 'border-red-200 dark:border-red-800',
    bar: 'bg-red-500',
  },
};

export default function PropertyCard({ property, compact = false }: PropertyCardProps) {
  const config = statusConfig[property.status];
  const Icon = config.icon;

  if (compact) {
    return (
      <div className={`card p-3 ${config.border} border`}>
        <div className="flex items-center justify-between">
          <span className="text-xs text-[var(--fg-muted)]">{property.name}</span>
          <Icon size={14} className={config.color} />
        </div>
        <div className="mt-1 flex items-baseline gap-1">
          <span className="text-lg font-semibold text-[var(--fg-primary)]">{property.value}</span>
          <span className="text-xs text-[var(--fg-muted)]">{property.unit}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`card p-4 ${config.border} border card-hover`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-[var(--fg-primary)]">{property.name}</h3>
            <span
              className={`badge ${
                property.inDomain ? 'badge-green' : 'badge-yellow'
              }`}
            >
              {property.inDomain ? 'In domain' : 'Out of domain'}
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-[var(--fg-primary)]">
              {property.value}
            </span>
            <span className="text-sm text-[var(--fg-muted)]">{property.unit}</span>
          </div>
          {property.description && (
            <p className="mt-1 text-xs text-[var(--fg-muted)]">{property.description}</p>
          )}
        </div>
        <div className={`rounded-lg p-2 ${config.bg}`}>
          <Icon size={20} className={config.color} />
        </div>
      </div>

      {/* Confidence bar */}
      <div className="mt-4">
        <div className="mb-1 flex items-center justify-between text-xs">
          <span className="text-[var(--fg-muted)]">Confidence</span>
          <span className="font-medium text-[var(--fg-primary)]">
            {Math.round(property.confidence * 100)}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
          <div
            className={`h-full rounded-full transition-all ${config.bar}`}
            style={{ width: `${property.confidence * 100}%` }}
            role="progressbar"
            aria-valuenow={Math.round(property.confidence * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      </div>
    </div>
  );
}
