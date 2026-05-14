'use client';

import { useState } from 'react';

const METHODS = [
  {
    label: 'Homebrew',
    steps: ['brew tap Mnemo-mcp/tap', 'brew install mnemo', 'cd your-project && mnemo init'],
  },
  {
    label: 'pip',
    steps: ['pip install mnemo', 'cd your-project && mnemo init'],
  },
  {
    label: 'Binary',
    steps: ['curl -fsSL https://raw.githubusercontent.com/Mnemo-mcp/Mnemo/main/scripts/install.sh | sh', 'cd your-project && mnemo init'],
  },
  {
    label: 'VS Code',
    steps: ['# Install "Mnemo" from VS Code Marketplace', '# Open project → click "Initialize Mnemo"', '# Done. Extension handles everything.'],
  },
];

const CONFIGS = [
  { name: 'Amazon Q', config: '# ~/.aws/amazonq/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo",\n      "args": ["mcp"]\n    }\n  }\n}' },
  { name: 'Cursor', config: '# Settings → MCP → Add Server\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo",\n      "args": ["mcp"]\n    }\n  }\n}' },
  { name: 'Claude Code', config: '# .claude/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo",\n      "args": ["mcp"]\n    }\n  }\n}' },
  { name: 'Kiro', config: '# ~/.kiro/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo",\n      "args": ["mcp"]\n    }\n  }\n}\n\n# With hooks:\n# mnemo init --hooks --client kiro' },
  { name: 'Copilot', config: '# .github/copilot/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo",\n      "args": ["mcp"]\n    }\n  }\n}' },
  { name: 'Gemini CLI', config: '# ~/.gemini/mcp.json\n{\n  "mcpServers": {\n    "mnemo": {\n      "command": "mnemo",\n      "args": ["mcp"]\n    }\n  }\n}' },
];

export default function Install() {
  const [method, setMethod] = useState(0);
  const [agent, setAgent] = useState(0);

  return (
    <section id="install" className="py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-16">
          <span className="text-xs font-semibold tracking-widest text-accent-pink uppercase">Get started</span>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mt-3 mb-5">
            Two steps. Done.
          </h2>
          <p className="text-gray-400 text-base max-w-2xl">
            Runs locally. Data stays on your machine. No API keys for core features. ChromaDB optional for vector search.
          </p>
        </div>

        {/* Install */}
        <div className="mb-14">
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider mb-5">Step 1 — Install</h3>
          <div className="flex gap-2 mb-4 flex-wrap">
            {METHODS.map((m, i) => (
              <button
                key={m.label}
                onClick={() => setMethod(i)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${i === method ? 'bg-accent-pink/10 text-accent-pink border border-accent-pink/30' : 'text-gray-500 hover:text-gray-300 border border-transparent'}`}
              >
                {m.label}
              </button>
            ))}
          </div>
          <div className="card p-5 font-mono text-sm">
            {METHODS[method].steps.map((step, i) => (
              <div key={i} className={step.startsWith('#') ? 'text-gray-600' : 'text-accent-pink'}>
                {!step.startsWith('#') && <span className="text-gray-600">$ </span>}
                {step}
              </div>
            ))}
          </div>
        </div>

        {/* Config */}
        <div>
          <h3 className="text-xs font-semibold text-white uppercase tracking-wider mb-5">Step 2 — Connect your agent</h3>
          <div className="grid md:grid-cols-[180px_1fr] gap-3">
            <div className="flex md:flex-col gap-1">
              {CONFIGS.map((a, i) => (
                <button
                  key={a.name}
                  onClick={() => setAgent(i)}
                  className={`px-3 py-2 text-xs text-left rounded-md transition-all ${i === agent ? 'bg-surface-raised text-white border border-white/10' : 'text-gray-500 hover:text-gray-300'}`}
                >
                  {a.name}
                </button>
              ))}
            </div>
            <div className="card p-5 font-mono text-xs overflow-x-auto">
              <pre className="text-gray-400 whitespace-pre">{CONFIGS[agent].config}</pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
