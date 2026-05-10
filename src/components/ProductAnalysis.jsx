import React from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, ShieldCheck, AlertCircle, TrendingDown, ArrowUpRight, Check, X, Info } from 'lucide-react';

const ProductAnalysis = ({ loading, data }) => {
  // When `data` (OrchestrateResponse) is available, use it; otherwise show mock data.
  // Future: map data.analyst_result, data.detective_result to the Bento cards dynamically.
  const stores = [
    { name: 'eBay', price: 1245.50, status: 'Limited', color: 'text-blue-400' },
    { name: 'Amazon', price: 1299.00, status: 'In Stock', color: 'text-orange-400' },
    { name: 'Local Store', price: 1350.00, status: 'In Stock', color: 'text-emerald-400' },
  ].sort((a, b) => a.price - b.price);

  const strategy = data?.analyst_result?.strategy || 'BELİRSİZ';
  const aiSummary = data?.analyst_result?.ai_summary || 'Fiyat şu an 30 günlük ortalamanın %12 altında. Mevcut stok seviyeleri kritik, önümüzdeki 2 hafta içinde bir indirim beklenmiyor.';
  const productName = data?.analyst_result?.product_name || 'MacBook Pro 14" M3';
  const recommendedPrice = data?.analyst_result?.price_trend?.current_price || 1245.50;
  
  let strategyColor = 'bg-slate-400';
  let strategyText = 'BELİRSİZ';
  let isPulsing = false;
  
  if (strategy === 'AL') {
    strategyColor = 'bg-emerald-500';
    strategyText = 'ŞİMDİ AL';
  } else if (strategy === 'BEKLE') {
    strategyColor = 'bg-yellow-500';
    strategyText = 'BEKLE';
    isPulsing = true;
  } else if (strategy === 'KAÇIN') {
    strategyColor = 'bg-red-500';
    strategyText = 'KAÇIN';
    isPulsing = true;
  }

  if (loading) {
    return (
      <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 h-96 skeleton" />
        <div className="lg:col-span-8 grid grid-cols-2 gap-6">
          <div className="h-48 skeleton" />
          <div className="h-48 skeleton" />
          <div className="col-span-2 h-48 skeleton" />
        </div>
      </div>
    );
  }

  return (
    <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Bento 1: Product Visual & Trust (Radial) */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="lg:col-span-4 glass-card p-6 flex flex-col gap-8 h-fit bg-white"
      >
        <div className="relative group">
          <div className="aspect-square rounded-2xl overflow-hidden border border-slate-100">
            <img 
              src="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=800" 
              alt={productName} 
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
            />
          </div>
          <div className="absolute -bottom-4 -right-4 w-32 h-32 glass-card flex flex-col items-center justify-center p-4 shadow-xl border-primary/20 bg-white">
            <div className="relative w-16 h-16 mb-1">
              <svg className="w-full h-full" viewBox="0 0 36 36">
                <path className="text-slate-100 stroke-current" strokeWidth="3" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <motion.path 
                  initial={{ strokeDasharray: "0, 100" }}
                  animate={{ strokeDasharray: "94, 100" }}
                  transition={{ duration: 2, ease: "easeOut" }}
                  className="text-primary stroke-current" 
                  strokeWidth="3" 
                  strokeLinecap="round"
                  fill="none" 
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" 
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center text-xs font-bold text-slate-900">94%</div>
            </div>
            <span className="text-[10px] font-bold text-slate-400 uppercase">Trust Score</span>
          </div>
        </div>

        <div className="mt-2">
          <h3 className="text-2xl font-display font-black text-slate-900">{productName}</h3>
          <p className="text-sm text-slate-500 mt-1 flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-primary" />
            Verified by Analyst Cluster B
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {['M3 Pro Chip', '18GB RAM', '512GB SSD'].map(tag => (
            <span key={tag} className="px-3 py-1 bg-slate-100 border border-slate-200 rounded-full text-[10px] font-bold text-slate-600">
              {tag}
            </span>
          ))}
        </div>
      </motion.div>

      {/* Bento 2: Strategic Advice (Glow) */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6"
      >
        <div className={`glass-card p-8 bg-gradient-to-br from-primary/5 to-transparent border-primary/20 flex flex-col justify-between bg-white ${isPulsing ? 'animate-pulse' : 'glow-advice'}`}>
          <div>
            <div className="flex items-center justify-between mb-6">
              <span className={`px-4 py-1.5 ${strategyColor} text-white font-black rounded-lg text-xs uppercase tracking-tighter`}>
                {strategyText}
              </span>
              <div className="flex -space-x-2">
                {[1,2,3].map(i => <div key={i} className="w-6 h-6 rounded-full border-2 border-white bg-slate-200" />)}
              </div>
            </div>
            <h2 className="text-2xl font-display font-black mb-4 text-slate-900">AI Öngörüsü</h2>
            <p className="text-slate-500 text-sm leading-relaxed">
              {aiSummary}
            </p>
          </div>
          <div className="mt-8 pt-6 border-t border-slate-100 flex items-end justify-between">
            <div>
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Recommended Price</p>
              <p className="text-3xl font-black text-slate-900">${recommendedPrice.toLocaleString()}</p>
            </div>
            <button className="btn-primary py-2.5 px-5 text-sm uppercase">Satın Al</button>
          </div>
        </div>

        {/* Bento 3: Price Ranking */}
        <div className="glass-card p-6 bg-white border-slate-100">
          <h3 className="font-display font-bold text-slate-900 mb-6 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-primary" />
            Market Ranking
          </h3>
          <div className="space-y-4">
            {stores.map((store, i) => (
              <div key={store.name} className="flex items-center gap-4 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-all border border-transparent hover:border-slate-200 group cursor-pointer">
                <div className="w-8 h-8 rounded-lg bg-white border border-slate-100 flex items-center justify-center text-xs font-black text-slate-400 group-hover:text-primary transition-colors shadow-sm">
                  #{i+1}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-slate-900">{store.name}</p>
                  <p className="text-[10px] text-slate-400">{store.status}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-black text-slate-900">${store.price.toLocaleString()}</p>
                  <p className="text-[10px] text-primary font-bold">Best Deal</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bento 4: AI Pro/Con List */}
        <div className="md:col-span-2 glass-card p-8 grid grid-cols-1 md:grid-cols-2 gap-8 bg-white border-slate-100">
          <div>
            <h4 className="text-xs font-black text-primary uppercase tracking-widest mb-4 flex items-center gap-2">
              <Check className="w-4 h-4" />
              Güçlü Yönler (Pros)
            </h4>
            <ul className="space-y-3">
              {[
                'Üstün M3 performans verimliliği',
                'Ekran parlaklığı ve renk doğruluğu',
                'Uzun batarya ömrü (22 saat+)',
              ].map(item => (
                <li key={item} className="text-sm text-slate-600 flex items-start gap-3">
                  <div className="mt-1 w-1.5 h-1.5 rounded-full bg-primary/40 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs font-black text-accent-rose uppercase tracking-widest mb-4 flex items-center gap-2">
              <X className="w-4 h-4" />
              Zayıf Yönler (Cons)
            </h4>
            <ul className="space-y-3">
              {[
                'Yüksek başlangıç fiyatı',
                'Base modelde 8GB RAM sınırlaması',
                'SSD hızları önceki nesle göre stabil değil',
              ].map(item => (
                <li key={item} className="text-sm text-slate-600 flex items-start gap-3">
                  <div className="mt-1 w-1.5 h-1.5 rounded-full bg-accent-rose/40 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default ProductAnalysis;
