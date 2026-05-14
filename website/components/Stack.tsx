export default function Stack() {
  return (
    <section id="stack" className="py-24 px-6 border-t border-border-subtle">
      <div className="max-w-5xl mx-auto">
        <div className="accent-line mb-6" />
        <h2 className="heading text-2xl md:text-3xl mb-4">Three pillars of engineering cognition</h2>
        <p className="text-text-secondary text-sm mb-14 max-w-lg">Each gives your AI agent a deeper, persistent understanding that survives across sessions.</p>

        <div className="grid md:grid-cols-3 gap-px bg-border-subtle">
          <div className="bg-surface p-8">
            <span className="font-mono text-xs text-accent tracking-wider">01</span>
            <h3 className="heading text-lg mt-3 mb-3">Knowledge Graph</h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              NetworkX graph with 880+ nodes. Services, classes, interfaces, methods, and people connected by structural relationships. Tree-sitter parses 14 languages into AST. Query neighbors, paths, hubs, and impact.
            </p>
          </div>
          <div className="bg-surface p-8">
            <span className="font-mono text-xs text-accent tracking-wider">02</span>
            <h3 className="heading text-lg mt-3 mb-3">Memory Lifecycle</h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              Tiered retention with decay scoring. Memories auto-categorize, detect contradictions, and enrich every response with proactive context. Branch-aware isolation prevents context bleed.
            </p>
          </div>
          <div className="bg-surface p-8">
            <span className="font-mono text-xs text-accent tracking-wider">03</span>
            <h3 className="heading text-lg mt-3 mb-3">Hybrid Search</h3>
            <p className="text-sm text-text-secondary leading-relaxed">
              BM25 keyword + ChromaDB vector + graph traversal, fused via Reciprocal Rank Fusion. Finds code by meaning, not filename. Falls back gracefully without ChromaDB.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
