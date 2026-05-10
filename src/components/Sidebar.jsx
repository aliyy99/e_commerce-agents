import React from 'react';
import { motion } from 'framer-motion';
import { Eye, Search, BarChart3, Cpu } from 'lucide-react';

const agents = [
  { id: 'vision', name: 'Vision Agent', status: 'Identifying...', icon: Eye },
  { id: 'detective', name: 'Detective Agent', status: 'Scraping Prices...', icon: Search },
  { id: 'analyst', name: 'Analyst Agent', status: 'Checking Reviews...', icon: BarChart3 },
];

const Sidebar = () => {
  return (
    <div className="w-80 h-screen glass-sidebar p-6 flex flex-col gap-8 fixed left-0 top-0 z-50">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-primary rounded-lg">
          <Cpu className="w-6 h-6 text-white" />
        </div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900">
          ShopSage <span className="text-primary">AI</span>
        </h1>
      </div>

      <div className="flex flex-col gap-4">
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest px-2">
          Active AI Agents
        </h2>
        {agents.map((agent) => (
          <motion.div
            key={agent.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 hover:border-primary/20 hover:bg-primary/5 transition-all group cursor-pointer"
          >
            <div className="p-2 rounded-xl bg-white text-primary border border-slate-100 group-hover:bg-primary group-hover:text-white transition-colors shadow-sm">
              <agent.icon className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-slate-700">{agent.name}</p>
              <p className="text-xs text-slate-500">{agent.status}</p>
            </div>
            <div className="status-dot shadow-[0_0_8px_rgba(5,150,105,0.3)]" />
          </motion.div>
        ))}
      </div>

      <div className="mt-auto p-4 rounded-2xl bg-primary/5 border border-primary/10">
        <p className="text-xs font-medium text-slate-600 mb-2">System Load</p>
        <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
          <motion.div 
            className="h-full bg-primary"
            initial={{ width: 0 }}
            animate={{ width: '65%' }}
            transition={{ duration: 2, ease: "easeOut" }}
          />
        </div>
        <p className="text-[10px] text-slate-400 mt-2 text-right">Agentic Mesh: Optimized</p>
      </div>
    </div>
  );
};

export default Sidebar;
