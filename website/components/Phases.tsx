const phases = [
  {
    phase: '01',
    title: 'Foundation',
    color: 'border-t-accent-pink',
    items: ['Knowledge Graph (NetworkX)', 'Persistent Memory', 'Repo Map Generation', 'Semantic Search (ChromaDB)', 'Multi-language Parsing (14 langs)'],
  },
  {
    phase: '02',
    title: 'Intelligence',
    color: 'border-t-accent-blue',
    items: ['Plan Mode (auto-create/complete)', 'Response Enrichment', 'Code Intelligence Reports', 'Convention Detection', 'Dead Code Analysis'],
  },
  {
    phase: '03',
    title: 'Scale',
    color: 'border-t-accent-green',
    items: ['Multi-Repo Workspace', 'Federated Graph Queries', 'Cross-Repo Impact Analysis', 'Workspace Linking', 'Auto-Discovery'],
  },
  {
    phase: '04',
    title: 'Safety',
    color: 'border-t-purple-500',
    items: ['Security Scanning', 'Breaking Change Detection', 'Regression Tracking', 'Architecture Drift', 'Pre-commit Hooks'],
  },
  {
    phase: '05',
    title: 'Team',
    color: 'border-t-accent-amber',
    items: ['Team Expertise Map', 'Incident Tracking', 'Code Reviews', 'Error Knowledge Base', 'Onboarding Guides'],
  },
  {
    phase: '06',
    title: 'APIs & DX',
    color: 'border-t-accent-red',
    items: ['API Discovery (OpenAPI)', 'REST API + Dashboard', 'VS Code Extension', 'Homebrew + Binary', 'CLI Diagnostics'],
  },
];

export default function Phases() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-3">
          <span className="text-gradient">Built in layers</span>
        </h2>
        <p className="text-gray-500 text-sm text-center mb-12 max-w-xl mx-auto">
          Each phase adds deeper engineering cognition. All shipped and tested.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {phases.map(p => (
            <div key={p.phase} className={`card p-5 border-t-2 ${p.color}`}>
              <div className="text-[10px] text-gray-600 mb-1 font-semibold">{p.phase}</div>
              <h3 className="font-semibold text-sm mb-3">{p.title}</h3>
              <ul className="space-y-1">
                {p.items.map(item => (
                  <li key={item} className="text-[11px] text-gray-500 flex items-start gap-2">
                    <span className="text-accent-pink mt-0.5">·</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
