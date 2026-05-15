import React from 'react';
import { motion } from 'framer-motion';
import { User, Heart, Bell, Settings, LogOut, ShoppingCart, ArrowRight } from 'lucide-react';

const Profile = ({ forceTab }) => {
  const [activeTab, setActiveTab] = React.useState(forceTab || 'profile');

  React.useEffect(() => {
    if (forceTab) setActiveTab(forceTab);
  }, [forceTab]);

  const favorites = [
    { id: 1, name: 'Sony WH-1000XM5', price: '$348.00', image: 'https://images.unsplash.com/photo-1613040809024-b4ef7ba99bc3?auto=format&fit=crop&q=80&w=400' },
    { id: 2, name: 'MacBook Pro 14"', price: '$1,245.50', image: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=400' },
    { id: 3, name: 'Logitech MX Master 3S', price: '$99.00', image: 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&q=80&w=400' },
  ];

  return (
    <div className="flex gap-8">
      {/* Profile Sidebar - Hidden if forced from main sidebar */}
      {!forceTab && (
        <div className="w-64 flex flex-col gap-2">
          <button 
            onClick={() => setActiveTab('profile')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'profile' ? 'bg-primary text-white font-bold' : 'text-slate-500 hover:bg-slate-100'}`}
          >
            <User className="w-5 h-5" />
            Profile
          </button>
          <button 
            onClick={() => setActiveTab('favorites')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'favorites' ? 'bg-primary text-white font-bold' : 'text-slate-500 hover:bg-slate-100'}`}
          >
            <Heart className="w-5 h-5" />
            My Favorites
          </button>
          <button 
            onClick={() => setActiveTab('alarms')}
            className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all ${activeTab === 'alarms' ? 'bg-primary text-white font-bold' : 'text-slate-500 hover:bg-slate-100'}`}
          >
            <Bell className="w-5 h-5" />
            My Alarms
          </button>
          <div className="h-px bg-slate-100 my-2" />
          <button className="flex items-center gap-3 px-4 py-3 rounded-xl text-accent-rose hover:bg-accent-rose/5 transition-all font-bold">
            <LogOut className="w-5 h-5" />
            Sign Out
          </button>
        </div>
      )}

      {/* Content Area */}
      <div className="flex-1 max-w-4xl">
        {activeTab === 'favorites' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-display font-black text-slate-900">My Favorites</h2>
            <div className="grid grid-cols-1 xl:grid-cols-2 2xl:grid-cols-3 gap-6">
              {favorites.map((item) => (
                <motion.div 
                  key={item.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="glass-card overflow-hidden group border-slate-100 hover:border-primary/30 transition-all bg-white"
                >
                  <div className="aspect-video relative overflow-hidden">
                    <img src={item.images?.[0]} alt={item.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                    <div className="absolute top-3 right-3 px-3 py-1 bg-white/90 backdrop-blur-md rounded-full text-xs font-bold text-slate-900 border border-slate-100">
                      {item.price}
                    </div>
                  </div>
                  <div className="p-5">
                    <h3 className="font-bold text-slate-900 mb-4">{item.name}</h3>
                    <div className="flex gap-2">
                      <button className="flex-1 py-2 bg-slate-50 hover:bg-accent-rose/5 hover:text-accent-rose border border-slate-200 rounded-lg text-xs font-bold text-slate-500 transition-all">
                        Untrack
                      </button>
                      <button className="flex-1 py-2 bg-primary/10 hover:bg-primary text-primary hover:text-white border border-primary/20 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-2">
                        Go to Site
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
          <div className="space-y-6">
            <h2 className="text-2xl font-display font-black text-slate-900 mb-6">Profile & Settings</h2>
            
            <div className="glass-card p-8 bg-white border-slate-100 mb-8">
              <div className="flex items-center gap-6">
                <div className="relative">
                  <div className="w-24 h-24 rounded-full bg-primary/10 border-4 border-white flex items-center justify-center text-primary shadow-sm">
                    <User className="w-12 h-12" />
                  </div>
                  <button className="absolute bottom-0 right-0 w-8 h-8 bg-white rounded-full border border-slate-200 shadow-sm flex items-center justify-center text-slate-500 hover:text-primary hover:border-primary transition-colors">
                    <Settings className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex-1">
                  <h2 className="text-2xl font-display font-black text-slate-900">Alex Rivera</h2>
                  <p className="text-sm font-bold text-primary mb-2">Pro Analyst Account</p>
                  <p className="text-xs text-slate-500">Last login: Today 14:23</p>
                </div>
                <button className="btn-primary py-3 px-6 text-sm uppercase tracking-widest">
                  Edit Profile
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Account Information */}
              <div className="glass-card p-6 bg-white border-slate-100">
                <h3 className="font-bold text-slate-900 mb-6 flex items-center gap-2">
                  <User className="w-5 h-5 text-slate-400" />
                  Account Information
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Full Name</label>
                    <input type="text" defaultValue="Alex Rivera" className="w-full mt-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:border-primary focus:bg-white transition-colors" />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Email</label>
                    <input type="email" defaultValue="alex.rivera@example.com" className="w-full mt-1 px-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:border-primary focus:bg-white transition-colors" />
                  </div>
                  <div>
                    <label className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Password</label>
                    <button className="w-full mt-1 px-4 py-2 bg-white border border-slate-200 rounded-lg text-sm text-slate-600 font-bold hover:bg-slate-50 transition-colors text-left">
                      Change Password...
                    </button>
                  </div>
                </div>
              </div>

              {/* Tercihler */}
              <div className="glass-card p-6 bg-white border-slate-100">
                <h3 className="font-bold text-slate-900 mb-6 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-slate-400" />
                  App Preferences
                </h3>
                <div className="space-y-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-bold text-slate-900">Theme</p>
                      <p className="text-xs text-slate-500">Match system theme</p>
                    </div>
                    <select className="bg-slate-50 border border-slate-200 rounded-lg text-sm px-3 py-1.5 outline-none">
                      <option>System</option>
                      <option>Light</option>
                      <option>Dark</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-bold text-slate-900">Currency</p>
                      <p className="text-xs text-slate-500">Default price display</p>
                    </div>
                    <select className="bg-slate-50 border border-slate-200 rounded-lg text-sm px-3 py-1.5 outline-none">
                      <option>USD ($)</option>
                      <option>TRY (₺)</option>
                      <option>EUR (€)</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-bold text-slate-900">AI Assistant Language</p>
                      <p className="text-xs text-slate-500">Gemini response language</p>
                    </div>
                    <select className="bg-slate-50 border border-slate-200 rounded-lg text-sm px-3 py-1.5 outline-none" defaultValue="English">
                      <option value="Türkçe">Turkish</option>
                      <option value="English">English</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Bildirimler */}
              <div className="glass-card p-6 bg-white border-slate-100 md:col-span-2">
                <h3 className="font-bold text-slate-900 mb-6 flex items-center gap-2">
                  <Bell className="w-5 h-5 text-slate-400" />
                  Notification Settings
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="flex items-center gap-3 p-3 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                    <input type="checkbox" defaultChecked className="w-5 h-5 accent-primary rounded" />
                    <div>
                      <p className="text-sm font-bold text-slate-900">Price Drops</p>
                      <p className="text-xs text-slate-500">When tracked products drop in price</p>
                    </div>
                  </label>
                  <label className="flex items-center gap-3 p-3 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                    <input type="checkbox" defaultChecked className="w-5 h-5 accent-primary rounded" />
                    <div>
                      <p className="text-sm font-bold text-slate-900">Stock Alerts</p>
                      <p className="text-xs text-slate-500">When out-of-stock items return</p>
                    </div>
                  </label>
                  <label className="flex items-center gap-3 p-3 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                    <input type="checkbox" className="w-5 h-5 accent-primary rounded" />
                    <div>
                      <p className="text-sm font-bold text-slate-900">Price Graphic</p>
                      <p className="text-xs text-slate-500">Weekly discount newsletters</p>
                    </div>
                  </label>
                  <label className="flex items-center gap-3 p-3 border border-slate-200 rounded-xl cursor-pointer hover:bg-slate-50 transition-colors">
                    <input type="checkbox" defaultChecked className="w-5 h-5 accent-primary rounded" />
                    <div>
                      <p className="text-sm font-bold text-slate-900">System Notifications</p>
                      <p className="text-xs text-slate-500">Security and account updates</p>
                    </div>
                  </label>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end pt-4">
              <button className="btn-primary py-3 px-8 text-sm uppercase tracking-widest shadow-lg shadow-primary/20">Save Changes</button>
            </div>
          </div>
        )}

        {activeTab === 'alarms' && (
          <div className="glass-card p-12 text-center flex flex-col items-center gap-4 bg-white border-slate-100">
            <div className="w-16 h-16 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-300">
              <Bell className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-900">No Alarms Yet</h3>
            <p className="text-slate-500 max-w-xs">Don't miss out on deals by setting up price alarms on product pages.</p>
            <button className="text-primary font-bold hover:underline mt-2">Discover Products</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;
