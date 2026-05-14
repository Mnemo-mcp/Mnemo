import Nav from '@/components/Nav';
import Hero from '@/components/Hero';
import Stack from '@/components/Stack';
import Features from '@/components/Features';
import Terminal from '@/components/Terminal';
import Phases from '@/components/Phases';
import Agents from '@/components/Agents';
import Install from '@/components/Install';
import Compare from '@/components/Compare';
import Architecture from '@/components/Architecture';
import Footer from '@/components/Footer';
import ScrollProgress from '@/components/ScrollProgress';

export default function Home() {
  return (
    <>
      <ScrollProgress />
      <Nav />
      <main>
        <Hero />
        <Stack />
        <Features />
        <section className="py-16 px-6">
          <div className="max-w-2xl mx-auto">
            <Terminal lines={[
              '$ mnemo search "authentication flow"',
              'Hybrid search: BM25 + vector + graph boost',
              'Found 5 results (fused via RRF, k=60)',
              '',
              '  1. AuthService.ValidateToken (0.94)',
              '  2. JwtMiddleware.cs (0.87)',
              '  3. Decision: "Use JWT with 1h expiry" (0.82)',
              '',
              '$ mnemo graph neighbors AuthService',
              '  → implements: IAuthService',
              '  → calls: TokenValidator, UserRepository',
              '  → depends_on: Microsoft.Identity',
            ]} />
          </div>
        </section>
        <Phases />
        <Agents />
        <Install />
        <Compare />
        <Architecture />
      </main>
      <Footer />
    </>
  );
}
