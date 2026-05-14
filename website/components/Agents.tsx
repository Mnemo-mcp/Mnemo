const FIRST_PARTY = [
  { name: 'Amazon Q', detail: 'Default target. Auto-configured on init.', tag: 'DEFAULT' },
  { name: 'Kiro', detail: 'Full hooks + skills + MCP integration', tag: 'HOOKS' },
  { name: 'Claude Code', detail: 'Lifecycle hooks + MCP + memory guide', tag: 'HOOKS' },
  { name: 'Cursor', detail: 'Native MCP support, single config', tag: 'MCP' },
];

const COMMUNITY = [
  'GitHub Copilot',
  'Gemini CLI',
  'Windsurf',
  'Cline',
  'Roo Code',
  'OpenCode',
  'Goose',
];

export default function Agents() {
  return (
    <section className="py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-16">
          <span className="text-xs font-semibold tracking-widest text-accent-pink uppercase">Compatibility</span>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mt-3 mb-5">
            11 agents supported.<br />One protocol.
          </h2>
          <p className="text-gray-400 text-base max-w-2xl">
            First-party hooks for Kiro and Claude Code. Every other MCP-compatible client works out of the box with a single JSON config.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-3 mb-8">
          {FIRST_PARTY.map(a => (
            <div key={a.name} className="card p-5 hover:border-accent-pink/20 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-semibold text-white text-sm">{a.name}</h3>
                <span className="text-[10px] font-semibold tracking-wider px-2 py-0.5 rounded-full bg-accent-pink/10 text-accent-pink border border-accent-pink/20">{a.tag}</span>
              </div>
              <p className="text-xs text-gray-500">{a.detail}</p>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {COMMUNITY.map(name => (
            <div key={name} className="px-3 py-2 bg-surface-raised border border-white/[0.04] rounded-lg text-xs text-gray-400 hover:text-white hover:border-white/10 transition-all">
              {name}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
