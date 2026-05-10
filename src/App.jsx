import React from 'react';
import Sidebar from './components/Sidebar';
import Hero from './components/Hero';
import ProductAnalysis from './components/ProductAnalysis';
import TrackingList from './components/TrackingList';
import ChatWidget from './components/ChatWidget';

import { Bell, User, Search, Settings } from 'lucide-react';

function App() {
  return (
    <div className="min-h-screen bg-background text-slate-900 font-sans selection:bg-primary/10">
      <Sidebar />
      <TrackingList />
      
      <main className="pl-80 relative z-10">
        {/* Web App Header */}
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4 bg-slate-100 px-4 py-2 rounded-xl border border-slate-200 w-96">
            <Search className="w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search assets, agents, or history..." 
              className="bg-transparent border-none outline-none text-sm w-full"
            />
          </div>

          <div className="flex items-center gap-6">
            <button className="relative p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
              <Bell className="w-6 h-6" />
              <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full border-2 border-white" />
            </button>
            <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
              <Settings className="w-6 h-6" />
            </button>
            <div className="h-8 w-[1px] bg-slate-200 mx-2" />
            <button className="flex items-center gap-3 pl-2 pr-1 py-1 rounded-full hover:bg-slate-100 transition-colors">
              <div className="text-right">
                <p className="text-sm font-bold leading-none">Alex Rivera</p>
                <p className="text-[10px] text-slate-500">Pro Account</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                <User className="w-6 h-6" />
              </div>
            </button>
          </div>
        </header>

        <div className="container mx-auto px-8 pb-24">
          <Hero />
          <ProductAnalysis />
          
          <div className="max-w-5xl mx-auto mt-12 grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="glass-card p-8">
              <h3 className="text-xl font-display font-bold mb-4 text-slate-900">Upcoming Drops</h3>
              <p className="text-slate-500 text-sm">Detective Agent is monitoring 12 upcoming releases for price drops.</p>
            </div>
            <div className="glass-card p-8">
              <h3 className="text-xl font-display font-bold mb-4 text-slate-900">Network Status</h3>
              <div className="flex items-center gap-4">
                <div className="flex -space-x-2">
                  {[1,2,3,4].map(i => (
                    <div key={i} className="w-8 h-8 rounded-full border-2 border-white bg-primary/10 flex items-center justify-center text-[10px] font-bold text-primary">
                      A{i}
                    </div>
                  ))}
                </div>
                <p className="text-slate-500 text-sm">4 Specialized nodes active.</p>
              </div>
            </div>
          </div>
        </div>
      </main>

      <ChatWidget />
    </div>
  );
}

export default App;
