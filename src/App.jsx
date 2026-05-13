import React, { useState, useCallback, useMemo } from 'react';
import Sidebar from './components/Sidebar';
import ProductAnalysis from './components/ProductAnalysis';
import Profile from './components/Profile';
import PipelineLoader from './components/PipelineLoader';
import ProductCard from './components/ProductCard';
import ChatWidget from './components/ChatWidget';
import Campaigns from './components/Campaigns';
import { Bell, User, Search, Settings, ChevronDown, LogOut, Heart, UserCircle, Camera, ArrowLeft, TrendingUp } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { sampleProducts } from './data/products';

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  // Search and App State
  const [searchQuery, setSearchQuery] = useState('');
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

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      setUploadedImage(event.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleSearch = useCallback(() => {
    if (!searchQuery.trim() && !uploadedImage) {
      setIsSearching(false);
      return;
    }

    setIsRunning(true);
    setSelectedProduct(null);
    setCurrentPage('dashboard');
    setIsSearching(true);
    setShowSuggestions(false);
    
    // Simulate search delay
    setTimeout(() => {
      setIsRunning(false);
    }, 1500);
  }, [searchQuery, uploadedImage]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setIsSearching(false);
    setUploadedImage(null);
  };

  const toggleFavorite = (product) => {
    setFavorites(prev => {
      if (prev.find(p => p.id === product.id)) {
        return prev.filter(p => p.id !== product.id);
      }
      return [...prev, product];
    });
  };

  const toggleTracked = (product) => {
    setTracked(prev => {
      if (prev.find(p => p.id === product.id)) {
        return prev.filter(p => p.id !== product.id);
      }
      return [...prev, product];
    });
  };

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

  const searchSuggestions = useMemo(() => {
    if (!searchQuery || searchQuery.length < 2) return [];
    const q = searchQuery.toLowerCase();
    return suggestionDatabase
      .filter(s => s.toLowerCase().includes(q) && s.toLowerCase() !== q)
      .slice(0, 7);
  }, [searchQuery]);

  const displayedProducts = useMemo(() => {
    if (isSearching && searchQuery) {
      return sampleProducts.filter(p => p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.description.toLowerCase().includes(searchQuery.toLowerCase()));
    }
    return sampleProducts;
  }, [isSearching, searchQuery]);

  return (
    <div className="min-h-screen bg-background text-slate-900 font-sans selection:bg-primary/20">
      <Sidebar activePage={currentPage} onNavigate={(page) => {
        setCurrentPage(page);
        if (page === 'dashboard') setSelectedProduct(null);
      }} />
      
      <main className="pl-72 relative z-10 transition-all duration-300">
        <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-md border-b border-slate-100 px-10 py-4 flex items-center justify-between">
          <div className="flex items-center gap-6 flex-1">
            <h2 className="text-lg font-black text-slate-900 tracking-tight capitalize whitespace-nowrap min-w-[160px]">
              {currentPage === 'dashboard' && (selectedProduct ? 'Product Details' : 'Discover')}
              {currentPage === 'campaigns' && 'Campaigns'}
              {currentPage === 'market' && 'Global Trends'}
              {currentPage === 'tracked' && 'Tracked Products'}
              {currentPage === 'favorites' && 'Favorites'}
              {currentPage === 'profile' && 'Profile'}
            </h2>
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
                placeholder="Search for a product or paste a link..." 
                className="bg-transparent border-none outline-none text-sm w-full text-slate-900 placeholder:text-slate-400"
              />
              {isSearching && (
                <button onClick={handleClearSearch} className="text-slate-400 hover:text-slate-600 px-2 text-xs font-bold">
                  CLEAR
                </button>
              )}
              <label className="cursor-pointer p-1.5 hover:bg-slate-200 rounded-lg transition-colors text-slate-400 hover:text-primary">
                <Camera className="w-4 h-4" />
                <input type="file" accept="image/*" onChange={handleImageUpload} className="hidden" />
              </label>
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
                            setShowSuggestions(false);
                            setIsSearching(true);
                            setIsRunning(true);
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
          </div>

          <div className="flex items-center gap-4 ml-6">
            {uploadedImage && (
              <div className="relative">
                <img src={uploadedImage} alt="Uploaded" className="w-10 h-10 rounded-lg object-cover border-2 border-primary/30" />
                <button 
                  onClick={() => setUploadedImage(null)} 
                  className="absolute -top-1 -right-1 w-4 h-4 bg-accent-rose text-white rounded-full text-[8px] flex items-center justify-center font-bold"
                >
                  ✕
                </button>
              </div>
            )}
            <button className="relative p-2.5 text-slate-500 hover:bg-slate-100 rounded-xl transition-colors border border-transparent hover:border-slate-100">
              <Bell className="w-5 h-5" />
              {tracked.length > 0 && <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-primary rounded-full border-2 border-white" />}
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
                    Results for "{searchQuery}" ({displayedProducts.length})
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
                  onAnalysisComplete={(report) => {
                    setAnalysisReports((prev) =>
                      selectedProduct ? { ...prev, [selectedProduct.id]: report } : prev
                    );
                  }}
                />
              </motion.div>
            )}

            {currentPage === 'market' && (
              <motion.div key="market" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                <h2 className="text-3xl font-display font-black text-slate-900">Global Market Trends</h2>
                <div className="grid grid-cols-3 gap-6">
                  {[1, 2, 3].map(i => (
                    <div key={i} className="glass-card p-8 bg-white border-slate-100">
                      <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center text-primary mb-6">
                        <TrendingUp className="w-6 h-6" />
                      </div>
                      <h3 className="text-xl font-bold mb-2">Trend Analysis #{i}</h3>
                      <p className="text-sm text-slate-500 mb-6">Market is shifting towards sustainable tech integration.</p>
                      <button className="text-xs font-black text-primary uppercase tracking-widest">Read Report</button>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {currentPage === 'tracked' && (
              <motion.div key="tracked" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                <h2 className="text-3xl font-display font-black text-slate-900">Tracked Products</h2>
                {tracked.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {tracked.map(product => (
                      <ProductCard 
                        key={product.id} 
                        product={product} 
                        onClick={(p) => { setSelectedProduct(p); setCurrentPage('dashboard'); }}
                        onFavorite={toggleFavorite}
                        onTrack={toggleTracked}
                        isFavorite={favorites.some(f => f.id === product.id)}
                        isTracked={tracked.some(t => t.id === product.id)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="glass-card p-12 text-center bg-white border-slate-100">
                    <p className="text-slate-500">You haven't tracked any products yet.</p>
                  </div>
                )}
              </motion.div>
            )}

            {currentPage === 'favorites' && (
              <motion.div key="favorites" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
                <h2 className="text-3xl font-display font-black text-slate-900">Favorites</h2>
                {favorites.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {favorites.map(product => (
                      <ProductCard 
                        key={product.id} 
                        product={product} 
                        onClick={(p) => { setSelectedProduct(p); setCurrentPage('dashboard'); }}
                        onFavorite={toggleFavorite}
                        onTrack={toggleTracked}
                        isFavorite={favorites.some(f => f.id === product.id)}
                        isTracked={tracked.some(t => t.id === product.id)}
                      />
                    ))}
                  </div>
                ) : (
                  <div className="glass-card p-12 text-center bg-white border-slate-100">
                    <p className="text-slate-500">You haven't added any products to your favorites yet.</p>
                  </div>
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

      {/* Gemini-Powered Shopping Assistant */}
      <ChatWidget contextProduct={selectedProduct} />
    </div>
  );
}

export default App;
