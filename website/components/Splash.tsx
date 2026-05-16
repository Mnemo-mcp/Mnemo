"use client";
import { motion, AnimatePresence } from "framer-motion";
import { useState, useEffect } from "react";

export default function Splash() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined" && sessionStorage.getItem("mnemo-visited")) {
      setVisible(false);
      return;
    }
    const timer = setTimeout(() => {
      setVisible(false);
      sessionStorage.setItem("mnemo-visited", "1");
    }, 1800);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  const orbitNodes = [
    { cx: 44, cy: 13 },
    { cx: 50, cy: 43 },
    { cx: 26, cy: 48 },
    { cx: 14, cy: 25 },
    { cx: 32, cy: 8 },
  ];

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="fixed inset-0 z-[9999] bg-bg flex items-center justify-center"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.4 }}
          aria-hidden="true"
        >
          <div className="relative">
            <motion.svg
              viewBox="0 0 64 64"
              className="w-20 h-20"
              initial={{ opacity: 0, scale: 0.5 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, type: "spring", stiffness: 200 }}
            >
              <defs>
                <linearGradient id="splash-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#F59E0B" />
                  <stop offset="100%" stopColor="#22D3EE" />
                </linearGradient>
              </defs>
              <motion.circle
                cx="32" cy="32" r="8"
                fill="url(#splash-grad)"
                initial={{ r: 0 }}
                animate={{ r: 8 }}
                transition={{ delay: 0.2, duration: 0.4 }}
              />
              {orbitNodes.map((node, i) => (
                <motion.circle
                  key={i}
                  cx={node.cx} cy={node.cy} r="3"
                  fill="#F59E0B"
                  opacity={0.7}
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 0.7 }}
                  transition={{ delay: 0.3 + i * 0.08, type: "spring" }}
                />
              ))}
              {orbitNodes.map((node, i) => (
                <motion.line
                  key={`l-${i}`}
                  x1="32" y1="32" x2={node.cx} y2={node.cy}
                  stroke="#F59E0B"
                  strokeWidth="0.8"
                  opacity={0.3}
                  initial={{ pathLength: 0 }}
                  animate={{ pathLength: 1 }}
                  transition={{ delay: 0.4 + i * 0.06, duration: 0.4 }}
                />
              ))}
            </motion.svg>
            <motion.div
              className="mt-4 text-center font-display font-bold text-2xl bg-gradient-to-r from-accent to-cyan bg-clip-text text-transparent italic"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5, duration: 0.4 }}
            >
              mnemo
            </motion.div>
            <motion.p
              className="mt-2 text-center font-mono text-[10px] text-zinc-500 tracking-widest uppercase"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8, duration: 0.4 }}
            >
              persistent cognition
            </motion.p>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
