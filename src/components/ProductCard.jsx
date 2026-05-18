import React, { useState, useEffect, useRef } from 'react';
import { Heart, Bell, ChevronLeft, ChevronRight, Timer, Tag, Percent, BellRing, ShoppingBag, TrendingDown, TrendingUp, Minus, Store } from 'lucide-react';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';

const formatTimeAgo = (isoString) => {
  if (!isoString) return null;
  const then = Date.parse(isoString);
  if (!Number.isFinite(then)) return null;
  const diffSec = Math.max(1, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  return new Date(then).toLocaleDateString();
};

const formatTimeLeft = (ms) => {
  if (ms <= 0) return 'Expired';
  const totalMinutes = Math.floor(ms / 60000);
  const days = Math.floor(totalMinutes / (60 * 24));
  const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
  const minutes = totalMinutes % 60;
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
};

const computeAverageStorePrice = (stores) => {
  if (!Array.isArray(stores) || stores.length === 0) return null;
  const prices = stores
    .map((s) => Number(s?.price))
    .filter((p) => Number.isFinite(p) && p > 0);
  if (prices.length === 0) return null;
  return prices.reduce((a, b) => a + b, 0) / prices.length;
};

const ProductCard = ({
  product,
  onClick,
  onFavorite,
  onTrack,
  isFavorite,
  isTracked,
  analyzedPrice = null,
  trackingExpiresAt = null,
  priceAlert = null,
  trackingActions = null,
  liveCheck = null,
}) => {
  const images = (product.images && product.images.length > 0) ? product.images : [PRODUCT_IMAGE_FALLBACK];
  const averagePrice = computeAverageStorePrice(product?.stores);
  const [imgIndex, setImgIndex] = useState(0);
  const [isHover, setIsHover] = useState(false);
  const [now, setNow] = useState(Date.now());
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!isTracked || !trackingExpiresAt) return;
    const tick = setInterval(() => setNow(Date.now()), 60000);
    return () => clearInterval(tick);
  }, [isTracked, trackingExpiresAt]);

  const remainingMs = trackingExpiresAt ? trackingExpiresAt - now : 0;
  const isExpired = trackingExpiresAt ? remainingMs <= 0 : false;
  const timeLeft = trackingExpiresAt ? formatTimeLeft(remainingMs) : '';

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
      className={`glass-card flex flex-col overflow-hidden bg-white hover:border-primary/30 transition-all group ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick ? () => onClick(product) : undefined}
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
            ) : averagePrice != null ? (
              <>
                <p className="text-[10px] text-slate-500 font-bold uppercase">Average</p>
                <p className="text-lg font-black text-slate-900">
                  {Math.round(averagePrice).toLocaleString()} TL
                </p>
              </>
            ) : (
              <>
                <p className="text-[10px] text-slate-400 font-bold uppercase">Price</p>
                <p className="text-sm font-bold text-slate-400">Run analysis</p>
              </>
            )}
          </div>
        </div>

        {(priceAlert || trackingActions || liveCheck) && (
          <div className="mt-3 pt-3 border-t border-dashed border-slate-100 space-y-2">
            {priceAlert && (
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
                  {priceAlert.mode === 'percent'
                    ? <Percent className="w-3.5 h-3.5" />
                    : <Tag className="w-3.5 h-3.5" />
                  }
                </span>
                <div className="text-[11px] text-slate-600 leading-tight">
                  <p className="font-bold text-slate-700">
                    {priceAlert.mode === 'percent'
                      ? `When it drops ${priceAlert.percentDrop}%`
                      : `When it drops to ${Number(priceAlert.targetPrice).toLocaleString()} TL`}
                  </p>
                  {priceAlert.mode === 'percent' && priceAlert.targetPrice ? (
                    <p className="text-slate-400">
                      ≈ {Number(priceAlert.targetPrice).toLocaleString()} TL
                    </p>
                  ) : null}
                </div>
              </div>
            )}
            {liveCheck && liveCheck.lowestPrice != null && (() => {
              const prev = liveCheck.previousLowestPrice;
              const curr = liveCheck.lowestPrice;
              const delta = (prev != null && Number.isFinite(prev)) ? curr - prev : null;
              const TrendIcon = delta == null
                ? Minus
                : delta < 0 ? TrendingDown : delta > 0 ? TrendingUp : Minus;
              const trendColor = delta == null
                ? 'text-slate-400 bg-slate-100'
                : delta < 0 ? 'text-emerald-600 bg-emerald-50' : delta > 0 ? 'text-rose-600 bg-rose-50' : 'text-slate-400 bg-slate-100';
              const target = priceAlert?.targetPrice ? Number(priceAlert.targetPrice) : null;
              const targetPct = target && target > 0
                ? Math.min(100, Math.max(0, Math.round((target / curr) * 100)))
                : null;
              return (
                <div className="space-y-1.5 rounded-lg bg-slate-50/60 border border-slate-100 px-2.5 py-2">
                  <div className="flex items-center gap-2">
                    <span className={`w-7 h-7 rounded-lg flex items-center justify-center ${trendColor}`}>
                      <TrendIcon className="w-3.5 h-3.5" />
                    </span>
                    <div className="flex-1 min-w-0 text-[11px] leading-tight">
                      <p className="font-bold text-slate-800 truncate">
                        {Math.round(curr).toLocaleString('en-US')} TL
                        {liveCheck.lowestStore && (
                          <span className="font-medium text-slate-500"> at {liveCheck.lowestStore}</span>
                        )}
                      </p>
                      <p className="text-slate-400 inline-flex items-center gap-1">
                        <Store className="w-3 h-3" />
                        Checked {formatTimeAgo(liveCheck.fetchedAt) || 'just now'}
                        {delta != null && delta !== 0 && (
                          <span className={delta < 0 ? 'text-emerald-600 font-bold' : 'text-rose-600 font-bold'}>
                            {' · '}{delta < 0 ? '−' : '+'}{Math.abs(Math.round(delta)).toLocaleString('en-US')} TL
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  {targetPct != null && (
                    <div>
                      <div className="h-1 rounded-full bg-slate-200 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-primary to-emerald-500 transition-all"
                          style={{ width: `${targetPct}%` }}
                        />
                      </div>
                      <p className="text-[10px] text-slate-400 mt-0.5">
                        Target {Math.round(target).toLocaleString('en-US')} TL · {targetPct}% reached
                      </p>
                    </div>
                  )}
                </div>
              );
            })()}
            {trackingActions && (
              <div className="flex flex-wrap gap-1.5">
                {trackingActions.notify && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-primary/10 text-primary text-[10px] font-bold">
                    <BellRing className="w-3 h-3" /> Notify
                  </span>
                )}
                {trackingActions.autoBuy && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold">
                    <ShoppingBag className="w-3 h-3" /> Auto-Buy
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ProductCard;
