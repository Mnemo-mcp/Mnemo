export default function Stack() {
  return (
    <section className="py-24 px-6 border-t border-border-subtle">
      <div className="max-w-6xl mx-auto">
        <p className="text-accent font-mono text-sm mb-4">Architecture</p>
        <h2 className="text-2xl md:text-3xl font-bold text-white mb-12">Three pillars of engineering cognition</h2>

        <div className="grid md:grid-cols-3 gap-4">
          <div className="card p-6">
            <div className="text-accent font-mono text-xs mb-3">01</div>
            <h3 className="font-semibold text-white mb-2">Knowledge Graph</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              LadybugDB graph with 1800+ nodes. Classes, methods, functions, communities, and memories connected by structural relationships. Tree-sitter + Roslyn parses 14 languages.
            </p>
          </div>
          <div className="card p-6">
            <div className="text-accent font-mono text-xs mb-3">02</div>
            <h3 className="font-semibold text-white mb-2">Memory Lifecycle</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              Tiered retention with decay scoring. Auto-categorize, detect contradictions, enrich every response. Branch-aware isolation prevents context bleed.
            </p>
          </div>
          <div className="card p-6">
            <div className="text-accent font-mono text-xs mb-3">03</div>
            <h3 className="font-semibold text-white mb-2">Hybrid Search</h3>
            <p className="text-sm text-gray-400 leading-relaxed">
              BM25 + ONNX dense embeddings + graph traversal, fused via Reciprocal Rank Fusion. 100% Recall@5. 2ms latency. No external database.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
