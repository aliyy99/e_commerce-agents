import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ProductAnalysis from './components/ProductAnalysis';
import Profile from './components/Profile';
import PipelineLoader from './components/PipelineLoader';
import ProductCard from './components/ProductCard';
import ChatWidget from './components/ChatWidget';
import TrackModal, { formatDuration } from './components/TrackModal';
import NotificationsDrawer from './components/NotificationsDrawer';
import Campaigns from './components/Campaigns';
import PriceGraphic from './components/PriceGraphic';
import VisionMatchModal from './components/VisionMatchModal';
import { Bell, User, Search, Settings, ChevronDown, LogOut, Heart, UserCircle, Camera, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster, toast } from 'react-hot-toast';
import { sampleProducts, brandModels } from './data/products';
import { analyzeImage } from './services/api';
import { matchProductFromVision, brandKeyFromVision } from './utils/productMatch';
import { filterProducts, findBestProductMatch, buildSuggestions } from './utils/searchMatch';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Search and App State
  const [searchQuery, setSearchQuery] = useState('');
  const [committedQuery, setCommittedQuery] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);

  // Navigation State
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // User Data State
  const [favorites, setFavorites] = useState([]);
  const [tracked, setTracked] = useState([]);
  const [analysisReports, setAnalysisReports] = useState({});
  const [priceHistoryReports, setPriceHistoryReports] = useState({});

  // Track Modal State
  const [trackModalOpen, setTrackModalOpen] = useState(false);
  const [productToTrack, setProductToTrack] = useState(null);

  // Notifications State
  const [notifications, setNotifications] = useState([]);
  const [notifDrawerOpen, setNotifDrawerOpen] = useState(false);
  const notifIdRef = useRef(0);

  const pushNotification = useCallback((notif) => {
    notifIdRef.current += 1;
    setNotifications(prev => [
      { id: `n-${notifIdRef.current}`, createdAt: Date.now(), read: false, ...notif },
      ...prev,
    ]);
  }, []);

  // Vision (image-search) State
  const [visionDisambiguation, setVisionDisambiguation] = useState(null); // { brand, suggestedModels, detected }
  const [visionError, setVisionError] = useState(null);

  const handleImageUpload = (e) => {
    const input = e.target;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.type?.startsWith('image/')) {
      setVisionError('Lütfen geçerli bir görsel dosyası seçin.');
      input.value = '';
      return;
    }

    setVisionError(null);
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setUploadedImage(reader.result);
      } else {
        setVisionError('Görsel okunamadı. Lütfen farklı bir dosya deneyin.');
      }
    };
    reader.onerror = () => {
      setVisionError('Görsel okunamadı. Lütfen tekrar deneyin.');
    };
    reader.readAsDataURL(file);
    input.value = '';
  };

  const finalizeQuery = useCallback((query, { autoSelect = true } = {}) => {
    setSearchQuery(query);
    setCommittedQuery(query);
    setIsSearching(true);
    setShowSuggestions(false);
    if (autoSelect) {
      const match = findBestProductMatch(query, sampleProducts);
      if (match) {
        setSelectedProduct(match);
        setCurrentPage('dashboard');
      }
    }
  }, []);

  const handleSearch = useCallback(async () => {
    if (!searchQuery.trim() && !uploadedImage) {
      setIsSearching(false);
      setCommittedQuery('');
      return;
    }

    setIsRunning(true);
    setVisionError(null);
    setSelectedProduct(null);
    setCurrentPage('dashboard');
    setIsSearching(true);
    setShowSuggestions(false);
    setCommittedQuery(searchQuery);

    // Image-driven path: hand the photo to the Vision Agent (Gemini 3 Flash with Pro fallback).
    if (uploadedImage) {
      try {
        const result = await analyzeImage(uploadedImage, 'tr');

        // Confident catalog hit → jump straight to the product.
        const matched = matchProductFromVision(result, sampleProducts);
        if (matched) {
          setSelectedProduct(matched);
          setSearchQuery(matched.name);
          setIsRunning(false);
          return;
        }

        // Brand recognised but model not pinned down → ask the user.
        const brand = brandKeyFromVision(result, brandModels);
        if (brand) {
          setVisionDisambiguation({
            brand,
            suggestedModels: brandModels[brand] || [],
            detected: result,
          });
          setIsRunning(false);
          return;
        }

        // Nothing decisive — fall back to whatever keywords Vision returned.
        const fallbackQuery = (result.product_name || result.search_keywords || '').trim();
        if (fallbackQuery) {
          finalizeQuery(fallbackQuery, { autoSelect: true });
        } else {
          setVisionError("We couldn't identify the product from the image. Try a different photo or type the name.");
        }
      } catch (err) {
        console.error('Vision analysis failed:', err);
        setVisionError(err?.message || 'Image analysis failed.');
      } finally {
        setIsRunning(false);
      }
      return;
    }

    // Text-only search — keep the existing simulated delay so the skeleton shows.
    setTimeout(() => {
      setIsRunning(false);
    }, 1500);
  }, [searchQuery, uploadedImage, finalizeQuery]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setCommittedQuery('');
    setIsSearching(false);
    setUploadedImage(null);
  };

  const toggleFavorite = (product) => {
    setFavorites(prev => {
      if (prev.find(p => p.id === product.id)) {
        toast.success(`${product.name} favorilerden çıkarıldı.`, {
          icon: '💔',
          style: { borderRadius: '10px', background: '#333', color: '#fff' }
        });
        return prev.filter(p => p.id !== product.id);
      }
      toast.success(`${product.name} favorilere eklendi!`, {
        icon: '❤️',
        style: { borderRadius: '10px', background: '#333', color: '#fff' }
      });
      return [...prev, product];
    });
  };

  const toggleTracked = (product) => {
    const existing = tracked.find(p => p.id === product.id);
    if (existing) {
      setTracked(prev => prev.filter(p => p.id !== product.id));
      toast.success(`${product.name} takipten çıkarıldı`, {
        style: { borderRadius: '10px', background: '#333', color: '#fff' }
      });
      pushNotification({
        type: 'track-removed',
        title: 'Takipten çıkarıldı',
        message: `${product.name} takip listenden kaldırıldı.`,
      });
      return;
    }
    setProductToTrack(product);
    setTrackModalOpen(true);
  };

  const confirmTrack = ({ durationMs, label }) => {
    if (!productToTrack || !durationMs || durationMs <= 0) return;
    const trackingExpiresAt = Date.now() + durationMs;
    const productName = productToTrack.name;
    setTracked(prev => [...prev, { ...productToTrack, trackingExpiresAt }]);
    setTrackModalOpen(false);
    setProductToTrack(null);
    toast.success(`${productName} ${label} boyunca takibe alındı`, {
      style: { borderRadius: '10px', background: '#333', color: '#fff' }
    });
    pushNotification({
      type: 'track-started',
      title: 'Takip başlatıldı',
      message: `${productName} ${label} boyunca takibe alındı.`,
    });
  };

  // Expiry watcher — every 30s, remove expired tracked items and emit notifications.
  useEffect(() => {
    const tick = () => {
      const now = Date.now();
      setTracked(prev => {
        const expired = prev.filter(p => p.trackingExpiresAt && p.trackingExpiresAt <= now);
        if (expired.length === 0) return prev;
        expired.forEach(p => {
          pushNotification({
            type: 'track-expired',
            title: 'Takip süresi doldu',
            message: `${p.name} ürününün takip süresi sona erdi ve listeden çıkarıldı.`,
          });
        });
        return prev.filter(p => !(p.trackingExpiresAt && p.trackingExpiresAt <= now));
      });
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [pushNotification]);

  const markAllNotificationsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);
  const clearAllNotifications = useCallback(() => setNotifications([]), []);
  const removeNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);
  const openNotifDrawer = useCallback(() => {
    setNotifDrawerOpen(true);
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  }, []);

  // Extended product suggestions database (keyword -> related models/products)
  const suggestionDatabase = [
    // Samsung family
    'Samsung Galaxy S24 Ultra',
    'Samsung Galaxy S24+',
    'Samsung Galaxy S23 FE',
    'Samsung Galaxy Z Fold 5',
    'Samsung Galaxy Z Flip 5',
    'Samsung Galaxy Tab S9',
    'Samsung Galaxy Buds2 Pro',
    // Apple / MacBook family
    'MacBook Pro 14" M3',
    'MacBook Pro 16" M3 Max',
    'MacBook Air 15" M3',
    'MacBook Air 13" M4',
    // Apple iPhone
    'iPhone 15 Pro Max',
    'iPhone 15 Pro',
    'iPhone 15',
    'iPhone 14',
    // Apple Watch
    'Apple Watch Series 9',
    'Apple Watch Ultra 2',
    'Apple Watch SE',
    // Sony
    'Sony WH-1000XM5',
    'Sony WH-1000XM4',
    'Sony WF-1000XM5',
    'Sony PlayStation 5',
    'Sony PlayStation 5 Slim',
    'Sony PlayStation Portal',
    // Dyson
    'Dyson V15 Detect',
    'Dyson V12 Detect Slim',
    'Dyson Airwrap',
    'Dyson Supersonic',
    'Dyson Purifier Cool',
    // PlayStation
    'PlayStation 5',
    'PlayStation 5 Slim',
    'PlayStation VR2',
    'PlayStation Portal',
    'PlayStation DualSense Edge',
    // Other popular
    'AirPods Pro 2',
    'AirPods Max',
    'iPad Pro M4',
    'iPad Air M2',
    'Nintendo Switch OLED',
    'Xbox Series X',
    'LG OLED C4 TV',
    'Bose QuietComfort Ultra',
  ];

  const searchSuggestions = useMemo(
    () => buildSuggestions(searchQuery, sampleProducts, suggestionDatabase, 7),
    [searchQuery],
  );

  const displayedProducts = useMemo(() => {
    if (isSearching && committedQuery) {
      return filterProducts(committedQuery, sampleProducts);
    }
    return sampleProducts;
  }, [isSearching, committedQuery]);

  return (
    <div className="min-h-screen bg-background text-slate-900 font-sans selection:bg-primary/20">
      <Toaster position="bottom-right" reverseOrder={false} toastOptions={{ duration: 3000 }} />
      <Sidebar activePage={currentPage} onNavigate={(page) => {
        setCurrentPage(page);
        if (page === 'dashboard') setSelectedProduct(null);
      }} />
      
      <main className="pl-72 relative z-10 transition-all duration-300">
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-100 px-10 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6 flex-1">
            <h2
              style={{ fontFamily: "'Playfair Display', Georgia, serif" }}
              className="text-3xl italic font-black tracking-tight whitespace-nowrap bg-gradient-to-r from-primary via-emerald-500 to-primary bg-clip-text text-transparent drop-shadow-sm"
            >
              Save Your Money
            </h2>
            {currentPage === 'dashboard' && (
            <div className="relative flex items-center gap-2 bg-slate-100 px-4 py-2 rounded-xl border border-slate-200 w-full max-w-xl focus-within:border-primary/50 transition-all group z-50">
              <Search className="w-4 h-4 text-slate-400 group-focus-within:text-primary transition-colors" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setShowSuggestions(e.target.value.length > 0);
                }}
                onFocus={() => setShowSuggestions(searchQuery.length > 0)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
                onKeyDown={handleKeyDown}
                placeholder="Search for a product..."
                className="bg-transparent border-none outline-none text-sm w-full text-slate-900 placeholder:text-slate-400"
              />
              {isSearching && (
                <button onClick={handleClearSearch} className="text-slate-400 hover:text-slate-600 px-2 text-xs font-bold">
                  CLEAR
                </button>
              )}
              <label className="cursor-pointer p-1.5 hover:bg-slate-200 rounded-lg transition-colors text-slate-400 hover:text-primary">
                <Camera className="w-4 h-4" />
                <input
                  type="file"
                  accept="image/*"
                  onClick={(e) => { e.currentTarget.value = ''; }}
                  onChange={handleImageUpload}
                  className="hidden"
                />
              </label>
              {uploadedImage && (
                <div className="relative">
                  <img src={uploadedImage} alt="Uploaded" className="w-7 h-7 rounded-md object-cover border border-primary/30" />
                  <button
                    onClick={() => setUploadedImage(null)}
                    className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-accent-rose text-white rounded-full text-[8px] flex items-center justify-center font-bold"
                  >
                    ✕
                  </button>
                </div>
              )}
              <button 
                onClick={handleSearch}
                disabled={isRunning}
                className={`px-4 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  isRunning 
                    ? 'bg-slate-200 text-slate-400 cursor-not-allowed' 
                    : 'bg-primary text-white hover:bg-primary-hover shadow-sm'
                }`}
              >
                {isRunning ? 'Searching...' : 'Search'}
              </button>

              {/* Autocomplete Suggestions Dropdown */}
              <AnimatePresence>
                {showSuggestions && searchSuggestions.length > 0 && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 10 }}
                    className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-2xl border border-slate-100 py-2 z-50 overflow-hidden"
                  >
                    {searchSuggestions.map((suggestion, idx) => {
                      const q = searchQuery.toLowerCase();
                      const matchIndex = suggestion.toLowerCase().indexOf(q);
                      const before = suggestion.slice(0, matchIndex);
                      const match = suggestion.slice(matchIndex, matchIndex + searchQuery.length);
                      const after = suggestion.slice(matchIndex + searchQuery.length);
                      return (
                        <button
                          key={idx}
                          onClick={() => {
                            setSearchQuery(suggestion);
                            setCommittedQuery(suggestion);
                            setShowSuggestions(false);
                            setIsSearching(true);
                            setIsRunning(true);
                            const match = findBestProductMatch(suggestion, sampleProducts);
                            if (match) {
                              setSelectedProduct(match);
                              setCurrentPage('dashboard');
                            }
                            setTimeout(() => setIsRunning(false), 1500);
                          }}
                          className="w-full text-left px-5 py-2.5 text-sm text-slate-600 hover:bg-slate-50 hover:text-primary transition-colors flex items-center gap-3"
                        >
                          <Search className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                          <span>
                            {before}<span className="font-bold text-slate-900">{match}</span>{after}
                          </span>
                        </button>
                      );
                    })}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            )}
          </div>

          <div className="flex items-center gap-4 ml-6">
            <button
              onClick={openNotifDrawer}
              className="relative p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors border border-transparent hover:border-slate-100"
              aria-label="Bildirimleri aç"
            >
              <Bell className="w-5 h-5" />
              {notifications.filter(n => !n.read).length > 0 && (
                <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 bg-rose-500 text-white text-[10px] font-black rounded-full border-2 border-white flex items-center justify-center">
                  {notifications.filter(n => !n.read).length > 9 ? '9+' : notifications.filter(n => !n.read).length}
                </span>
              )}
            </button>
            <button className="p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors border border-transparent hover:border-slate-100">
              <Settings className="w-5 h-5" />
            </button>
            <div className="h-8 w-px bg-slate-200 mx-2" />
            <div className="relative">
              <button 
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-3 pl-2 pr-1 py-1 rounded-xl hover:bg-slate-50 transition-all border border-transparent hover:border-slate-200 group"
              >
                <div className="text-right hidden sm:block">
                  <p className="text-sm font-black leading-none text-slate-900">Alex Rivera</p>
                  <p className="text-[10px] text-primary font-bold mt-1">Pro Analyst</p>
                </div>
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20 overflow-hidden relative">
                  <User className="w-6 h-6" />
                </div>
                <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${isUserMenuOpen ? 'rotate-180' : ''}`} />
              </button>
              <AnimatePresence>
                {isUserMenuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setIsUserMenuOpen(false)} />
                    <motion.div 
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      className="absolute right-0 mt-3 w-56 glass-card p-2 z-50 border-slate-200 shadow-xl bg-white"
                    >
                      <button 
                        onClick={() => { setCurrentPage('profile'); setIsUserMenuOpen(false); }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all"
                      >
                        <UserCircle className="w-4 h-4" />
                        My Profile
                      </button>
                      <button 
                        onClick={() => { setCurrentPage('favorites'); setIsUserMenuOpen(false); }}
                        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all"
                      >
                        <Heart className="w-4 h-4" />
                        Favorites
                      </button>
                      <div className="h-px bg-slate-100 my-2" />
                      <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-accent-rose hover:bg-accent-rose/5 transition-all font-bold">
                        <LogOut className="w-4 h-4" />
                        Sign Out
                      </button>
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </div>
        </header>

        <div className="px-10 py-8 max-w-[1600px] mx-auto overflow-hidden">
          <AnimatePresence mode="wait">
            {currentPage === 'dashboard' && !selectedProduct && (
              <motion.div 
                key="dashboard-discover"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="space-y-8"
              >
                {isSearching && (
                  <h3 className="text-xl font-black text-slate-900 mb-4">
                    Results for "{committedQuery}" ({displayedProducts.length})
                  </h3>
                )}
                {!isSearching && (
                  <h3 className="text-2xl font-black text-slate-900 mb-6">Featured Products</h3>
                )}

                {isRunning ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {[1,2,3,4].map(i => <div key={i} className="h-80 skeleton rounded-2xl" />)}
                  </div>
                ) : (
                  <div className="space-y-12">
                    {displayedProducts.length > 0 ? (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                        {displayedProducts.map(product => (
                          <ProductCard 
                            key={product.id} 
                            product={product} 
                            onClick={setSelectedProduct}
                            onFavorite={toggleFavorite}
                            onTrack={toggleTracked}
                            isFavorite={favorites.some(f => f.id === product.id)}
                            isTracked={tracked.some(t => t.id === product.id)}
                            analyzedPrice={analysisReports?.[product.id]?.lowestPrice ?? null}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="glass-card p-12 text-center bg-white border-slate-100">
                        <p className="text-slate-500">No products found matching your search.</p>
                      </div>
                    )}

                    {isSearching && (
                      <div className="space-y-6">
                        <div className="flex items-center gap-4">
                          <div className="h-px bg-slate-200 flex-1" />
                          <h3 className="text-sm font-black text-slate-400 uppercase tracking-widest">Alternative Options</h3>
                          <div className="h-px bg-slate-200 flex-1" />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                          {sampleProducts
                            .filter(p => !displayedProducts.find(dp => dp.id === p.id))
                            .slice(0, 4)
                            .map(product => (
                              <ProductCard 
                                key={product.id} 
                                product={product} 
                                onClick={setSelectedProduct}
                                onFavorite={toggleFavorite}
                                onTrack={toggleTracked}
                                isFavorite={favorites.some(f => f.id === product.id)}
                                isTracked={tracked.some(t => t.id === product.id)}
                              />
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </motion.div>
            )}

            {currentPage === 'dashboard' && selectedProduct && (
              <motion.div
                key="dashboard-details"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <button 
                  onClick={() => setSelectedProduct(null)}
                  className="flex items-center gap-2 text-sm font-bold text-slate-500 hover:text-primary transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Go Back
                </button>
                <ProductAnalysis
                  loading={false}
                  product={selectedProduct}
                  onFavorite={() => toggleFavorite(selectedProduct)}
                  onTrack={() => toggleTracked(selectedProduct)}
                  isFavorite={favorites.some(f => f.id === selectedProduct.id)}
                  isTracked={tracked.some(t => t.id === selectedProduct.id)}
                  analysisReports={analysisReports}
                  onAnalysisComplete={(payload) => {
                    setAnalysisReports((prev) =>
                      selectedProduct ? { ...prev, [selectedProduct.id]: payload } : prev
                    );
                  }}
                />
              </motion.div>
            )}

            {currentPage === 'market' && (
              <motion.div key="market" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <PriceGraphic
                  favorites={favorites}
                  tracked={tracked}
                  onFavorite={toggleFavorite}
                  onTrack={toggleTracked}
                  priceHistoryReports={priceHistoryReports}
                  onAnalysisComplete={(productId, report) =>
                    setPriceHistoryReports((prev) => ({ ...prev, [productId]: report }))
                  }
                />
              </motion.div>
            )}

            {currentPage === 'tracked' && (
              <motion.div key="tracked" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                <div className="flex items-center gap-4 border-b border-slate-100 pb-6">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                    <Bell className="w-6 h-6 fill-current" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-display font-black text-slate-900">Tracked Products</h2>
                    <p className="text-slate-500 text-sm font-medium mt-1">
                      {tracked.length} {tracked.length === 1 ? 'product' : 'products'} being tracked
                    </p>
                  </div>
                </div>

                {tracked.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {tracked.map((product, idx) => (
                      <motion.div 
                        key={product.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <ProductCard 
                          product={product} 
                          onClick={(p) => { setSelectedProduct(p); setCurrentPage('dashboard'); }}
                          onFavorite={toggleFavorite}
                          onTrack={toggleTracked}
                          isFavorite={favorites.some(f => f.id === product.id)}
                          isTracked={true}
                          trackingExpiresAt={product.trackingExpiresAt}
                        />
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center justify-center py-20 px-4 text-center bg-white border border-slate-100 rounded-3xl shadow-sm"
                  >
                    <div className="w-24 h-24 mb-6 rounded-full bg-slate-50 flex items-center justify-center">
                      <Bell className="w-10 h-10 text-slate-300" />
                    </div>
                    <h3 className="text-xl font-black text-slate-900 mb-2">No tracked products</h3>
                    <p className="text-slate-500 max-w-md mb-8">
                      Keep an eye on price drops and stock changes by tracking the products you're interested in.
                    </p>
                    <button 
                      onClick={() => setCurrentPage('dashboard')}
                      className="px-6 py-3 bg-primary text-white font-bold rounded-xl shadow-sm hover:bg-primary-hover transition-colors"
                    >
                      Discover Products
                    </button>
                  </motion.div>
                )}
              </motion.div>
            )}

            {currentPage === 'favorites' && (
              <motion.div key="favorites" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                <div className="flex items-center gap-4 border-b border-slate-100 pb-6">
                  <div className="w-12 h-12 rounded-2xl bg-accent-rose/10 flex items-center justify-center text-accent-rose">
                    <Heart className="w-6 h-6 fill-current" />
                  </div>
                  <div>
                    <h2 className="text-3xl font-display font-black text-slate-900">My Favorites</h2>
                    <p className="text-slate-500 text-sm font-medium mt-1">
                      {favorites.length} {favorites.length === 1 ? 'product' : 'products'} saved for later
                    </p>
                  </div>
                </div>

                {favorites.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {favorites.map((product, idx) => (
                      <motion.div 
                        key={product.id}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <ProductCard 
                          product={product} 
                          onClick={(p) => { setSelectedProduct(p); setCurrentPage('dashboard'); }}
                          onFavorite={toggleFavorite}
                          onTrack={toggleTracked}
                          isFavorite={favorites.some(f => f.id === product.id)}
                          isTracked={tracked.some(t => t.id === product.id)}
                        />
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center justify-center py-20 px-4 text-center bg-white border border-slate-100 rounded-3xl shadow-sm"
                  >
                    <div className="w-24 h-24 mb-6 rounded-full bg-slate-50 flex items-center justify-center">
                      <Heart className="w-10 h-10 text-slate-300" />
                    </div>
                    <h3 className="text-xl font-black text-slate-900 mb-2">No favorites yet</h3>
                    <p className="text-slate-500 max-w-md mb-8">
                      Keep track of the products you love by clicking the heart icon on any product card.
                    </p>
                    <button 
                      onClick={() => setCurrentPage('dashboard')}
                      className="px-6 py-3 bg-primary text-white font-bold rounded-xl shadow-sm hover:bg-primary-hover transition-colors"
                    >
                      Discover Products
                    </button>
                  </motion.div>
                )}
              </motion.div>
            )}

            {currentPage === 'profile' && (
              <motion.div key="profile" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}>
                <Profile forceTab="profile" />
              </motion.div>
            )}

            {currentPage === 'campaigns' && (
              <motion.div key="campaigns" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <Campaigns />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Tracking Modal */}
      <TrackModal
        isOpen={trackModalOpen}
        product={productToTrack}
        onClose={() => { setTrackModalOpen(false); setProductToTrack(null); }}
        onConfirm={confirmTrack}
      />

      {/* Notifications Drawer */}
      <NotificationsDrawer
        isOpen={notifDrawerOpen}
        notifications={notifications}
        onClose={() => setNotifDrawerOpen(false)}
        onMarkAllRead={markAllNotificationsRead}
        onClearAll={clearAllNotifications}
        onRemove={removeNotification}
      />

      {/* Gemini-Powered Shopping Assistant */}
      <ChatWidget contextProduct={selectedProduct} />

      {/* Image-search disambiguation */}
      <VisionMatchModal
        isOpen={!!visionDisambiguation}
        brand={visionDisambiguation?.brand}
        suggestedModels={visionDisambiguation?.suggestedModels || []}
        detected={visionDisambiguation?.detected}
        uploadedImage={uploadedImage}
        onClose={() => setVisionDisambiguation(null)}
        onConfirm={(modelName) => {
          setVisionDisambiguation(null);
          finalizeQuery(modelName, { autoSelect: true });
        }}
      />

      {visionError && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[110] bg-white border border-accent-rose/30 shadow-lg rounded-2xl px-5 py-3 text-sm text-slate-700 flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-accent-rose" />
          {visionError}
          <button
            onClick={() => setVisionError(null)}
            className="ml-2 text-xs font-bold text-slate-400 hover:text-slate-700"
          >
            DISMISS
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
