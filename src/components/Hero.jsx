import React from 'react';
import { motion } from 'framer-motion';
import { Search, Camera, Sparkles } from 'lucide-react';

const Hero = () => {
  return (
    <div className="flex flex-col items-center justify-center pt-24 pb-12 px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8 }}
        className="text-center mb-12"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-semibold mb-6">
          <Sparkles className="w-3 h-3" />
          <span>Next-Gen Shopping Intelligence</span>
        </div>
        <h1 className="text-5xl md:text-6xl font-display font-extrabold mb-6 leading-tight text-slate-900">
          Shop Smarter with <br />
          <span className="gradient-text">Agentic Intelligence</span>
        </h1>
        <p className="text-slate-500 text-lg max-w-2xl mx-auto">
          Our specialized AI agents scan the web, analyze reviews, and track prices 
          in real-time to ensure you always get the best value.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="w-full max-w-3xl relative"
      >
        <div className="relative glass-card p-2 flex items-center gap-2">
          <div className="flex-1 flex items-center gap-4 px-4">
            <Search className="w-5 h-5 text-slate-400" />
            <input 
              type="text" 
              placeholder="Paste a product link or search anything..." 
              className="bg-transparent border-none outline-none w-full text-slate-900 placeholder:text-slate-400 py-4"
            />
          </div>
          <button className="p-3 hover:bg-slate-100 rounded-xl transition-colors text-slate-400 hover:text-slate-600 group">
            <Camera className="w-6 h-6 group-hover:scale-110 transition-transform" />
          </button>
          <button className="btn-primary">
            Analyze Now
          </button>
        </div>
        <div className="flex gap-4 mt-6 justify-center text-xs text-slate-400">
          <span>Try: "Latest OLED Laptops"</span>
          <span>•</span>
          <span>"Best Noise Cancelling Headphones"</span>
          <span>•</span>
          <span>"Budget 4K Monitors"</span>
        </div>
      </motion.div>
    </div>
  );
};

export default Hero;
