import React from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, ShieldCheck, AlertCircle, TrendingDown, ArrowUpRight, Check, X, Info, Star, Heart, Bell } from 'lucide-react';

const ProductAnalysis = ({ loading, product, onFavorite, onTrack, isFavorite, isTracked }) => {
  if (loading || !product) {
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

  const { strategy, aiSummary, name: productName, stores } = product;
  const recommendedPrice = Math.min(...stores.map(s => s.price));
  
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

  const renderStars = (rating, maxRating) => {
    const stars = [];
    for (let i = 1; i <= maxRating; i++) {
      stars.push(
        <Star 
          key={i} 
          className={`w-3 h-3 ${i <= Math.round(rating) ? 'text-yellow-400 fill-yellow-400' : 'text-slate-200'}`} 
        />
      );
    }
    return stars;
  };

  return (
    <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Bento 1: Product Visual & Trust */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="lg:col-span-4 glass-card p-6 flex flex-col gap-8 h-fit bg-white"
      >
        <div className="relative group">
          <div className="aspect-square rounded-2xl overflow-hidden border border-slate-100">
            <img 
              src={product.image} 
              alt={productName} 
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700"
            />
          </div>
          <div className="absolute top-4 right-4 flex flex-col gap-2">
            <button 
              onClick={onFavorite}
              className={`w-10 h-10 rounded-full flex items-center justify-center shadow-md transition-all ${isFavorite ? 'bg-accent-rose text-white' : 'bg-white text-slate-400 hover:text-accent-rose'}`}
            >
              <Heart className="w-5 h-5" fill={isFavorite ? "currentColor" : "none"} />
            </button>
            <button 
              onClick={onTrack}
              className={`w-10 h-10 rounded-full flex items-center justify-center shadow-md transition-all ${isTracked ? 'bg-primary text-white' : 'bg-white text-slate-400 hover:text-primary'}`}
            >
              <Bell className="w-5 h-5" fill={isTracked ? "currentColor" : "none"} />
            </button>
          </div>
        </div>

        <div className="mt-2">
          <h3 className="text-2xl font-display font-black text-slate-900">{productName}</h3>
          <p className="text-sm text-slate-500 mt-2">{product.description}</p>
        </div>
      </motion.div>

      {/* Bento 2: Strategic Advice & Stores Analysis */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="lg:col-span-8 flex flex-col gap-6"
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
              <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">En İyi Fiyat</p>
              <p className="text-3xl font-black text-slate-900">${recommendedPrice.toLocaleString()}</p>
            </div>
          </div>
        </div>

        {/* E-Commerce Stores Analysis */}
        <div className="glass-card p-6 bg-white border-slate-100 flex-1">
          <h3 className="font-display font-bold text-slate-900 mb-6 flex items-center gap-2">
            <TrendingDown className="w-4 h-4 text-primary" />
            Market Analizi ve Yorumlar
          </h3>
          <div className="grid grid-cols-1 gap-4">
            {stores.map((store, i) => (
              <div key={store.name} className="flex flex-col p-5 rounded-2xl bg-slate-50 border border-slate-100 hover:border-primary/20 transition-all">
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-slate-200">
                  <div>
                    <p className="text-lg font-black text-slate-900">{store.name}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex">{renderStars(store.rating, store.maxRating)}</div>
                      <span className="text-xs text-slate-500 font-bold">{store.rating} / {store.maxRating}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-black text-slate-900">${store.price.toLocaleString()}</p>
                    {store.price === recommendedPrice && (
                      <span className="px-2 py-1 bg-primary/10 text-primary rounded text-[10px] font-bold uppercase">En İyi Fiyat</span>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-[10px] font-black text-emerald-600 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                      <Check className="w-3 h-3" />
                      Müşteri Artıları
                    </h4>
                    <ul className="space-y-2">
                      {store.pros.map(pro => (
                        <li key={pro} className="text-xs text-slate-600 flex items-start gap-2">
                          <div className="mt-1 w-1 h-1 rounded-full bg-emerald-500 shrink-0" />
                          {pro}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h4 className="text-[10px] font-black text-accent-rose uppercase tracking-widest mb-3 flex items-center gap-1.5">
                      <X className="w-3 h-3" />
                      Müşteri Eksileri
                    </h4>
                    <ul className="space-y-2">
                      {store.cons.map(con => (
                        <li key={con} className="text-xs text-slate-600 flex items-start gap-2">
                          <div className="mt-1 w-1 h-1 rounded-full bg-accent-rose shrink-0" />
                          {con}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </motion.div>
    </div>
  );
};

export default ProductAnalysis;
