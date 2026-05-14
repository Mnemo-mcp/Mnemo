const FEATURES = [
  { num: '880+', unit: 'nodes', title: 'Structural Knowledge Graph', desc: 'Services, classes, interfaces, methods, files, and people as nodes. Relationships like implements, inherits, calls, depends_on give agents real architectural awareness across 14 languages.' },
  { num: '56', unit: 'tools', title: 'Complete MCP Toolset', desc: 'Every tool enriches its response with proactive context. The agent gets warnings, next tasks, and related decisions without extra calls.' },
  { num: '3×', unit: 'streams', title: 'Hybrid Retrieval', desc: 'BM25 with Porter stemming, vector similarity via MiniLM-L6-v2, and graph traversal boost. Fused with Reciprocal Rank Fusion.' },
  { num: 'Auto', unit: 'decay', title: 'Self-Maintaining Memory', desc: 'Retention scoring with access reinforcement. Frequently-used memories stay hot. Stale ones fade. Contradiction detection supersedes conflicting facts.' },
  { num: '14', unit: 'langs', title: 'Deep Code Parsing', desc: 'Python, TypeScript, Go, C#, Java, Rust, Ruby, PHP, C/C++, Kotlin, Swift, Scala. Full AST extraction via tree-sitter. Roslyn for enhanced C#.' },
  { num: '16', unit: 'rules', title: 'Secret Filtering', desc: 'AWS keys, GitHub PATs, JWTs, Bearer tokens, private keys — all stripped before storage. Your .mnemo/ never contains credentials.' },
  { num: 'DAG', unit: 'tasks', title: 'Plan Mode', desc: 'Auto-creates plans from natural language. Tasks have dependencies and frontier scoring. Auto-marks done when matching work is reported.' },
  { num: '5', unit: 'hooks', title: 'Lifecycle Capture', desc: 'Kiro and Claude Code hooks observe agent activity passively. Memory builds itself without explicit calls.' },
  { num: '0', unit: 'deps', title: 'Single Process, Local JSON', desc: 'No Redis. No Postgres. No Docker. Everything in .mnemo/ as JSON. Starts in under 1 second. Works offline.' },
];

export default function Features() {
  return (
    <section id="features" className="py-28 px-6 border-t border-border-subtle">
      <div className="max-w-5xl mx-auto">
        <div className="accent-line mb-6" />
        <h2 className="heading text-3xl md:text-4xl mb-4">Everything an agent needs to understand your codebase.</h2>
        <p className="text-text-secondary text-base max-w-lg mb-16">
          Not a vector store. Not a markdown file. A full cognition runtime.
        </p>

        <div className="space-y-px bg-border-subtle">
          {FEATURES.map((f, i) => (
            <div key={i} className="bg-surface p-6 md:p-8 grid md:grid-cols-[120px_1fr] gap-6 items-start">
              <div>
                <span className="font-display text-2xl font-bold text-accent">{f.num}</span>
                <span className="text-xs text-text-muted ml-1 uppercase tracking-wider font-mono">{f.unit}</span>
              </div>
              <div>
                <h3 className="font-body font-semibold text-sm text-text-primary mb-2">{f.title}</h3>
                <p className="text-sm text-text-secondary leading-relaxed max-w-xl">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
