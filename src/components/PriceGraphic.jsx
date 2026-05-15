import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, TrendingUp, TrendingDown, Activity, Zap, ArrowLeft, ExternalLink } from 'lucide-react';
import ProductCard from './ProductCard';
import PriceChart from './PriceChart';
import { sampleProducts } from '../data/products';
import { filterProducts } from '../utils/searchMatch';
import { fetchPriceHistory } from '../services/api';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';

const TREND_META = {
  downward: { label: 'Down', color: 'text-emerald-500', bg: 'bg-emerald-50', border: 'border-emerald-100', Icon: TrendingDown },
  upward:   { label: 'Up', color: 'text-accent-rose', bg: 'bg-rose-50', border: 'border-rose-100', Icon: TrendingUp },
  stable:   { label: 'Stable', color: 'text-slate-600', bg: 'bg-slate-100', border: 'border-slate-200', Icon: Activity },
  volatile: { label: 'Volatile', color: 'text-indigo-500', bg: 'bg-indigo-50', border: 'border-indigo-100', Icon: Activity },
};

const PriceGraphic = ({
  favorites,
  tracked,
  onFavorite,
  onTrack,
  priceHistoryReports,
  onAnalysisComplete,
}) => {
  const [localQuery, setLocalQuery] = useState('');
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);

  const displayedProducts = useMemo(
    () => filterProducts(localQuery, sampleProducts),
    [localQuery],
  );

  const selectedReport = selectedProduct ? priceHistoryReports?.[selectedProduct.id] : null;

  const handleAnalyze = async () => {
    if (!selectedProduct) return;
    setIsAnalyzing(true);
    setError(null);
    try {
      const result = await fetchPriceHistory({
        productName: selectedProduct.name,
        productId: String(selectedProduct.id),
        currency: 'TRY',
        locale: 'en',
      });
      onAnalysisComplete(selectedProduct.id, result);
    } catch (err) {
      console.error('Price history fetch failed', err);
      setError(err?.message || 'Analysis failed.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // ── Detail view ─────────────────────────────────────────────────────────
  if (selectedProduct) {
    const trendMeta = selectedReport
      ? TREND_META[selectedReport.trend] || TREND_META.stable
      : null;
    const productImage = (selectedProduct.images || [])[0] || PRODUCT_IMAGE_FALLBACK;

    return (
      <motion.div
        key="price-graphic-detail"
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -20 }}
        className="space-y-6"
      >
        <button
          onClick={() => { setSelectedProduct(null); setError(null); }}
          className="flex items-center gap-2 text-sm font-bold text-slate-500 hover:text-primary transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Product summary card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="lg:col-span-4 glass-card bg-white p-6 flex flex-col gap-6 h-fit"
          >
            <div className="aspect-square rounded-2xl overflow-hidden bg-slate-50 border border-slate-100 flex items-center justify-center">
              <img
                src={productImage}
                alt={selectedProduct.name}
                onError={(e) => {
                  if (e.currentTarget.dataset.fb === '1') return;
                  e.currentTarget.dataset.fb = '1';
                  e.currentTarget.src = PRODUCT_IMAGE_FALLBACK;
                }}
                className="w-full h-full object-contain p-6 mix-blend-multiply"
              />
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest text-primary">{selectedProduct.brand}</p>
              <h3 className="text-xl font-display font-black text-slate-900 mt-1 leading-tight">{selectedProduct.name}</h3>
            </div>

            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className={`w-full flex items-center justify-center gap-2 px-5 py-3 rounded-xl font-bold text-sm shadow-lg transition-all ${
                isAnalyzing
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  : 'bg-primary text-white hover:bg-primary-dark shadow-primary/20 hover:-translate-y-0.5'
              }`}
            >
              <Zap className={`w-4 h-4 ${isAnalyzing ? 'animate-pulse' : ''}`} />
              {isAnalyzing ? 'Analyzing…' : selectedReport ? 'Re-analyze' : 'Analyze'}
            </button>

            {selectedReport && trendMeta && (
              <div className={`flex items-center justify-between border rounded-xl px-3 py-2 ${trendMeta.bg} ${trendMeta.border}`}>
                <span className="flex items-center gap-2">
                  <trendMeta.Icon className={`w-4 h-4 ${trendMeta.color}`} />
                  <span className={`text-[11px] font-bold uppercase tracking-widest ${trendMeta.color}`}>{trendMeta.label}</span>
                </span>
                <span className="text-[10px] font-black text-slate-400 uppercase tracking-wider">{selectedReport.model_used}</span>
              </div>
            )}
          </motion.div>

          {/* Chart + insight panel */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="lg:col-span-8 space-y-5"
          >
            {error && (
              <div className="bg-white border border-accent-rose/30 rounded-2xl p-5 shadow-sm">
                <p className="text-sm font-bold text-accent-rose">Analysis failed</p>
                <p className="text-xs text-slate-600 leading-relaxed mt-1">{error}</p>
              </div>
            )}

            {!selectedReport && !isAnalyzing && !error && (
              <div className="bg-gradient-to-br from-white via-white to-primary/5 rounded-3xl border border-slate-100 shadow-sm p-12 flex flex-col items-center justify-center min-h-[480px]">
                <div className="relative w-24 h-24 mb-6">
                  <div className="absolute inset-0 rounded-3xl bg-primary/10 rotate-6" />
                  <div className="absolute inset-0 rounded-3xl bg-primary/15 -rotate-6" />
                  <div className="relative w-full h-full rounded-3xl bg-primary text-white flex items-center justify-center shadow-lg shadow-primary/30">
                    <Zap className="w-10 h-10" />
                  </div>
                </div>
                <h3 className="text-2xl font-display font-black text-slate-900 mb-2">Comprehensive Price Analysis</h3>
                <p className="text-sm text-slate-500 max-w-md text-center leading-relaxed">
                  Click <strong className="text-slate-700">Analyze</strong> to generate a 12-month price chart for this product, powered by Gemini 3 Pro and live Google Search data.
                </p>
              </div>
            )}

            {isAnalyzing && !selectedReport && (
              <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-12 flex flex-col items-center justify-center min-h-[480px]">
                <div className="relative w-16 h-16 mb-6">
                  <div className="absolute inset-0 rounded-full border-4 border-primary/15" />
                  <div className="absolute inset-0 rounded-full border-4 border-primary border-t-transparent animate-spin" />
                </div>
                <div className="flex gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: '120ms' }} />
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" style={{ animationDelay: '240ms' }} />
                </div>
              </div>
            )}

            {selectedReport && (
              <>
                <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
                  <PriceChart points={selectedReport.points} currency={selectedReport.currency} />
                </div>

                {selectedReport.sources?.length > 0 && (
                  <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-6">
                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Sources</p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {selectedReport.sources.slice(0, 6).map((src, idx) => (
                        <a
                          key={`${src.uri}-${idx}`}
                          href={src.uri}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="group flex items-center gap-2 px-3 py-2 rounded-xl border border-slate-100 hover:border-primary/40 hover:bg-primary/5 transition-all text-xs text-slate-600 hover:text-primary"
                        >
                          <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                          <span className="truncate">{src.title || src.uri}</span>
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </motion.div>
        </div>
      </motion.div>
    );
  }

  // ── Catalog view ────────────────────────────────────────────────────────
  return (
    <motion.div
      key="price-graphic-catalog"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-primary/10 text-primary rounded-xl flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
          <h2 className="text-3xl font-display font-black text-slate-900">Price Graphic</h2>
        </div>

        <div className="relative flex items-center gap-2 bg-white border border-slate-200 px-4 py-2.5 rounded-xl w-full md:max-w-md focus-within:border-primary/50 transition-colors shadow-sm">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={localQuery}
            onChange={(e) => setLocalQuery(e.target.value)}
            placeholder="Search products…"
            className="bg-transparent border-none outline-none text-sm w-full text-slate-900 placeholder:text-slate-400"
          />
          {localQuery && (
            <button
              onClick={() => setLocalQuery('')}
              className="text-[10px] font-bold text-slate-400 hover:text-slate-700 tracking-widest"
            >
              CLEAR
            </button>
          )}
        </div>
      </div>

      <AnimatePresence mode="popLayout">
        {displayedProducts.length > 0 ? (
          <motion.div
            key="grid"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
          >
            {displayedProducts.map((product) => {
              const report = priceHistoryReports?.[product.id];
              const trendMeta = report ? TREND_META[report.trend] || TREND_META.stable : null;
              return (
                <div key={product.id} className="relative">
                  <ProductCard
                    product={product}
                    onClick={(p) => setSelectedProduct(p)}
                    onFavorite={onFavorite}
                    onTrack={onTrack}
                    isFavorite={favorites.some((f) => f.id === product.id)}
                    isTracked={tracked.some((t) => t.id === product.id)}
                    analyzedPrice={report?.lowest ?? null}
                  />
                  {report && trendMeta && (
                    <div className={`absolute top-3 left-3 flex items-center gap-1.5 px-2.5 py-1 rounded-full ${trendMeta.bg} ${trendMeta.border} border shadow-sm pointer-events-none`}>
                      <trendMeta.Icon className={`w-3 h-3 ${trendMeta.color}`} />
                      <span className={`text-[10px] font-bold uppercase tracking-widest ${trendMeta.color}`}>{trendMeta.label}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-card p-12 text-center bg-white border-slate-100"
          >
            <p className="text-slate-500">No products match your search.</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default PriceGraphic;
