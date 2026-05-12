import React from 'react';
import { 
  LayoutDashboard, 
  TrendingUp, 
  Zap, 
  Heart,
  Shield,
  CreditCard,
  User,
  Tag
} from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = ({ activePage, onNavigate }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'campaigns', label: 'Campaigns', icon: Tag },
    { id: 'market', label: 'Market Trends', icon: TrendingUp },
    { id: 'tracked', label: 'Tracked Products', icon: Zap },
    { id: 'favorites', label: 'Favorites', icon: Heart },
  ];

  return (
    <aside className="fixed left-0 top-0 h-full w-72 bg-white/50 backdrop-blur-xl border-r border-slate-200 z-50 flex flex-col p-6">
      {/* Brand */}
      <div className="flex items-center gap-3 px-4 mb-10 group cursor-pointer" onClick={() => onNavigate('dashboard')}>
        <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center shadow-lg shadow-primary/20 group-hover:scale-110 transition-transform">
          <Zap className="w-6 h-6 text-white fill-white" />
        </div>
        <h1 className="text-xl font-display font-black tracking-tighter text-slate-900">SHOPSAGE<span className="text-primary">.AI</span></h1>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1.5">
        <p className="px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest mb-4">Intelligence Mesh</p>
        {menuItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group ${
              activePage === item.id 
              ? 'bg-primary text-white font-bold shadow-lg shadow-primary/10' 
              : 'text-slate-500 hover:bg-primary/5 hover:text-primary'
            }`}
          >
            <item.icon className={`w-5 h-5 ${activePage === item.id ? 'text-white' : 'text-slate-400 group-hover:text-primary transition-colors'}`} />
            <span className="text-sm">{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
};

export default Sidebar;
