'use client';

import { useEffect, useState, useRef } from 'react';

interface TerminalProps {
  lines: string[];
}

export default function Terminal({ lines }: TerminalProps) {
  const [visibleLines, setVisibleLines] = useState(0);
  const [typing, setTyping] = useState(true);
  const ref = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          let i = 0;
          const interval = setInterval(() => {
            i++;
            setVisibleLines(i);
            if (i >= lines.length) {
              clearInterval(interval);
              setTyping(false);
            }
          }, 120);
        }
      },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [lines.length]);

  return (
    <div ref={ref} className="card overflow-hidden">
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border-subtle">
        <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
        <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
        <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
        <span className="ml-2 font-mono text-[10px] text-gray-600">mnemo</span>
      </div>
      <div className="p-5 font-mono text-xs leading-relaxed overflow-x-auto min-h-[200px]">
        {lines.slice(0, visibleLines).map((line, i) => (
          <div key={i} className={`transition-opacity duration-200 ${line.startsWith('$') ? 'text-accent font-medium' : line.startsWith('#') || line.startsWith('[') ? 'text-gray-400' : 'text-gray-500'}`}>
            {line || '\u00A0'}
          </div>
        ))}
        {typing && (
          <span className="inline-block w-2 h-4 bg-accent animate-pulse" />
        )}
      </div>
    </div>
  );
}
