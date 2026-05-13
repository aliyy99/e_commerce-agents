import React from 'react';
import { Heart, Bell, Star, Zap } from 'lucide-react';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';

const ProductCard = ({ product, onClick, onFavorite, onTrack, isFavorite, isTracked }) => {
  const imageSrc = product.images?.[0] || PRODUCT_IMAGE_FALLBACK;

  return (
    <div 
      className="glass-card flex flex-col overflow-hidden bg-white hover:border-primary/30 transition-all cursor-pointer group"
      onClick={() => onClick(product)}
    >
      <div className="relative h-48 bg-slate-100 overflow-hidden">
        <img 
          src={imageSrc}
          alt={product.name} 
          onError={(e) => {
            if (e.currentTarget.dataset.fallbackApplied === 'true') return;
            e.currentTarget.dataset.fallbackApplied = 'true';
            e.currentTarget.src = PRODUCT_IMAGE_FALLBACK;
          }}
          className="w-full h-full object-contain p-3 bg-white transition-transform duration-500"
        />
        <div className={`absolute top-3 right-3 flex flex-col gap-2 transition-opacity ${isFavorite || isTracked ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
          <button 
            onClick={(e) => { e.stopPropagation(); onFavorite(product); }}
            className={`w-8 h-8 backdrop-blur rounded-full flex items-center justify-center shadow-sm transition-all ${isFavorite ? 'bg-accent-rose text-white' : 'bg-white/90 text-slate-400 hover:text-accent-rose hover:bg-white'}`}
            title="Add to Favorites"
          >
            <Heart className="w-4 h-4" fill={isFavorite ? "currentColor" : "none"} />
          </button>
          <button 
            onClick={(e) => { e.stopPropagation(); onTrack(product); }}
            className={`w-8 h-8 backdrop-blur rounded-full flex items-center justify-center shadow-sm transition-all ${isTracked ? 'bg-primary text-white' : 'bg-white/90 text-slate-400 hover:text-primary hover:bg-white'}`}
            title="Track"
          >
            <Bell className="w-4 h-4" fill={isTracked ? "currentColor" : "none"} />
          </button>
        </div>
      </div>
      <div className="p-5 flex-1 flex flex-col">
        <h3 className="text-lg font-bold text-slate-900 mb-2">{product.name}</h3>
        <p className="text-xs text-slate-500 mb-4 line-clamp-2 flex-1">
          {product.description}
        </p>
        <div className="mt-auto border-t border-slate-100 pt-4 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-slate-400 font-bold uppercase">Starting At</p>
            <p className="text-lg font-black text-slate-900">{Math.min(...product.stores.map(s => s.price)).toLocaleString()} TL</p>
          </div>
          <button className="text-xs font-bold text-primary hover:underline">
            View Details
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
