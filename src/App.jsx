import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ProductAnalysis from './components/ProductAnalysis';
import Profile from './components/Profile';
import { Bell, User, Search, Settings, ChevronDown, LogOut, Heart, UserCircle, LayoutDashboard } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background text-slate-100 font-sans selection:bg-primary/20">
      <Sidebar activePage={currentPage} onNavigate={setCurrentPage} />
      
      <main className="pl-72 relative z-10 transition-all duration-300">
        {/* Web App Header */}
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-100 px-10 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6 flex-1">
            <h2 className="text-lg font-black text-slate-900 tracking-tight capitalize">
              {currentPage === 'dashboard' ? 'Intelligence Dashboard' : 'Account Intelligence'}
            </h2>
            <div className="flex items-center gap-4 bg-slate-100 px-4 py-2 rounded-xl border border-slate-200 w-full max-w-xl focus-within:border-primary/50 transition-all group">
              <Search className="w-4 h-4 text-slate-400 group-focus-within:text-primary transition-colors" />
              <input 
                type="text" 
                placeholder="Paste a product link or search intelligence..." 
                className="bg-transparent border-none outline-none text-sm w-full text-slate-900 placeholder:text-slate-400"
              />
            </div>
          </div>

          <div className="flex items-center gap-4 ml-6">
            <button className="relative p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors border border-transparent hover:border-slate-100">
              <Bell className="w-5 h-5" />
              <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-primary rounded-full border-2 border-white" />
            </button>
            <button className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors border border-transparent hover:border-slate-100">
              <Settings className="w-5 h-5" />
            </button>
            
            <div className="h-8 w-px bg-slate-200 mx-2" />
            
            <div className="relative">
              <button 
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-3 pl-2 pr-1 py-1 rounded-xl hover:bg-slate-50 transition-all border border-transparent hover:border-slate-200 group"
              >
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-black leading-none text-slate-900">Alex Rivera</p>
                  <p className="text-[10px] text-primary font-bold mt-1">Pro Analyst</p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 overflow-hidden relative">
                  <User className="w-6 h-6" />
                </div>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              <AnimatePresence>
                {isUserMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setIsUserMenuOpen(false)} />
                    <motion.div 
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute right-0 mt-3 w-56 glass-card p-2 z-50 border-slate-200 shadow-xl bg-white"
                    >
                      <button 
                        onClick={() => { setCurrentPage('profile'); setIsUserMenuOpen(false); }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all"
                      >
                        <UserCircle className="w-4 h-4" />
                        My Profile
                      </button>
                      <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all">
                        <Heart className="w-4 h-4" />
                        Favorites
                      </button>
                      <div className="h-px bg-slate-100 my-2" />
                      <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-accent-rose hover:bg-accent-rose/5 transition-all font-bold">
                        <LogOut className="w-4 h-4" />
                        Sign Out
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        <div className="px-10 py-8 max-w-[1600px] mx-auto overflow-hidden">
          <AnimatePresence mode="wait">
            {currentPage === 'dashboard' ? (
              <motion.div 
                key="dashboard"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-10"
              >
                {/* Quick Stats / Overview */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                  {[
                    { label: 'Active Monitors', value: '12', sub: '+2 today', color: 'primary' },
                    { label: 'Intelligence Gathered', value: '1.4k', sub: 'Last 24h', color: 'blue' },
                    { label: 'Successful Finds', value: '28', sub: 'Last 7 days', color: 'emerald' },
                    { label: 'Credits Remaining', value: '450', sub: 'Refills in 2d', color: 'amber' },
                  ].map((stat, i) => (
                    <div key={i} className="glass-card p-6 flex flex-col gap-2 border-slate-100 hover:border-slate-200 transition-colors bg-white">
                      <span className="text-[10px] font-black text-slate-400 uppercase tracking-widest">{stat.label}</span>
                      <div className="flex items-end gap-2">
                        <span className="text-3xl font-black text-slate-900">{stat.value}</span>
                        <span className="text-[10px] text-primary font-bold mb-1.5 uppercase">{stat.sub}</span>
                      </div>
                    </div>
                  ))}
                </div>

                <ProductAnalysis loading={false} />
                
                <div className="grid grid-cols-1 xl:grid-cols-3 gap-8 pb-10">
                  <div className="xl:col-span-2 glass-card p-8 border-slate-100 bg-white">
                    <div className="flex items-center justify-between mb-8">
                      <h3 className="text-xl font-display font-black text-slate-900">Intelligence Activity</h3>
                      <button className="text-xs text-primary font-black uppercase tracking-widest hover:underline">View Stream</button>
                    </div>
                    <div className="space-y-8">
                      {[1,2,3].map(i => (
                        <div key={i} className="flex items-start gap-4 pb-8 border-b border-slate-100 last:border-0 last:pb-0">
                          <div className="w-11 h-11 rounded-xl bg-slate-50 flex items-center justify-center border border-slate-100 shadow-inner">
                            <Search className="w-5 h-5 text-slate-400" />
                          </div>
                          <div className="flex-1">
                            <p className="text-sm font-bold text-slate-900">Detective Agent found a new price point</p>
                            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">Sony WH-1000XM5 price dropped by <span className="text-primary font-bold">12%</span> on Amazon Marketplace.</p>
                          </div>
                          <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">14m ago</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="glass-card p-8 flex flex-col border-slate-100 bg-white">
                    <h3 className="text-xl font-display font-black mb-8 text-slate-900">Agent Network</h3>
                    <div className="space-y-6 flex-1">
                      <div className="p-5 rounded-2xl bg-primary/5 border border-primary/10 group hover:bg-primary/10 transition-all cursor-pointer">
                        <div className="flex justify-between items-center mb-4">
                          <span className="text-xs font-black text-slate-700 uppercase tracking-widest">Vision Node A-1</span>
                          <span className="px-2 py-0.5 rounded-md bg-primary text-white text-[10px] font-black uppercase">ACTIVE</span>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: '85%' }}
                            className="bg-primary h-full shadow-[0_0_10px_rgba(5,150,105,0.3)]" 
                          />
                        </div>
                        <p className="text-[10px] text-slate-500 mt-3 font-bold uppercase tracking-tighter">Processing: Multimodal Query #4492</p>
                      </div>
                      <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200 group hover:border-slate-300 transition-all cursor-pointer">
                        <div className="flex justify-between items-center mb-4">
                          <span className="text-xs font-black text-slate-400 uppercase tracking-widest">Analyst Cluster B</span>
                          <span className="px-2 py-0.5 rounded-md bg-slate-200 text-slate-500 text-[10px] font-black uppercase">IDLE</span>
                        </div>
                        <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                          <div className="bg-slate-300 h-full w-0" />
                        </div>
                        <p className="text-[10px] text-slate-500 mt-3 font-bold uppercase tracking-tighter">Standby: Monitoring Review Stream</p>
                      </div>
                    </div>
                    <button className="btn-primary w-full mt-8 py-4 text-xs tracking-widest uppercase">UPGRADE AGENT MESH</button>
                  </div>
                </div>
              </motion.div>
            ) : (
              <motion.div 
                key="profile"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <Profile />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;
