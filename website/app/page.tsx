"use client";
import Splash from "@/components/Splash";
import Navbar from "@/components/Navbar";
import Hero from "@/components/Hero";
import Problem from "@/components/Problem";
import Solution from "@/components/Solution";
import Lifecycle from "@/components/Lifecycle";
import Agents from "@/components/Agents";
import Install from "@/components/Install";
import Features from "@/components/Features";
import Architecture from "@/components/Architecture";
import FinalCTA from "@/components/FinalCTA";
import Footer from "@/components/Footer";
import { ScrollProgress, BackToTop } from "@/components/ScrollUtils";

export default function Home() {
  return (
    <>
      <Splash />
      <ScrollProgress />
      <Navbar />
      <main id="main-content">
        <Hero />
        <Problem />
        <Solution />
        <Lifecycle />
        <Agents />
        <Install />
        <Features />
        <Architecture />
        <FinalCTA />
      </main>
      <Footer />
      <BackToTop />
    </>
  );
}
