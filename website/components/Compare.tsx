const ROWS: [string, string, string, string, string][] = [
  ['Code Intelligence (14-lang AST)', '✓', '—', '—', '—'],
  ['Knowledge Graph (structural)', '✓', '✓', '—', '—'],
  ['Plan Mode (auto-create + DAG)', '✓', '—', '—', '—'],
  ['Multi-Repo Workspace', '✓', '—', '—', '—'],
  ['Privacy Filtering (16 patterns)', '✓', '—', '✓', '—'],
  ['Memory Lifecycle (decay + evict)', '✓', '✓', '—', '—'],
  ['Hybrid Search (BM25+Vec+Graph)', '✓', '✓', '—', '—'],
  ['Offline / Local-First', '✓', '✓', '—', '✓'],
  ['Zero External Databases', '✓', '✓', '—', '✓'],
  ['Lifecycle Hooks (passive capture)', '✓', '✓', '—', '—'],
  ['Task Dependencies (DAG)', '✓', '✓', '—', '—'],
  ['Response Enrichment (proactive)', '✓', '—', '—', '—'],
  ['REST API + Dashboard UI', '✓', '✓', '✓', '—'],
  ['128+ Tests', '✓', '✓', '—', '—'],
];

export default function Compare() {
  return (
    <section id="compare" className="py-28 px-6">
      <div className="max-w-5xl mx-auto">
        <div className="mb-16">
          <span className="text-xs font-semibold tracking-widest text-accent-pink uppercase">How it stacks up</span>
          <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mt-3 mb-5">
            Feature comparison.
          </h2>
          <p className="text-gray-400 text-base max-w-2xl">
            Mnemo focuses on code understanding — not just memory storage. AST parsing, knowledge graphs, and proactive enrichment set it apart.
          </p>
        </div>

        <div className="overflow-x-auto border border-white/[0.06] rounded-lg">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/[0.08]">
                <th className="text-left py-4 px-5 text-gray-500 font-medium text-xs uppercase tracking-wider">Capability</th>
                <th className="py-4 px-5 text-center font-bold text-accent-pink bg-accent-pink/5 text-xs uppercase tracking-wider">Mnemo</th>
                <th className="py-4 px-5 text-center text-gray-500 font-medium text-xs uppercase tracking-wider">AgentMemory</th>
                <th className="py-4 px-5 text-center text-gray-500 font-medium text-xs uppercase tracking-wider">Mem0</th>
                <th className="py-4 px-5 text-center text-gray-500 font-medium text-xs uppercase tracking-wider">MEMORY.md</th>
              </tr>
            </thead>
            <tbody>
              {ROWS.map(([feature, mnemo, am, mem0, md], i) => (
                <tr key={i} className="border-b border-white/[0.04] hover:bg-white/[0.01] transition-colors">
                  <td className="py-3 px-5 text-gray-300">{feature}</td>
                  <td className="py-3 px-5 text-center bg-accent-pink/[0.02]">
                    <span className={mnemo === '✓' ? 'text-accent-green' : 'text-gray-700'}>{mnemo}</span>
                  </td>
                  <td className="py-3 px-5 text-center">
                    <span className={am === '✓' ? 'text-accent-green' : 'text-gray-700'}>{am}</span>
                  </td>
                  <td className="py-3 px-5 text-center">
                    <span className={mem0 === '✓' ? 'text-accent-green' : 'text-gray-700'}>{mem0}</span>
                  </td>
                  <td className="py-3 px-5 text-center">
                    <span className={md === '✓' ? 'text-accent-green' : 'text-gray-700'}>{md}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
