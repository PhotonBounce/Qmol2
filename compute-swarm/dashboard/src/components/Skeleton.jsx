import React from 'react'

function SkeletonPulse({ className }) {
  return (
    <div className={`animate-pulse rounded bg-slate-200 ${className}`} />
  )
}

export function SkeletonCard() {
  return (
    <div className="card space-y-4">
      <div className="flex items-center gap-4">
        <SkeletonPulse className="h-12 w-12 rounded-lg" />
        <div className="flex-1 space-y-2">
          <SkeletonPulse className="h-4 w-1/3" />
          <SkeletonPulse className="h-6 w-1/2" />
        </div>
      </div>
    </div>
  )
}

export function SkeletonTable({ rows = 5, cols = 4 }) {
  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              {Array.from({ length: cols }).map((_, i) => (
                <th key={i} className="px-6 py-3">
                  <SkeletonPulse className="h-4 w-16" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {Array.from({ length: rows }).map((_, r) => (
              <tr key={r}>
                {Array.from({ length: cols }).map((__, c) => (
                  <td key={c} className="px-6 py-4">
                    <SkeletonPulse className="h-4 w-full" />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function SkeletonChart() {
  return (
    <div className="card">
      <SkeletonPulse className="h-6 w-1/3 mb-4" />
      <SkeletonPulse className="h-72 w-full rounded-lg" />
    </div>
  )
}

export default function Skeleton({ variant = 'card', rows, cols }) {
  if (variant === 'table') return <SkeletonTable rows={rows} cols={cols} />
  if (variant === 'chart') return <SkeletonChart />
  return <SkeletonCard />
}
