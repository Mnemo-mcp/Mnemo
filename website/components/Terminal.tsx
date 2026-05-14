'use client';

import { useState, useEffect } from 'react';

export default function Terminal({ lines }: { lines: string[] }) {
  const [visibleLines, setVisibleLines] = useState<string[]>([]);

  useEffect(() => {
    setVisibleLines([]);
    let i = 0;
    const timer = setInterval(() => {
      if (i < lines.length) {
        setVisibleLines(prev => [...prev, lines[i - 1] ?? lines[0]]);
        i++;
      } else {
        clearInterval(timer);
      }
    }, 500);
    // Show first line immediately
    setVisibleLines([lines[0]]);
    i = 1;
    return () => clearInterval(timer);
  }, [lines]);

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06]">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/70" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/70" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-500/70" />
        <span className="ml-2 text-[10px] text-gray-600">mnemo</span>
      </div>
      <div className="p-4 font-mono text-xs space-y-0.5">
        {visibleLines.map((line, idx) => (
          <div key={idx} className={line?.startsWith('$') ? 'text-accent-pink' : 'text-gray-500'}>
            {line || ''}
          </div>
        ))}
        <span className="inline-block w-1.5 h-3.5 bg-accent-pink animate-pulse" />
      </div>
    </div>
  );
}
