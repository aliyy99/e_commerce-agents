import React, { useState, useEffect, useRef } from 'react';
import { Heart, Bell, ChevronLeft, ChevronRight } from 'lucide-react';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';

const ProductCard = ({ product, onClick, onFavorite, onTrack, isFavorite, isTracked, analyzedPrice = null }) => {
  const images = (product.images && product.images.length > 0) ? product.images : [PRODUCT_IMAGE_FALLBACK];
  const [imgIndex, setImgIndex] = useState(0);
  const [isHover, setIsHover] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (isHover && images.length > 1) {
      intervalRef.current = setInterval(() => {
        setImgIndex((i) => (i + 1) % images.length);
      }, 1200);
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isHover, images.length]);

  useEffect(() => {
    if (!isHover) setImgIndex(0);
  }, [isHover]);

  const goPrev = (e) => {
    e.stopPropagation();
    setImgIndex((i) => (i - 1 + images.length) % images.length);
  };
  const goNext = (e) => {
    e.stopPropagation();
    setImgIndex((i) => (i + 1) % images.length);
  };

  return (
    <div
      className="glass-card flex flex-col overflow-hidden bg-white hover:border-primary/30 transition-all cursor-pointer group"
      onClick={() => onClick(product)}
      onMouseEnter={() => setIsHover(true)}
      onMouseLeave={() => setIsHover(false)}
    >
      <div className="relative h-48 bg-slate-100 overflow-hidden">
        {isTracked && trackingExpiresAt && (
          <div className={`absolute top-3 left-3 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 shadow-sm backdrop-blur-md z-10 transition-all ${isExpired ? 'bg-slate-900/80 text-white' : 'bg-primary/90 text-white'}`}>
            <Timer className="w-3.5 h-3.5" />
            {timeLeft}
          </div>
        )}
        <img
          key={imgIndex}
          src={images[imgIndex]}
          alt={product.name}
          onError={(e) => {
            if (e.currentTarget.dataset.fallbackApplied === 'true') return;
            e.currentTarget.dataset.fallbackApplied = 'true';
            e.currentTarget.src = PRODUCT_IMAGE_FALLBACK;
          }}
          className="w-full h-full object-contain p-3 bg-white transition-all duration-500"
        />

        {images.length > 1 && (
          <>
            <button
              onClick={goPrev}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-white/85 backdrop-blur text-slate-600 hover:text-primary hover:bg-white shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label="Previous image"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={goNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-white/85 backdrop-blur text-slate-600 hover:text-primary hover:bg-white shadow-sm flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
              aria-label="Next image"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1.5">
              {images.map((_, idx) => (
                <button
                  key={idx}
                  onClick={(e) => { e.stopPropagation(); setImgIndex(idx); }}
                  className={`h-1.5 rounded-full transition-all ${idx === imgIndex ? 'w-5 bg-primary' : 'w-1.5 bg-slate-300 hover:bg-slate-400'}`}
                  aria-label={`Show image ${idx + 1}`}
                />
              ))}
            </div>
          </>
        )}

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
            {analyzedPrice != null ? (
              <>
                <p className="text-[10px] text-emerald-500 font-bold uppercase">Analyzed Lowest</p>
                <p className="text-lg font-black text-slate-900">
                  {Math.round(analyzedPrice).toLocaleString()} TL
                </p>
              </>
            ) : (
              <>
                <p className="text-[10px] text-slate-400 font-bold uppercase">Price</p>
                <p className="text-sm font-bold text-slate-400">Run analysis</p>
              </>
            )}
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
t-lg font-black text-slate-900">
                  {Math.round(analyzedPrice).toLocaleString()} TL
                </p>
              </>
            ) : (
              <>
                <p className="text-[10px] text-slate-400 font-bold uppercase">Price</p>
                <p className="text-sm font-bold text-slate-400">Run analysis</p>
              </>
            )}
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
