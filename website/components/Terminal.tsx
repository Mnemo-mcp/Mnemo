'use client';

interface TerminalProps {
  lines: string[];
}

export default function Terminal({ lines }: TerminalProps) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border-subtle">
        <div className="w-2 h-2 rounded-full bg-accent/60" />
        <div className="w-2 h-2 rounded-full bg-text-muted/40" />
        <div className="w-2 h-2 rounded-full bg-text-muted/40" />
        <span className="ml-2 font-mono text-[10px] text-text-muted">mnemo</span>
      </div>
      <div className="p-5 font-mono text-xs leading-relaxed space-y-0.5 overflow-x-auto">
        {lines.map((line, i) => (
          <div key={i} className={line.startsWith('$') ? 'text-accent' : line.startsWith('#') || line.startsWith('[') ? 'text-text-secondary' : 'text-text-muted'}>
            {line || '\u00A0'}
          </div>
        ))}
      </div>
    </div>
  );
}
