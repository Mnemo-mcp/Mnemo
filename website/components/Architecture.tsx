const layers = [
  { name: 'MCP Tools', detail: '56 tools · JSON-RPC stdin/stdout', color: 'bg-accent', width: 'w-full' },
  { name: 'Response Enrichment', detail: 'plan hints · warnings · decisions', color: 'bg-accent-dim', width: 'w-[92%]' },
  { name: 'Knowledge Graph', detail: 'NetworkX · 880+ nodes · 1455+ edges', color: 'bg-accent', width: 'w-[84%]' },
  { name: 'Plan Mode', detail: 'DAG tasks · auto-complete · TASKS.md', color: 'bg-purple-500', width: 'w-[76%]' },
  { name: 'Hybrid Search', detail: 'BM25 + ChromaDB + Graph · RRF fusion', color: 'bg-accent-dim', width: 'w-[68%]' },
  { name: 'Code Parsing', detail: 'tree-sitter · 14 langs · Roslyn', color: 'bg-accent', width: 'w-[60%]' },
  { name: 'Storage', detail: '.mnemo/*.json · fully local · git snapshots', color: 'bg-accent', width: 'w-[52%]' },
];

export default function Architecture() {
  return (
    <section className="py-24 px-6">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-3">
          <span className="text-accent">Architecture</span>
        </h2>
        <p className="text-gray-400 text-sm text-center mb-14 max-w-xl mx-auto">
          Seven independent layers. Each one testable in isolation. Data flows down, context flows up.
        </p>

        <div className="flex flex-col items-center gap-1.5">
          {layers.map((layer, i) => (
            <div key={i} className={`${layer.width} transition-all`}>
              <div className="relative group">
                <div className={`absolute inset-0 ${layer.color} opacity-[0.07] rounded-lg`} />
                <div className="relative flex items-center justify-between px-5 py-3.5 border border-border-subtle rounded-lg hover:border-white/[0.12] transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${layer.color}`} />
                    <span className="text-sm font-semibold text-white">{layer.name}</span>
                  </div>
                  <span className="text-[11px] text-gray-400 hidden sm:block">{layer.detail}</span>
                </div>
              </div>
              {i < layers.length - 1 && (
                <div className="flex justify-center py-0.5">
                  <div className="w-px h-2 bg-white/[0.08]" />
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="mt-12 grid grid-cols-3 gap-3 text-center">
          <div className="card p-4">
            <div className="text-lg font-bold text-accent">↑</div>
            <div className="text-[10px] text-gray-400 mt-1 uppercase tracking-wider">Context flows up</div>
          </div>
          <div className="card p-4">
            <div className="text-lg font-bold text-accent">↓</div>
            <div className="text-[10px] text-gray-400 mt-1 uppercase tracking-wider">Data flows down</div>
          </div>
          <div className="card p-4">
            <div className="text-lg font-bold text-accent">0</div>
            <div className="text-[10px] text-gray-400 mt-1 uppercase tracking-wider">External deps</div>
          </div>
        </div>
      </div>
    </section>
  );
}
