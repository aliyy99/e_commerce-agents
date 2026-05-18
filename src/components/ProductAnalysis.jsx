import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Heart, Bell, Star, Zap, ChevronLeft, ChevronRight, CheckCircle2 } from 'lucide-react';
import { compareProducts } from '../services/api';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';
import { getDefaultVariantSelection, resolveProductVariant } from '../utils/productVariants';
import AnalystReport from './AnalystReport';

const productLinksMapping = {
  "Samsung Galaxy S25 Ultra 512 GB 12 GB Ram": [
    "https://www.hepsiburada.com/samsung-galaxy-s25-ultra-512-gb-12-gb-ram-samsung-turkiye-garantili-siyah-titanyum-p-HBCV00007MIDSU",
    "https://www.trendyol.com/samsung/galaxy-s25-ultra-512-gb-titanyum-siyah-samsung-turkiye-garantili-p-889950721?boutiqueId=61&merchantId=639331",
    "https://www.mediamarkt.com.tr/tr/product/_samsung-galaxys25-ultra-12gb256gb-akilli-telefon-titanyum-1245636.html",
    "https://www.vatanbilgisayar.com/samsung-galaxy-s25-ultra-12-512-gb-akilli-telefon-titanyum-gumus.html"
  ],
  "Samsung Galaxy S24 256 GB 8 GB Ram": [
    "https://www.hepsiburada.com/samsung-galaxy-s24-256-gb-8-gb-ram-samsung-turkiye-garantili-siyah-p-HBCV00005MLJA9",
    "https://www.trendyol.com/samsung/galaxy-s24-256-gb-siyah-p-792775314?boutiqueId=61&merchantId=866772",
    "https://www.mediamarkt.com.tr/tr/product/_samsung-galaxy-s24-8-gb-256-gb-akilli-telefon-siyah-163030835.html"
  ],
  "Apple Macbook Air M4 16 GB 512 GB SSD macOS 13\"": [
    "https://www.hepsiburada.com/apple-macbook-air-m5-16gb-512gb-ssd-macos-13-tasinabilir-bilgisayar-gece-yarisi-mdhe4tu-a-pm-HBC0000D5X0MD",
    "https://www.trendyol.com/apple/13-macbook-air-apple-m4-chip-with-10-core-cpu-and-10-core-gpu-16gb-512gb-ssd-yildiz-isigi-p-904728363?boutiqueId=689770&merchantId=968",
    "https://www.mediamarkt.com.tr/tr/product/_apple-mc7c4tuamacbook-airapple-m4-islemci10-cekirdek-cpu-10-cekirdek-gpu16gb-ram512gb-ssd153sky-blue-1245668.html",
    "https://www.vatanbilgisayar.com/macbook-air-mw133tu-a-m4-16gb-512gb-ssd-liquid-retina-13-6inc-gece-yarisi.html"
  ],
  "Apple iPhone 15 128 GB Mavi": [
    "https://www.hepsiburada.com/apple-iphone-15-128-gb-mavi-p-HBCV00004X9ZCK",
    "https://www.trendyol.com/apple/iphone-15-128-gb-mavi-p-762254881?boutiqueId=61&merchantId=570209",
    "https://www.mediamarkt.com.tr/tr/product/_apple-iphone-15-128-gb-akilli-telefon-mavi-mtp43tua-1232436.html",
    "https://www.vatanbilgisayar.com/iphone-15-128-gb-akilli-telefon-mavi.html"
  ],
  "Samsung Galaxy Tab S11 Ultra 12GB 256GB SM-X930": [
    "https://www.hepsiburada.com/samsung-galaxy-tab-s11-ultra-12gb-256gb-sm-x930-p-HBCV00009UIZ0A",
    "https://www.trendyol.com/samsung/galaxy-tab-s11-ultra-12gb-256gb-gri-tablet-p-978670937?boutiqueId=61&merchantId=1090273",
    "https://www.mediamarkt.com.tr/tr/product/_samsung-galaxy-tab-s11-ultra-sm-x930-146-inc-12-gb-256-gb-tablet-gri-164212346.html",
    "https://www.vatanbilgisayar.com/samsung-galaxy-tab-s11-ultra-14-inc-android-tablet.html"
  ],
  "Samsung Galaxy Buds4 Pro Bluetooth Kulaklık Siyah (ANC)": [
    "https://www.hepsiburada.com/samsung-galaxy-buds4-pro-bluetooth-kulaklik-siyah-anc-p-HBCV0000CWH2BY",
    "https://www.mediamarkt.com.tr/tr/product/_samsung-galaxy-buds4-pro-bluetooth-kulak-ici-kulaklik-siyah-1252511.html",
    "https://www.vatanbilgisayar.com/samsung-galaxy-buds4-pro-anc-kulak-ici-kablosuz-bluetooth-kulaklik-siyah.html"
  ]
};

const ProductAnalysis = ({ loading, product, initialVariantSelection = null, onFavorite, onTrack, isFavorite, isTracked, analysisReports, onAnalysisComplete }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  // Initial selection precedence: caller-provided override (e.g. vision-detected
  // colour) > variant `isDefault` flag > first option in each group.
  const buildInitialSelection = (prod, override) => ({
    ...getDefaultVariantSelection(prod),
    ...(override || {}),
  });
  const [variantSelection, setVariantSelection] = useState(() =>
    buildInitialSelection(product, initialVariantSelection),
  );
  const [analysisError, setAnalysisError] = useState(null);

  useEffect(() => {
    setCurrentImageIndex(0);
    setVariantSelection(buildInitialSelection(product, initialVariantSelection));
    setAnalysisError(null);
    // initialVariantSelection is intentionally part of the dep list — when
    // App.jsx swaps it out (e.g. vision re-runs on the same product) we want
    // to re-apply the new colour.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product, initialVariantSelection]);

  const variantState = useMemo(
    () => resolveProductVariant(product, variantSelection),
    [product, variantSelection],
  );

  // When the user picks a different colour the gallery should snap back to
  // the first image so they immediately see the new colour, not the 4th shot
  // of the previous one.
  const variantImagesKey = (variantState.images || []).join('|');
  useEffect(() => {
    setCurrentImageIndex(0);
  }, [variantImagesKey]);

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

  const { id: productId } = product;
  const productName = variantState.displayName || product.name;
  const resolvedSpecs = variantState.specs;
  // Variant-aware images: each colour option can carry its own gallery; if
  // the active variant set provides one, use it instead of the base product
  // images. This is what makes "click Pink → see the pink phone".
  const variantImages = (variantState.images || product.images || [])
    .filter((image) => typeof image === 'string' && image.trim());
  const resolvedProductImages = variantImages.length > 0 ? variantImages : [PRODUCT_IMAGE_FALLBACK];
  const variantAveragePrice = (() => {
    const prices = (variantState.stores || [])
      .map((s) => Number(s?.price))
      .filter((p) => Number.isFinite(p) && p > 0);
    if (prices.length === 0) return null;
    return prices.reduce((a, b) => a + b, 0) / prices.length;
  })();
  const analysisPayload = analysisReports?.[productId];
  const deepAnalysis = analysisPayload?.deepAnalysis || null;
  const analysisModel = analysisPayload?.modelUsed || null;
  const analyzedLowestPrice = analysisPayload?.lowestPrice ?? null;
  const analyzedLowestSite = analysisPayload?.lowestSite || null;

  const handleNextImage = () => {
    setCurrentImageIndex((prev) => (prev + 1) % resolvedProductImages.length);
  };

  const handlePrevImage = () => {
    setCurrentImageIndex((prev) => (prev - 1 + resolvedProductImages.length) % resolvedProductImages.length);
  };

  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      let links = [];
      // Link mapping is keyed by the base catalog name; variant-applied
      // display names may differ ("… 1 TB 12 GB Ram"), so look up by base.
      if (productLinksMapping[product.name]) {
        links = productLinksMapping[product.name];
      } else if (productLinksMapping[productName]) {
        links = productLinksMapping[productName];
      } else {
        links = (product?.stores || [])
          .map((store) => store?.url || '')
          .filter((url) => /^https?:\/\//i.test(url));
      }

      if (links.length === 0) {
        throw new Error('No predefined links found for this product.');
      }

      const productsData = links.map((url) => {
        let siteName = 'Unknown';
        try {
          const hostname = new URL(url).hostname.replace(/^www\./i, '');
          siteName = hostname.split('.')[0] || hostname;
        } catch {
          siteName = 'Unknown';
        }

        return {
          site: siteName.charAt(0).toUpperCase() + siteName.slice(1),
          url,
          product_name: productName,
        };
      });

      const result = await compareProducts(productsData);
      if (!result?.deep_analysis) {
        throw new Error('Backend did not return a valid analysis report.');
      }
      onAnalysisComplete({
        deepAnalysis: result.deep_analysis,
        modelUsed: result.model_used || null,
        lowestPrice: result.lowest_price ?? null,
        lowestSite: result.lowest_price_site ?? null,
        storePrices: result.store_prices ?? [],
      });
    } catch (err) {
      console.error(err);
      const message = err instanceof Error ? err.message : 'An unexpected error occurred during analysis.';
      setAnalysisError(message);
    } finally {
      setIsAnalyzing(false);
    }
  };

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
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="lg:col-span-4 glass-card p-6 flex flex-col gap-8 h-fit bg-white"
      >
        <div className="relative group">
          <div className="aspect-square rounded-2xl overflow-hidden border border-slate-100 relative bg-slate-50">
            <AnimatePresence mode="wait">
              <motion.img
                key={currentImageIndex}
                src={resolvedProductImages[currentImageIndex]}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
                alt={`${productName} - Image ${currentImageIndex + 1}`}
                onError={(e) => {
                  if (e.currentTarget.dataset.fallbackApplied === 'true') return;
                  e.currentTarget.dataset.fallbackApplied = 'true';
                  e.currentTarget.src = PRODUCT_IMAGE_FALLBACK;
                }}
                className="w-full h-full object-contain mix-blend-multiply p-4"
              />
            </AnimatePresence>
            
            {resolvedProductImages.length > 1 && (
            <>
                <button 
                  onClick={handlePrevImage}
                  className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white/80 backdrop-blur shadow-sm flex items-center justify-center text-slate-700 hover:bg-white hover:text-primary transition-colors z-10"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button 
                  onClick={handleNextImage}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-white/80 backdrop-blur shadow-sm flex items-center justify-center text-slate-700 hover:bg-white hover:text-primary transition-colors z-10"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
                <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5 z-10 bg-white/60 backdrop-blur-md px-3 py-1.5 rounded-full">
                  {resolvedProductImages.map((_, idx) => (
                    <button
                      key={idx}
                      onClick={() => setCurrentImageIndex(idx)}
                      className={`w-1.5 h-1.5 rounded-full transition-all ${idx === currentImageIndex ? 'bg-primary w-3' : 'bg-slate-300'}`}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
          <div className="absolute top-4 right-4 flex flex-col gap-2 z-20">
            <button
              onClick={onFavorite}
              className={`w-10 h-10 rounded-full flex items-center justify-center shadow-md transition-all ${isFavorite ? 'bg-accent-rose text-white' : 'bg-white text-slate-400 hover:text-accent-rose'}`}
            >
              <Heart className="w-5 h-5" fill={isFavorite ? 'currentColor' : 'none'} />
            </button>
            <button
              onClick={onTrack}
              className={`w-10 h-10 rounded-full flex items-center justify-center shadow-md transition-all ${isTracked ? 'bg-primary text-white' : 'bg-white text-slate-400 hover:text-primary'}`}
            >
              <Bell className="w-5 h-5" fill={isTracked ? 'currentColor' : 'none'} />
            </button>
          </div>
        </div>

        <div className="mt-2">
          <h3 className="text-2xl font-display font-black text-slate-900">{productName}</h3>
          <p className="text-sm text-slate-500 mt-2 leading-relaxed">{product.description}</p>
        </div>

        {product.variants?.length > 0 && (
          <div className="mt-2 space-y-4">
            <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-2">
              Options
            </h4>
            <div className="space-y-4">
              {product.variants.map((group) => {
                const active = variantSelection[group.label];
                const isColorGroup = (group.label || '').toLowerCase() === 'color';
                return (
                  <div key={group.label}>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">
                        {group.label}
                      </p>
                      <p className="text-[11px] font-black text-slate-700">{active}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {group.options.map((opt) => {
                        const isActive = active === opt.shortValue;
                        return (
                          <button
                            key={opt.shortValue}
                            onClick={() =>
                              setVariantSelection((prev) => ({
                                ...prev,
                                [group.label]: opt.shortValue,
                              }))
                            }
                            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold border transition-all ${
                              isActive
                                ? 'bg-primary text-white border-primary shadow-sm'
                                : 'bg-white text-slate-600 border-slate-200 hover:border-primary/60 hover:text-primary'
                            }`}
                          >
                            {isColorGroup && opt.swatch && (
                              <span
                                className={`w-3.5 h-3.5 rounded-full border ${isActive ? 'border-white/70' : 'border-slate-300'}`}
                                style={{ background: opt.swatch }}
                                aria-hidden="true"
                              />
                            )}
                            <span>{opt.shortValue}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
            {variantAveragePrice != null && (
              <div className="flex items-center justify-between bg-primary/5 border border-primary/15 rounded-xl px-3 py-2 mt-2">
                <span className="text-[11px] font-bold text-primary uppercase tracking-widest">
                  Average Market Price
                </span>
                <span className="text-base font-black text-slate-900">
                  {Math.round(variantAveragePrice).toLocaleString('en-US')} TL
                </span>
              </div>
            )}
            {analyzedLowestPrice != null && (
              <div className="flex items-center justify-between bg-emerald-50 border border-emerald-100 rounded-xl px-3 py-2">
                <span className="text-[11px] font-bold text-emerald-600 uppercase tracking-widest">
                  Analyzed Lowest{analyzedLowestSite ? ` · ${analyzedLowestSite}` : ''}
                </span>
                <span className="text-base font-black text-slate-900">
                  {Math.round(analyzedLowestPrice).toLocaleString('en-US')} TL
                </span>
              </div>
            )}
          </div>
        )}

        {resolvedSpecs && (
          <div className="mt-4 space-y-4">
            <h4 className="text-xs font-black text-slate-400 uppercase tracking-widest border-b border-slate-100 pb-2">Technical Details</h4>
            <div className="grid grid-cols-1 gap-3">
              {resolvedSpecs.map((spec) => (
                <div key={spec.label} className="flex justify-between items-center py-1.5 border-b border-slate-50 last:border-0 hover:bg-slate-50 px-2 rounded-lg transition-colors">
                  <span className="text-[11px] font-bold text-slate-500">{spec.label}</span>
                  <span className="text-[11px] font-black text-slate-800 text-right ml-4">{spec.value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="lg:col-span-8 flex flex-col gap-6 bg-slate-50/50 rounded-2xl border border-dashed border-slate-200 relative min-h-[800px] p-6"
      >
        <div className="absolute top-6 right-6 z-10">
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm shadow-lg transition-all ${isAnalyzing ? 'bg-slate-300 text-slate-500 cursor-not-allowed' : 'bg-primary text-white hover:bg-primary-dark shadow-primary/20 hover:-translate-y-0.5'}`}
          >
            <Zap className={`w-4 h-4 ${isAnalyzing ? 'animate-pulse' : ''}`} />
            {isAnalyzing ? 'Analyzing...' : 'Analyze'}
          </button>
        </div>

        {analysisError ? (
          <div className="bg-white border border-accent-rose/30 rounded-2xl p-8 shadow-sm mt-14">
            <h3 className="text-lg font-bold text-accent-rose mb-2">Analysis failed</h3>
            <p className="text-sm text-slate-600 leading-relaxed mb-4">{analysisError}</p>
            <p className="text-xs text-slate-400">
              Check that the backend service is running and verify your network connection, then try again.
            </p>
            <button
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className="mt-4 px-4 py-2 rounded-lg bg-primary text-white text-xs font-bold hover:bg-primary-hover disabled:opacity-50"
            >
              Try Again
            </button>
          </div>
        ) : isAnalyzing && !deepAnalysis ? (
          <div className="mt-14 rounded-3xl bg-gradient-to-br from-slate-50 to-white border border-slate-100 p-10 text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  animate={{ y: [0, -10, 0] }}
                  transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }}
                  className="w-3 h-3 rounded-full bg-primary"
                />
              ))}
            </div>
            <h3 className="font-display text-xl font-black text-slate-900">
              The Analyst Agent is reading every review…
            </h3>
            <p className="text-sm text-slate-500 mt-2 max-w-md mx-auto">
              Detecting blind spots, clustering chronic complaints, filtering suspicious reviews and writing an honest verdict.
            </p>
          </div>
        ) : deepAnalysis ? (
          <div className="mt-14">
            <AnalystReport analysis={deepAnalysis} modelUsed={analysisModel} />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center p-12 h-full bg-white rounded-2xl border border-slate-100 shadow-sm mt-14">
            <div className="w-20 h-20 bg-primary/5 text-primary rounded-3xl flex items-center justify-center mx-auto mb-6 transform rotate-3">
              <Zap className="w-10 h-10 -rotate-3" />
            </div>
            <h3 className="text-2xl font-display font-black text-slate-900 mb-3">Comprehensive Product Analysis</h3>
            <p className="text-slate-500 text-sm max-w-md mx-auto leading-relaxed">
              Click <strong>Analyze</strong> to run the Analyst Agent. It scans every site, filters suspicious reviews, surfaces blind spots and chronic issues, and writes an honest pros/cons verdict.
            </p>
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default ProductAnalysis;
