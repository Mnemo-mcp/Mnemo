const FEATURES = [
  {
    stat: '880+',
    unit: 'nodes',
    title: 'Structural Knowledge Graph',
    text: 'NetworkX graph mapping services, classes, interfaces, methods, files, and people. Tree-sitter parses 14 languages into AST. Relationships like implements, inherits, calls, depends_on give agents real architectural awareness.',
    color: '#db2777',
  },
  {
    stat: '56',
    unit: 'tools',
    title: 'Complete MCP Toolset',
    text: 'recall, remember, search, graph, plan, intelligence, health, security — every tool enriches its response with proactive context. The agent gets warnings, next tasks, and related decisions without extra calls.',
    color: '#2563eb',
  },
  {
    stat: '3×',
    unit: 'streams',
    title: 'Hybrid Retrieval Engine',
    text: 'BM25 keyword search with Porter stemming, vector similarity via ChromaDB + MiniLM-L6-v2, and graph traversal boost. Fused with Reciprocal Rank Fusion. Falls back gracefully without ChromaDB.',
    color: '#7c3aed',
  },
  {
    stat: 'Auto',
    unit: 'decay',
    title: 'Self-Maintaining Memory',
    text: 'Retention scoring with Ebbinghaus decay and access reinforcement. Frequently-used memories stay hot. Stale ones fade. Contradiction detection supersedes conflicting facts. Branch-aware isolation prevents context bleed.',
    color: '#16a34a',
  },
  {
    stat: '14',
    unit: 'langs',
    title: 'Deep Code Parsing',
    text: 'Python, TypeScript, Go, C#, Java, Rust, Ruby, PHP, C/C++, Kotlin, Swift, Scala. Full AST extraction via tree-sitter. Roslyn for enhanced C# analysis. Method-level detail on demand.',
    color: '#d97706',
  },
  {
    stat: '16',
    unit: 'rules',
    title: 'Automatic Secret Filtering',
    text: 'AWS keys, GitHub PATs, JWTs, Bearer tokens, Slack tokens, npm tokens, private XML tags — all stripped before storage. Every write passes through the filter. Your .mnemo/ never contains credentials.',
    color: '#dc2626',
  },
  {
    stat: 'DAG',
    unit: 'tasks',
    title: 'Plan Mode with Dependencies',
    text: 'Auto-creates plans from natural language. Tasks have priority, dependencies, and frontier scoring. Draft plans expire if not promoted. Auto-marks tasks done when matching work is reported. Syncs to TASKS.md.',
    color: '#2563eb',
  },
  {
    stat: '5',
    unit: 'hooks',
    title: 'Lifecycle Capture',
    text: 'Kiro and Claude Code hooks observe agent activity passively. agentSpawn injects recall, postToolUse captures modifications, stop records sessions. Memory builds itself without explicit calls.',
    color: '#db2777',
  },
  {
    stat: 'SHA',
    unit: 'dedup',
    title: 'Signal Over Noise',
    text: 'Tool-call dedup with SHA-256 hashing and 5-minute TTL. Content dedup via sparse embedding similarity. Observation capture for pattern mining. Lessons system with spaced-repetition decay.',
    color: '#7c3aed',
  },
  {
    stat: '0',
    unit: 'deps',
    title: 'Single Process, Local JSON',
    text: 'No Redis. No Postgres. No Docker. Everything lives in .mnemo/ as JSON files. ChromaDB is optional. Starts in under 1 second. Works offline. Works on planes.',
    color: '#16a34a',
  },
  {
    stat: 'Git',
    unit: 'travel',
    title: 'State Snapshots',
    text: 'Full .mnemo/ state committed to a local git repo on each snapshot. List history, restore any point. Auto-snapshot before destructive operations. Obsidian export with YAML frontmatter.',
    color: '#d97706',
  },
  {
    stat: 'UI',
    unit: 'live',
    title: 'Visual Dashboard',
    text: 'Web dashboard on port 7890. Interactive knowledge graph visualization. Activity heatmap. Memory browser with filters. Tool metrics. Lessons with confidence bars. Command palette.',
    color: '#dc2626',
  },
];

export default function Features() {
  return (
    <section id="features" className="py-28 px-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-16">
          <span className="text-xs font-semibold tracking-widest text-accent-pink uppercase">Capabilities</span>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mt-3 mb-5">
            Everything an agent needs to<br />understand your codebase.
          </h2>
          <p className="text-gray-400 text-base max-w-2xl">
            Mnemo isn&apos;t a vector store or a markdown file. It&apos;s a full cognition runtime — parse, graph, remember, search, plan, and enrich every response.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-px bg-white/[0.04] border border-white/[0.04] rounded-lg overflow-hidden">
          {FEATURES.map(f => (
            <div key={f.title} className="bg-surface p-7 hover:bg-surface-raised transition-colors">
              <div className="flex items-baseline gap-2 mb-4">
                <span className="text-lg font-bold" style={{ color: f.color }}>{f.stat}</span>
                <span className="text-[10px] tracking-widest uppercase text-gray-500">{f.unit}</span>
              </div>
              <h3 className="text-sm font-semibold text-white mb-2">{f.title}</h3>
              <p className="text-xs text-gray-500 leading-relaxed">{f.text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
