import React from 'react';
import { motion } from 'framer-motion';
import { User, Heart, Bell, Settings, LogOut, ShoppingCart, ArrowRight } from 'lucide-react';

const Profile = () => {
  const [activeTab, setActiveTab] = React.useState('favorites');

  const favorites = [
    { id: 1, name: 'Sony WH-1000XM5', price: '$348.00', image: 'https://images.unsplash.com/photo-1613040809024-b4ef7ba99bc3?auto=format&fit=crop&q=80&w=400' },
    { id: 2, name: 'MacBook Pro 14"', price: '$1,245.50', image: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=400' },
    { id: 3, name: 'Logitech MX Master 3S', price: '$99.00', image: 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&q=80&w=400' },
  ];

  return (
    <div className="flex gap-8">
      {/* Profile Sidebar */}
      <div className="w-64 flex flex-col gap-2">
        <button 
          onClick={() => setActiveTab('profile')}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'profile' ? 'bg-primary text-white font-bold' : 'text-slate-500 hover:bg-slate-100'}`}
        >
          <User className="w-5 h-5" />
          Profil
        </button>
        <button 
          onClick={() => setActiveTab('favorites')}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'favorites' ? 'bg-primary text-white font-bold' : 'text-slate-500 hover:bg-slate-100'}`}
        >
          <Heart className="w-5 h-5" />
          Favorilerim
        </button>
        <button 
          onClick={() => setActiveTab('alarms')}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'alarms' ? 'bg-primary text-white font-bold' : 'text-slate-500 hover:bg-slate-100'}`}
        >
          <Bell className="w-5 h-5" />
          Alarmlarım
        </button>
        <div className="h-px bg-slate-100 my-2" />
        <button className="flex items-center gap-3 px-4 py-3 rounded-xl text-accent-rose hover:bg-accent-rose/5 transition-all font-bold">
          <LogOut className="w-5 h-5" />
          Çıkış Yap
        </button>
      </div>

      {/* Content Area */}
      <div className="flex-1">
        {activeTab === 'favorites' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-display font-black text-slate-900">Favorilerim</h2>
            <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-6">
              {favorites.map((item) => (
                <motion.div 
                  key={item.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-card overflow-hidden group border-slate-100 hover:border-primary/30 transition-all bg-white"
                >
                  <div className="aspect-video relative overflow-hidden">
                    <img src={item.image} alt={item.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    <div className="absolute top-3 right-3 px-3 py-1 bg-white/90 backdrop-blur-md rounded-full text-xs font-bold text-slate-900 border border-slate-100">
                      {item.price}
                    </div>
                  </div>
                  <div className="p-5">
                    <h3 className="font-bold text-slate-900 mb-4">{item.name}</h3>
                    <div className="flex gap-2">
                      <button className="flex-1 py-2 bg-slate-50 hover:bg-accent-rose/5 hover:text-accent-rose border border-slate-200 rounded-lg text-xs font-bold text-slate-500 transition-all">
                        Takibi Bırak
                      </button>
                      <button className="flex-1 py-2 bg-primary/10 hover:bg-primary text-primary hover:text-white border border-primary/20 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2">
                        Siteye Git
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'profile' && (
          <div className="glass-card p-8 space-y-8 bg-white border-slate-100">
            <div className="flex items-center gap-6">
              <div className="w-24 h-24 rounded-full bg-primary/10 border-4 border-white flex items-center justify-center text-primary shadow-sm">
                <User className="w-12 h-12" />
              </div>
              <div>
                <h2 className="text-2xl font-display font-black text-slate-900">Alex Rivera</h2>
                <p className="text-slate-500">Pro Analyst Account</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-6 pt-6 border-t border-slate-100">
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">E-posta</p>
                <p className="text-sm font-bold text-slate-900">alex.rivera@example.com</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Üyelik Tarihi</p>
                <p className="text-sm font-bold text-slate-900">Ekim 2025</p>
              </div>
            </div>
            <button className="btn-primary w-full py-4 text-sm mt-4 uppercase tracking-widest">Ayarları Güncelle</button>
          </div>
        )}

        {activeTab === 'alarms' && (
          <div className="glass-card p-12 text-center flex flex-col items-center gap-4 bg-white border-slate-100">
            <div className="w-16 h-16 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-300">
              <Bell className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">Henüz Alarm Yok</h3>
            <p className="text-slate-500 max-w-xs">Ürün sayfalarından fiyat alarmı kurarak fırsatları kaçırmayın.</p>
            <button className="text-primary font-bold hover:underline mt-2">Ürünleri Keşfet</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;
