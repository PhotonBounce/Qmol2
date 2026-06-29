import { useState, useMemo } from 'react';

interface MoleculeViewerProps {
  smiles: string;
  size?: number;
}

/**
 * Simple SVG-based molecule viewer fallback.
 * In production, replace with RDKit.js when available:
 *   const RDKit = await window.RDKit.get_mol(smiles);
 *   const svg = RDKit.get_svg();
 */
export default function MoleculeViewer({ smiles, size = 200 }: MoleculeViewerProps) {
  const [hovered, setHovered] = useState(false);

  // Very simple heuristic: count atoms by common symbols
  const { formula, mw } = useMemo(() => {
    const atoms: Record<string, number> = {};
    const tokenRegex = /[A-Z][a-z]?|\d+|\[.*?\]|./g;
    const tokens = smiles.match(tokenRegex) || [];
    for (const t of tokens) {
      if (/^[A-Z][a-z]?$/.test(t)) {
        atoms[t] = (atoms[t] || 0) + 1;
      }
    }
    const weights: Record<string, number> = { C: 12.01, H: 1.008, N: 14.01, O: 15.999, S: 32.06, P: 30.97, F: 19.0, Cl: 35.45, Br: 79.9, I: 126.9 };
    let formulaStr = '';
    let mwCalc = 0;
    for (const [atom, count] of Object.entries(atoms)) {
      formulaStr += atom + (count > 1 ? count : '');
      mwCalc += (weights[atom] || 0) * count;
    }
    return { formula: formulaStr || 'Unknown', mw: mwCalc.toFixed(2) };
  }, [smiles]);

  // Generate a deterministic pseudo-structure visualization
  const svgContent = useMemo(() => {
    const seed = smiles.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    const rand = (s: number) => {
      const x = Math.sin(s * 9301 + 49297) * 0.5 + 0.5;
      return x;
    };
    const cx = size / 2;
    const cy = size / 2;
    const radius = size * 0.35;
    const numNodes = Math.min(Math.max(4, smiles.length % 12 + 4), 10);
    const nodes: Array<{ x: number; y: number; r: number; color: string }> = [];
    for (let i = 0; i < numNodes; i++) {
      const angle = (i / numNodes) * Math.PI * 2 + rand(seed + i) * 0.5;
      const r = radius * (0.6 + rand(seed + i + 100) * 0.4);
      nodes.push({
        x: cx + Math.cos(angle) * r,
        y: cy + Math.sin(angle) * r,
        r: 4 + rand(seed + i + 200) * 6,
        color: ['#0d9488', '#14b8a6', '#2dd4bf', '#5eead4', '#0f766e'][i % 5],
      });
    }
    const lines: Array<{ x1: number; y1: number; x2: number; y2: number; opacity: number }> = [];
    for (let i = 0; i < nodes.length; i++) {
      const next = (i + 1) % nodes.length;
      lines.push({
        x1: nodes[i].x,
        y1: nodes[i].y,
        x2: nodes[next].x,
        y2: nodes[next].y,
        opacity: 0.3 + rand(seed + i + 300) * 0.4,
      });
      // Cross connections
      if (i < nodes.length - 2 && rand(seed + i + 400) > 0.6) {
        const cross = (i + 2) % nodes.length;
        lines.push({
          x1: nodes[i].x,
          y1: nodes[i].y,
          x2: nodes[cross].x,
          y2: nodes[cross].y,
          opacity: 0.2,
        });
      }
    }
    return { nodes, lines };
  }, [smiles, size]);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <svg width={size} height={size} className="rounded-lg bg-[var(--bg-tertiary)]">
        {svgContent.lines.map((line, i) => (
          <line
            key={`l-${i}`}
            x1={line.x1}
            y1={line.y1}
            x2={line.x2}
            y2={line.y2}
            stroke="var(--fg-muted)"
            strokeWidth={1.5}
            opacity={line.opacity}
          />
        ))}
        {svgContent.nodes.map((node, i) => (
          <circle
            key={`n-${i}`}
            cx={node.x}
            cy={node.y}
            r={node.r}
            fill={node.color}
            opacity={0.85}
          />
        ))}
      </svg>
      {hovered && (
        <div className="absolute -top-2 left-1/2 z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-[var(--bg-secondary)] px-3 py-2 text-xs shadow-lg border border-[var(--border)]">
          <div className="font-medium text-[var(--fg-primary)]">{formula}</div>
          <div className="text-[var(--fg-muted)]">MW: {mw} g/mol</div>
          <div className="mt-1 max-w-[200px] truncate text-[10px] text-[var(--fg-muted)] font-mono">
            {smiles}
          </div>
          <div className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 bg-[var(--bg-secondary)] border-r border-b border-[var(--border)]" />
        </div>
      )}
    </div>
  );
}
