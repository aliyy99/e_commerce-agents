import React from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, ShieldCheck, AlertCircle, TrendingDown, ArrowUpRight, Check, X, Info, Star, Heart, Bell, Zap } from 'lucide-react';

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
  let strategyText = 'UNCERTAIN';
  let isPulsing = false;
  
  if (strategy === 'AL') {
    strategyColor = 'bg-emerald-500';
    strategyText = 'BUY NOW';
  } else if (strategy === 'BEKLE') {
    strategyColor = 'bg-yellow-500';
    strategyText = 'WAIT';
    isPulsing = true;
  } else if (strategy === 'KAÇIN') {
    strategyColor = 'bg-red-500';
    strategyText = 'AVOID';
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

        {/* Technical Specs Section */}
        {product.specs && (
          <div className="mt-4 space-y-4">
            <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-2">Technical Details</h4>
            <div className="grid grid-cols-1 gap-3">
              {product.specs.map(spec => (
                <div key={spec.label} className="flex justify-between items-center py-1">
                  <span className="text-[10px] font-bold text-slate-500">{spec.label}</span>
                  <span className="text-[10px] font-black text-slate-900 text-right ml-4">{spec.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </motion.div>

      {/* Bento 2: Placeholder for Strategic Advice & Stores Analysis */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="lg:col-span-8 flex flex-col gap-6 items-center justify-center bg-slate-50/50 rounded-2xl border border-dashed border-slate-200 relative min-h-[400px]"
      >
        <div className="text-center p-8">
          <div className="w-16 h-16 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Zap className="w-8 h-8" />
          </div>
          <h3 className="text-xl font-display font-black text-slate-900 mb-2">Detailed Analysis</h3>
          <p className="text-slate-500 text-sm max-w-sm mx-auto">
            AI-powered detailed analysis of the product's price history, seller reliability scores, and customer reviews.
          </p>
        </div>

        {/* Analyze Button (Top Right) */}
        <div className="absolute top-6 right-6">
          <button 
            disabled
            className="flex items-center gap-2 px-6 py-3 bg-primary/50 text-white rounded-xl font-bold text-sm shadow-lg shadow-primary/20 cursor-not-allowed transition-all"
            title="Currently inactive"
          >
            <Zap className="w-4 h-4" />
            Analyze
          </button>
        </div>
      </motion.div>
    </div>
  );
};

export default ProductAnalysis;
