'use client';

import { useState, useEffect, useRef } from 'react';

function Counter({ target, suffix = '' }: { target: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          const duration = 1200;
          const steps = 30;
          const increment = target / steps;
          let current = 0;
          const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
              setCount(target);
              clearInterval(timer);
            } else {
              setCount(Math.floor(current));
            }
          }, duration / steps);
        }
      },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [target]);

  return <span ref={ref}>{count}{suffix}</span>;
}

export default function Stats() {
  const stats = [
    { value: 56, suffix: '', label: 'MCP Tools' },
    { value: 14, suffix: '', label: 'Languages Parsed' },
    { value: 128, suffix: '+', label: 'Tests Passing' },
    { value: 880, suffix: '+', label: 'Graph Nodes' },
    { value: 0, suffix: '', label: 'External DBs' },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-5 gap-6 mt-10">
      {stats.map(s => (
        <div key={s.label} className="text-center">
          <div className="text-2xl md:text-3xl font-bold text-gradient">
            <Counter target={s.value} suffix={s.suffix} />
          </div>
          <div className="text-[11px] text-gray-500 mt-1 uppercase tracking-wider">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
