"use client";
import { motion, useInView } from "framer-motion";
import { useRef, useState } from "react";
import { useReducedMotion } from "./useReducedMotion";

const tabs = [
  { id: "pip", label: "pip", cmd: "pip install mnemo-dev" },
  { id: "brew", label: "brew", cmd: "brew tap Mnemo-mcp/tap && brew install mnemo" },
  { id: "npx", label: "npx", cmd: "npx @mnemo-dev/mcp" },
  { id: "vscode", label: "VS Code", cmd: "code --install-extension Nikhil1057.mnemo-vscode" },
];

const quickstart = [
  { step: "Install", desc: "Choose your preferred package manager above." },
  { step: "Init", desc: "Run mnemo init in your project root." },
  { step: "Code", desc: "Start coding — Mnemo handles the rest." },
];

export default function Install() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-100px" });
  const [activeTab, setActiveTab] = useState("pip");
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");
  const [copyScale, setCopyScale] = useState(false);
  const reduced = useReducedMotion();

  const activeCmd = tabs.find((t) => t.id === activeTab)!.cmd;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(activeCmd);
      setCopyState("copied");
    } catch {
      try {
        const ta = document.createElement("textarea");
        ta.value = activeCmd;
        ta.style.position = "fixed";
        ta.style.opacity = "0";
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
        setCopyState("copied");
      } catch {
        setCopyState("failed");
      }
    }
    setCopyScale(true);
    setTimeout(() => setCopyScale(false), 150);
    setTimeout(() => setCopyState("idle"), 2000);
  };

  return (
    <section id="install" className="relative py-32" aria-labelledby="install-heading" ref={ref}>
      <div className="absolute left-0 top-0 w-full h-[1px] bg-gradient-to-r from-transparent via-accent/15 to-transparent" aria-hidden="true" />

      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          className="mb-12"
          initial={reduced ? undefined : { opacity: 0, y: 30 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.7 }}
        >
          <h2 id="install-heading" className="font-display font-black text-4xl sm:text-5xl lg:text-[4.5rem] tracking-tight italic leading-[0.9]">
            Get started in seconds
          </h2>
          <p className="mt-4 text-zinc-400 text-lg">One command. Zero configuration.</p>
        </motion.div>

        <motion.div
          className="bg-dim border border-zinc-800/80 overflow-hidden"
          initial={reduced ? undefined : { opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.2, duration: 0.6 }}
        >
          <div className="flex border-b border-zinc-800/80" role="tablist" aria-label="Installation methods">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                id={`tab-${tab.id}`}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`panel-${tab.id}`}
                className={`px-6 py-3 font-mono text-xs uppercase tracking-wider transition-colors relative ${
                  activeTab === tab.id ? "text-accent bg-accent/5" : "text-zinc-500 hover:text-zinc-300"
                }`}
                onClick={() => { setActiveTab(tab.id); setCopyState("idle"); }}
              >
                {tab.label}
                {activeTab === tab.id && (
                  <motion.div className="absolute bottom-0 left-0 right-0 h-[2px] bg-accent" layoutId="tab-indicator" />
                )}
              </button>
            ))}
          </div>

          {tabs.map((tab) => (
            <div key={tab.id} id={`panel-${tab.id}`} role="tabpanel" aria-labelledby={`tab-${tab.id}`} hidden={activeTab !== tab.id}>
              <div className="flex items-center justify-between p-6">
                <code className="font-mono text-base sm:text-lg text-accent-light">
                  <span className="text-zinc-600">$ </span>{tab.cmd}
                </code>
                <div aria-live="polite" aria-atomic="true">
                  <button
                    onClick={handleCopy}
                    className={`px-4 py-2 font-mono text-xs uppercase tracking-wider border transition-all duration-200 ${
                      copyState === "copied"
                        ? "bg-cyan/10 text-cyan border-cyan/30 shadow-[0_0_15px_rgba(34,211,238,0.2)]"
                        : "bg-accent/10 text-accent border-accent/20 hover:bg-accent/20 hover:shadow-[0_0_15px_rgba(245,158,11,0.15)]"
                    }`}
                    style={{ transform: copyScale ? "scale(1.1)" : "scale(1)" }}
                    aria-label={copyState === "copied" ? `Copied ${tab.label} install command` : `Copy ${tab.label} install command`}
                  >
                    {copyState === "copied" ? "✓ Copied" : copyState === "failed" ? "✕ Failed" : "Copy"}
                  </button>
                </div>
              </div>
            </div>
          ))}
        </motion.div>

        {/* Quickstart steps */}
        <motion.div
          className="mt-12 grid sm:grid-cols-3 gap-6"
          initial={reduced ? undefined : { opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ delay: 0.4, duration: 0.6 }}
        >
          {quickstart.map((item, i) => (
            <div key={i} className="text-center group">
              <div className="w-10 h-10 bg-dim border border-accent/20 flex items-center justify-center mx-auto mb-3 transition-all duration-300 group-hover:border-accent/50 group-hover:shadow-[0_0_12px_rgba(245,158,11,0.15)]">
                <span className="font-mono font-bold text-accent text-sm">{i + 1}</span>
              </div>
              <h3 className="font-display font-semibold text-white mb-1">{item.step}</h3>
              <p className="text-sm text-zinc-400">{item.desc}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}
