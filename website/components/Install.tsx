'use client';

import { useState } from 'react';

const METHODS = [
  { label: 'Homebrew', steps: ['brew tap Mnemo-mcp/tap', 'brew install mnemo', 'cd your-project && mnemo init'] },
  { label: 'pip', steps: ['pip install mnemo-dev', 'cd your-project && mnemo init'] },
  { label: 'npx', steps: ['npx @mnemo-dev/mcp'] },
  { label: 'Binary', steps: ['curl -fsSL https://raw.githubusercontent.com/Mnemo-mcp/Mnemo/main/scripts/install.sh | sh', 'cd your-project && mnemo init'] },
];

const AGENTS = ['Amazon Q', 'Cursor', 'Claude Code', 'Kiro', 'Copilot', 'Gemini CLI', 'Windsurf', 'Cline', 'Roo Code', 'OpenCode', 'Goose'];

export default function Install() {
  const [method, setMethod] = useState(0);

  return (
    <section id="install" className="py-28 px-6 border-t border-border-subtle">
      <div className="max-w-5xl mx-auto">
        <div className="accent-line mb-6" />
        <h2 className="heading text-3xl md:text-4xl mb-4">Two commands. Done.</h2>
        <p className="text-text-secondary text-base max-w-lg mb-14">
          Runs locally. Data stays on your machine. No API keys for core features.
        </p>

        <div className="grid md:grid-cols-[1fr_1fr] gap-12">
          <div>
            <h3 className="font-mono text-xs text-accent uppercase tracking-[0.2em] mb-5">Install</h3>
            <div className="flex gap-2 mb-5 flex-wrap">
              {METHODS.map((m, i) => (
                <button
                  key={m.label}
                  onClick={() => setMethod(i)}
                  className={`px-3 py-1.5 text-xs font-mono rounded-sm transition-all ${i === method ? 'bg-accent/10 text-accent border border-accent/30' : 'text-text-muted hover:text-text-secondary border border-transparent'}`}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <div className="card p-5 font-mono text-sm space-y-1">
              {METHODS[method].steps.map((step, i) => (
                <div key={i} className="text-accent">
                  <span className="text-text-muted">$ </span>{step}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="font-mono text-xs text-accent uppercase tracking-[0.2em] mb-5">Supported Agents</h3>
            <div className="flex flex-wrap gap-2">
              {AGENTS.map((a) => (
                <span key={a} className="px-3 py-2 text-xs text-text-secondary border border-border-subtle rounded-sm">
                  {a}
                </span>
              ))}
            </div>
            <p className="text-xs text-text-muted mt-6">
              Any MCP-compatible client works. First-party hooks for Kiro and Claude Code.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
