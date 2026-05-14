export default function Stack() {
  const cards = [
    {
      title: 'Knowledge Graph',
      description: 'NetworkX graph with 880+ nodes and 1455+ edges. Services, classes, interfaces, methods, packages, and people connected by structural relationships across 14 languages.',
      color: 'border-accent-pink',
      text: 'text-accent-pink',
    },
    {
      title: 'Memory Lifecycle',
      description: 'Tiered retention with Ebbinghaus decay. Memories auto-categorize, auto-create plans, detect contradictions, and enrich every response with proactive context.',
      color: 'border-accent-blue',
      text: 'text-accent-blue',
    },
    {
      title: 'Hybrid Search',
      description: 'BM25 + ChromaDB vector + graph traversal, fused via Reciprocal Rank Fusion. Finds code by meaning, not just filename. Zero external databases.',
      color: 'border-accent-green',
      text: 'text-accent-green',
    },
  ];

  return (
    <section id="stack" className="py-24 px-6">
      <div className="max-w-5xl mx-auto">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-3">
          <span className="text-gradient">Three pillars of engineering cognition</span>
        </h2>
        <p className="text-gray-500 text-sm text-center mb-12 max-w-xl mx-auto">
          Each pillar gives your AI agent a deeper, persistent understanding of your codebase that survives across sessions.
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          {cards.map(card => (
            <div key={card.title} className={`card p-6 border-t-2 ${card.color}`}>
              <h3 className={`text-sm font-semibold mb-3 ${card.text}`}>{card.title}</h3>
              <p className="text-xs text-gray-500 leading-relaxed">{card.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
