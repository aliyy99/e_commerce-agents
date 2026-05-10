import React from 'react';
import { 
  LayoutDashboard, 
  Search, 
  History, 
  TrendingUp, 
  Zap, 
  Shield,
  CreditCard,
  User
} from 'lucide-react';
import { motion } from 'framer-motion';

const Sidebar = ({ activePage, onNavigate }) => {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'search', label: 'Intelligence Search', icon: Search },
    { id: 'history', label: 'Analysis History', icon: History },
    { id: 'market', label: 'Market Trends', icon: TrendingUp },
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

      {/* Footer Card */}
      <div className="mt-auto pt-6 border-t border-slate-100">
        <div className="p-5 rounded-2xl bg-gradient-to-br from-primary/10 to-transparent border border-primary/10 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
            <Shield className="w-12 h-12 text-primary" />
          </div>
          <div className="relative z-10">
            <div className="flex items-center gap-2 mb-3">
              <CreditCard className="w-4 h-4 text-primary" />
              <span className="text-[10px] font-black text-primary uppercase tracking-widest">Enterprise Plan</span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed mb-4">Ajanlarınızı %100 kapasiteyle kullanın.</p>
            <button 
              onClick={() => onNavigate('profile')}
              className="w-full py-2.5 bg-primary/10 hover:bg-primary text-primary hover:text-white rounded-lg text-xs font-black transition-all border border-primary/20"
            >
              UPGRADE NOW
            </button>
          </div>
        </div>
        
        <button 
          onClick={() => onNavigate('profile')}
          className={`w-full mt-4 flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${
            activePage === 'profile' ? 'bg-slate-100 text-slate-900' : 'text-slate-500 hover:text-slate-900'
          }`}
        >
          <User className="w-5 h-5 text-slate-400" />
          <span className="text-sm font-bold">Account Settings</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
