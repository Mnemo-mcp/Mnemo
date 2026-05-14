const FEATURES = [
  { num: '880+', unit: 'nodes', title: 'Structural Knowledge Graph', desc: 'Services, classes, interfaces, methods, files, and people. Relationships: implements, inherits, calls, depends_on. 14 languages via tree-sitter.' },
  { num: '56', unit: 'tools', title: 'Complete MCP Toolset', desc: 'Every tool enriches its response with proactive context — warnings, next tasks, related decisions without extra calls.' },
  { num: '3×', unit: 'streams', title: 'Hybrid Retrieval', desc: 'BM25 with stemming, vector similarity via MiniLM-L6-v2, graph traversal boost. Fused with Reciprocal Rank Fusion.' },
  { num: 'Auto', unit: 'decay', title: 'Self-Maintaining Memory', desc: 'Retention scoring with access reinforcement. Hot memories stay, stale ones fade. Contradiction detection supersedes conflicts.' },
  { num: '16', unit: 'rules', title: 'Secret Filtering', desc: 'AWS keys, GitHub PATs, JWTs, Bearer tokens, private keys — all stripped before storage. .mnemo/ never contains credentials.' },
  { num: 'DAG', unit: 'tasks', title: 'Plan Mode', desc: 'Auto-creates plans from natural language. Dependencies, frontier scoring, auto-completion. Syncs to .mnemo/TASKS.md.' },
  { num: '5', unit: 'hooks', title: 'Lifecycle Capture', desc: 'Kiro and Claude Code hooks observe agent activity passively. agentSpawn, postToolUse, stop. Memory builds itself.' },
  { num: '11', unit: 'agents', title: 'Universal MCP Support', desc: 'Amazon Q, Cursor, Claude Code, Kiro, Copilot, Gemini CLI, Windsurf, Cline, Roo Code, OpenCode, Goose.' },
  { num: '0', unit: 'deps', title: 'Single Process, Local JSON', desc: 'No Redis. No Postgres. No Docker. Everything in .mnemo/ as JSON. Starts in under 1 second. Works offline.' },
];

export default function Features() {
  return (
    <section id="features" className="py-28 px-6 border-t border-border-subtle">
      <div className="max-w-6xl mx-auto">
        <p className="text-accent font-mono text-sm mb-4">Capabilities</p>
        <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">Everything an agent needs.</h2>
        <p className="text-gray-400 text-base max-w-lg mb-14">Not a vector store. Not a markdown file. A full cognition runtime — parse, graph, remember, search, plan, enrich.</p>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-px bg-border-subtle rounded-lg overflow-hidden">
          {FEATURES.map((f, i) => (
            <div key={i} className="bg-surface p-6 hover:bg-surface-raised transition-colors">
              <div className="flex items-baseline gap-1.5 mb-3">
                <span className="text-lg font-bold text-accent">{f.num}</span>
                <span className="text-[10px] text-gray-500 uppercase tracking-wider font-mono">{f.unit}</span>
              </div>
              <h3 className="text-sm font-semibold text-white mb-2">{f.title}</h3>
              <p className="text-xs text-gray-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
