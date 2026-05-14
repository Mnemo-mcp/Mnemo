import Nav from '@/components/Nav';
import Hero from '@/components/Hero';
import Stack from '@/components/Stack';
import Features from '@/components/Features';
import Terminal from '@/components/Terminal';
import Install from '@/components/Install';
import Footer from '@/components/Footer';

export default function Home() {
  return (
    <>
      <Nav />
      <main>
        <Hero />
        <Stack />
        <Features />
        <section className="py-20 px-6 border-t border-border-subtle">
          <div className="max-w-3xl mx-auto">
            <div className="accent-line mb-6" />
            <h2 className="heading text-2xl md:text-3xl mb-8">See it work</h2>
            <Terminal lines={[
              '$ mnemo init',
              '[mnemo] Parsed 157 files · 14 languages · tree-sitter AST',
              '[mnemo] Graph: 880 nodes, 1455 edges',
              '[mnemo] Architecture: Clean Architecture + CQRS',
              '[mnemo] 56 MCP tools ready.',
              '',
              '$ mnemo recall',
              '# Context',
              '  Decision: CosmosDB for persistence',
              '  Pattern: Handler-per-payer strategy',
              '  Plan: SOAP Migration [2/4] → next: update models',
              '  Warning: PaymentService has 3 regression risks',
              '',
              '$ mnemo search "auth token refresh"',
              '  1. AuthService.ValidateToken (0.94)',
              '  2. JwtMiddleware.cs (0.87)',
              '  3. Decision: "JWT with 1h expiry" (0.82)',
            ]} />
          </div>
        </section>
        <Install />
      </main>
      <Footer />
    </>
  );
}
