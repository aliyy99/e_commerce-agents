import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sparkles, ArrowRight, Search, Bell, LineChart, Bot } from 'lucide-react';

const FEATURES = [
  {
    icon: Search,
    title: 'Vision-Powered Discovery',
    body: 'Snap a photo and our agent identifies the exact model — colour, storage, generation.',
  },
  {
    icon: LineChart,
    title: 'Live Price Intelligence',
    body: 'Compare Hepsiburada, Trendyol, MediaMarkt and Vatan in one place, in real time.',
  },
  {
    icon: Bell,
    title: 'Drop-Triggered Alerts',
    body: 'Set a target price; we ping you the moment any store crosses it.',
  },
  {
    icon: Bot,
    title: 'Honest Analyst Reports',
    body: 'Every product gets a blind-spot, chronic-issue and trust-score breakdown — not marketing copy.',
  },
];

const Landing = ({ onEnter }) => {
  const [isEntering, setIsEntering] = useState(false);

  const handleEnter = () => {
    if (isEntering) return;
    setIsEntering(true);
    // Short delay so the button can animate before the route swap.
    setTimeout(() => onEnter?.(), 280);
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-slate-950 text-white">
      {/* Aurora background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 -left-40 w-[640px] h-[640px] rounded-full bg-emerald-500/30 blur-[140px]" />
        <div className="absolute top-20 right-[-200px] w-[560px] h-[560px] rounded-full bg-primary/30 blur-[160px]" />
        <div className="absolute bottom-[-180px] left-1/3 w-[700px] h-[700px] rounded-full bg-fuchsia-500/20 blur-[180px]" />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.6) 1px, transparent 0)',
            backgroundSize: '28px 28px',
          }}
        />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Top bar */}
        <header className="flex items-center justify-between px-8 lg:px-16 py-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-primary flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <span
              style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
              className="text-2xl italic font-black tracking-tight bg-gradient-to-r from-emerald-300 via-white to-primary bg-clip-text text-transparent"
            >
              Techno Track
            </span>
          </div>
        </header>

        {/* Hero */}
        <main className="flex-1 flex flex-col lg:flex-row items-center gap-12 px-8 lg:px-16 pb-16">
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
            className="flex-1 max-w-2xl"
          >
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 border border-white/15 text-[11px] font-bold uppercase tracking-widest text-emerald-200 backdrop-blur">
              <Sparkles className="w-3.5 h-3.5" />
              AI-Powered Price Intelligence
            </span>
            <h1
              style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
              className="mt-6 text-5xl lg:text-7xl font-black leading-[1.05] tracking-tight"
            >
              Own the{' '}
              <span className="italic bg-gradient-to-r from-emerald-300 via-white to-primary bg-clip-text text-transparent">
                best technology
              </span>{' '}
              at the best price.
            </h1>
            <p className="mt-6 text-lg lg:text-xl text-slate-300 leading-relaxed max-w-xl">
              One assistant tracks every Turkish marketplace, learns the price
              history, and tells you exactly when to buy — so you never overpay
              for the gear you actually want.
            </p>

            <div className="mt-10">
              <motion.button
                onClick={handleEnter}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                disabled={isEntering}
                className="group inline-flex items-center justify-center gap-2 px-8 py-4 rounded-2xl bg-gradient-to-r from-emerald-400 to-primary text-slate-950 font-black text-base shadow-xl shadow-emerald-500/30 hover:shadow-emerald-500/50 transition-shadow disabled:opacity-70"
              >
                {isEntering ? 'Opening…' : 'Log In'}
                <ArrowRight className="w-5 h-5 transition-transform group-hover:translate-x-0.5" />
              </motion.button>
            </div>
          </motion.div>

          {/* Feature card stack */}
          <motion.div
            initial={{ opacity: 0, y: 32 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut', delay: 0.15 }}
            className="flex-1 w-full max-w-xl"
          >
            <div className="relative rounded-3xl bg-white/[0.04] border border-white/10 backdrop-blur-xl p-8 shadow-2xl shadow-black/40">
              <div className="absolute inset-x-0 -top-px h-px bg-gradient-to-r from-transparent via-white/40 to-transparent" />
              <div className="flex items-center justify-between mb-6">
                <p className="text-[11px] font-bold uppercase tracking-widest text-emerald-200">
                  What's inside
                </p>
                <span className="text-[11px] font-bold text-slate-400">v2026.05</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {FEATURES.map((f, idx) => (
                  <motion.div
                    key={f.title}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.3 + idx * 0.08 }}
                    className="rounded-2xl bg-white/[0.04] border border-white/10 p-4 hover:bg-white/[0.07] transition-colors"
                  >
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-400/30 to-primary/30 border border-white/10 flex items-center justify-center mb-3">
                      <f.icon className="w-4 h-4 text-emerald-200" />
                    </div>
                    <h3 className="text-sm font-black text-white">{f.title}</h3>
                    <p className="text-[12px] text-slate-400 leading-relaxed mt-1.5">{f.body}</p>
                  </motion.div>
                ))}
              </div>

              <div className="mt-6 grid grid-cols-3 gap-3 text-center">
                {[
                  { k: 'Stores', v: '4+' },
                  { k: 'Agents', v: '5' },
                  { k: 'Avg. Saving', v: '%18' },
                ].map((s) => (
                  <div key={s.k} className="rounded-xl bg-white/[0.03] border border-white/10 py-3">
                    <p className="text-xl font-black text-white">{s.v}</p>
                    <p className="text-[10px] uppercase tracking-widest text-slate-400 mt-0.5">
                      {s.k}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </main>

        {/* Footer */}
        <footer className="px-8 lg:px-16 pb-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <span>© {new Date().getFullYear()} Techno Track — Smarter shopping, less spending.</span>
          <span className="flex items-center gap-4">
            <a className="hover:text-slate-300 transition-colors" href="#">Privacy</a>
            <a className="hover:text-slate-300 transition-colors" href="#">Terms</a>
            <a className="hover:text-slate-300 transition-colors" href="#">Contact</a>
          </span>
        </footer>
      </div>
    </div>
  );
};

export default Landing;
