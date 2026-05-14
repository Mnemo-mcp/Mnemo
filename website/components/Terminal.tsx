'use client';

interface TerminalProps {
  lines: string[];
}

export default function Terminal({ lines }: TerminalProps) {
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border-subtle">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
        <span className="ml-2 font-mono text-[10px] text-gray-600">mnemo</span>
      </div>
      <div className="p-5 font-mono text-xs leading-relaxed overflow-x-auto">
        {lines.map((line, i) => (
          <div key={i} className={line.startsWith('$') ? 'text-accent font-medium' : line.startsWith('#') || line.startsWith('[') ? 'text-gray-400' : 'text-gray-500'}>
            {line || '\u00A0'}
          </div>
        ))}
      </div>
    </div>
  );
}
