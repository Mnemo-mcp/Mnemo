'use client';

import { useState } from 'react';

const METHODS = [
  { label: 'Homebrew', steps: ['brew tap Mnemo-mcp/tap', 'brew install mnemo', 'cd your-project && mnemo init'] },
  { label: 'pip', steps: ['pip install mnemo-dev', 'cd your-project && mnemo init'] },
  { label: 'npx', steps: ['npx @mnemo-dev/mcp'] },
  { label: 'Binary', steps: ['curl -fsSL https://raw.githubusercontent.com/Mnemo-mcp/Mnemo/main/scripts/install.sh | sh', 'cd your-project && mnemo init'] },
  { label: 'VS Code', steps: ['# Install "Mnemo" from VS Code Marketplace', '# Open project → click "Initialize Mnemo"'] },
];

const CONFIGS = [
  { name: 'Amazon Q', config: '# ~/.aws/amazonq/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo-mcp"\n    }\n  }\n}' },
  { name: 'Cursor', config: '# .cursor/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo-mcp"\n    }\n  }\n}' },
  { name: 'Kiro', config: '# Auto-configured:\n$ mnemo init --client kiro\n\n# Installs agent + hooks + MCP config' },
  { name: 'Claude Code', config: '# Auto-configured:\n$ mnemo init --client claude-code\n\n# Installs hooks + MCP config' },
];

export default function Install() {
  const [method, setMethod] = useState(0);
  const [config, setConfig] = useState(0);

  return (
    <section id="install" className="py-28 px-6 border-t border-border-subtle">
      <div className="max-w-6xl mx-auto">
        <p className="text-accent font-mono text-sm mb-4">Get started</p>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Two steps. Done.</h2>
        <p className="text-gray-400 text-base max-w-lg mb-14">Runs locally. Data stays on your machine. No API keys for core features.</p>

        <div className="grid lg:grid-cols-2 gap-12">
          <div>
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider mb-5">Step 1 — Install</h3>
            <div className="flex gap-1.5 mb-4 flex-wrap">
              {METHODS.map((m, i) => (
                <button key={m.label} onClick={() => setMethod(i)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${i === method ? 'bg-accent/10 text-accent border border-accent/30' : 'text-gray-500 hover:text-gray-300 border border-transparent'}`}>
                  {m.label}
                </button>
              ))}
            </div>
            <div className="card p-5 font-mono text-sm">
              {METHODS[method].steps.map((step, i) => (
                <div key={i} className={step.startsWith('#') ? 'text-gray-500' : 'text-accent'}>
                  {!step.startsWith('#') && <span className="text-gray-600">$ </span>}{step}
                </div>
              ))}
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-white uppercase tracking-wider mb-5">Step 2 — Connect your agent</h3>
            <div className="flex gap-1.5 mb-4 flex-wrap">
              {CONFIGS.map((c, i) => (
                <button key={c.name} onClick={() => setConfig(i)}
                  className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${i === config ? 'bg-accent/10 text-accent border border-accent/30' : 'text-gray-500 hover:text-gray-300 border border-transparent'}`}>
                  {c.name}
                </button>
              ))}
            </div>
            <div className="card p-5 font-mono text-xs">
              <pre className="text-gray-400 whitespace-pre">{CONFIGS[config].config}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
