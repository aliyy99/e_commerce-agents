import React, { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Landing from './components/Landing';
import ProductAnalysis from './components/ProductAnalysis';
import Profile from './components/Profile';
import PipelineLoader from './components/PipelineLoader';
import ProductCard from './components/ProductCard';
import ChatWidget from './components/ChatWidget';
import TrackModal, { formatDuration } from './components/TrackModal';
import NotificationsDrawer from './components/NotificationsDrawer';
import Campaigns from './components/Campaigns';
import PriceGraphic from './components/PriceGraphic';
import Orders from './components/Orders';
import DeviceCompare from './components/DeviceCompare';
import VisionMatchModal from './components/VisionMatchModal';
import DiscoverFilters from './components/DiscoverFilters';
import { Bell, User, Search, Settings, ChevronDown, LogOut, Heart, UserCircle, Camera, ArrowLeft, Compass, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { Toaster, toast } from 'react-hot-toast';
import { sampleProducts, brandModels } from './data/products';
import { analyzeImage, checkTrackedPrices } from './services/api';
import { matchProductFromVision, brandKeyFromVision, pickInitialVariantSelection } from './utils/productMatch';
import { filterProducts, findBestProductMatch, buildSuggestions } from './utils/searchMatch';
import {
  applyDiscoverFilters,
  extractFilterOptions,
  EMPTY_DISCOVER_FILTERS,
} from './utils/productFilters';

function App() {
  // Show the marketing/login landing on every fresh load. The user lands
  // here, clicks Log In (or Continue as Guest), and only then sees the dashboard.
  const [hasEnteredApp, setHasEnteredApp] = useState(false);
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
  // When vision matches a product AND detects a colour, we pre-set the
  // variant selection so opening the detail page lands on the exact colour
  // the user uploaded (instead of the catalog default).
  const [visionVariantOverride, setVisionVariantOverride] = useState(null);

  // Latest device comparison — kept around so the ChatWidget can answer
  // follow-up questions about it ("which is better for gaming?", etc.).
  const [latestComparison, setLatestComparison] = useState(null);

  // History of every comparison the user has run, keyed by the unordered
  // device-pair so re-running A↔B doesn't create a duplicate entry. Lives at
  // the App level (not inside DeviceCompare) so the results survive page
  // changes and unmounts — same pattern as `priceHistoryReports`.
  const [comparisonHistory, setComparisonHistory] = useState({});
  const recordComparison = useCallback((payload) => {
    if (!payload?.deviceA?.id || !payload?.deviceB?.id || !payload.report) return;
    const [low, high] = [payload.deviceA.id, payload.deviceB.id].sort((a, b) => a - b);
    const key = `${low}__${high}`;
    setComparisonHistory((prev) => ({
      ...prev,
      [key]: { ...payload, savedAt: Date.now() },
    }));
    setLatestComparison(payload);
  }, []);
  const removeComparison = useCallback((key) => {
    setComparisonHistory((prev) => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }, []);

  // Latest campaigns snapshot (coupons + tech news) — kept here so the chat
  // assistant can answer questions like "hangi kuponları kullanabilirim?" or
  // "iPhone'da indirim var mı?" without re-running the search.
  const [campaignsData, setCampaignsData] = useState(null);

  // Discover (Keşfet) page filter state — driven by the left sidebar chips.
  const [discoverFilters, setDiscoverFilters] = useState(EMPTY_DISCOVER_FILTERS);
  const filterOptions = useMemo(() => extractFilterOptions(sampleProducts), []);
  const resetDiscoverFilters = useCallback(() => {
    setDiscoverFilters(EMPTY_DISCOVER_FILTERS);
  }, []);

  const handleImageUpload = (e) => {
    const input = e.target;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.type?.startsWith('image/')) {
      setVisionError('Please choose a valid image file.');
      input.value = '';
      return;
    }

    setVisionError(null);
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === 'string') {
        setUploadedImage(reader.result);
      } else {
        setVisionError('Could not read the image. Please try a different file.');
      }
    };
    reader.onerror = () => {
      setVisionError('Could not read the image. Please try again.');
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

    // Image-driven path: hand the photo to the Vision Agent (Pro → Flash cascade).
    if (uploadedImage) {
      try {
        const result = await analyzeImage(uploadedImage, 'tr');
        const confidence = typeof result.confidence === 'number' ? result.confidence : 0;

        // Hard fail: model couldn't see a product at all. No point searching.
        if (confidence < 0.3 && !result.product_name && !result.brand) {
          setVisionError(
            "We couldn't identify the product from the image. Try a clearer photo or type the product name.",
          );
          setIsRunning(false);
          return;
        }

        // Confident catalog hit → jump straight to the product. (Match helper
        // already enforces brand parity + token-overlap + min confidence.)
        const matched = matchProductFromVision(result, sampleProducts);
        if (matched) {
          const colorSelection = pickInitialVariantSelection(matched, result);
          // Bind the override to the matched product's id so navigating to a
          // different product later doesn't accidentally re-apply this colour.
          setVisionVariantOverride(
            colorSelection ? { productId: matched.id, selection: colorSelection } : null,
          );
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

        // Vision gave us a product name but it didn't pass our catalog filter
        // → use it as a search query instead of force-selecting a wrong row.
        const fallbackQuery = (result.product_name || result.search_keywords || result.brand || '').trim();
        if (fallbackQuery) {
          finalizeQuery(fallbackQuery, { autoSelect: false });
        } else {
          setVisionError(
            "We couldn't identify the product from the image. Try a different photo or type the product name.",
          );
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
        toast.success(`${product.name} removed from favorites.`, {
          icon: '💔',
          style: { borderRadius: '10px', background: '#333', color: '#fff' }
        });
        return prev.filter(p => p.id !== product.id);
      }
      toast.success(`${product.name} added to favorites!`, {
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
      toast.success(`${product.name} untracked`, {
        style: { borderRadius: '10px', background: '#333', color: '#fff' }
      });
      pushNotification({
        type: 'track-removed',
        title: 'Untracked',
        message: `${product.name} was removed from your tracking list.`,
      });
      return;
    }
    setProductToTrack(product);
    setTrackModalOpen(true);
  };

  const confirmTrack = ({ durationMs, label, priceAlert, actions }) => {
    if (!productToTrack || !durationMs || durationMs <= 0) return;
    const trackingExpiresAt = Date.now() + durationMs;
    const productName = productToTrack.name;
    const trackingActions = actions || { notify: true, autoBuy: false };
    setTracked(prev => [
      ...prev,
      {
        ...productToTrack,
        trackingExpiresAt,
        priceAlert: priceAlert || null,
        trackingActions,
      },
    ]);
    setTrackModalOpen(false);
    setProductToTrack(null);
    toast.success(`${productName} is being tracked for ${label}`, {
      style: { borderRadius: '10px', background: '#333', color: '#fff' }
    });
    pushNotification({
      type: 'track-started',
      title: 'Tracking started',
      message: `${productName} is being tracked for ${label}.`,
    });

    // Immediate auto-buy: if the user enabled auto-buy AND the catalog already
    // has a store at/below the target, fire the purchase right now without
    // waiting for the rotating poller to hit this item. Source = 'baseline' so
    // we can tell instant buys from live-check-triggered ones in the order log.
    if (priceAlert && trackingActions.autoBuy) {
      const baseStores = (productToTrack.stores || [])
        .map((s) => ({ name: s?.name, price: Number(s?.price) }))
        .filter((s) => Number.isFinite(s.price) && s.price > 0);
      if (baseStores.length > 0) {
        const cheapest = baseStores.reduce((min, s) => (s.price < min.price ? s : min), baseStores[0]);
        const target = priceAlert.mode === 'target'
          ? Number(priceAlert.targetPrice)
          : priceAlert.targetPrice
            ? Number(priceAlert.targetPrice)
            : null;
        if (target != null && cheapest.price <= target) {
          // Defer one tick so the tracked state is committed before the
          // executeAutoBuy guard reads it.
          setTimeout(
            () => executeAutoBuy(
              { ...productToTrack },
              { store: cheapest.name, price: cheapest.price, source: 'baseline' },
            ),
            0,
          );
        }
      }
    }
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
            title: 'Tracking expired',
            message: `${p.name} tracking has ended and the product was removed from your list.`,
          });
        });
        return prev.filter(p => !(p.trackingExpiresAt && p.trackingExpiresAt <= now));
      });
    };
    tick();
    const id = setInterval(tick, 30000);
    return () => clearInterval(id);
  }, [pushNotification]);

  // ── Auto-buy orders ─────────────────────────────────────────────────────
  // Orders generated by the auto-buy flow (tracked product crosses target +
  // user opted into auto-buy). The Orders page prepends these to its seed
  // mock list so a fresh purchase shows up at the top instantly.
  const [orders, setOrders] = useState([]);
  const orderSeqRef = useRef(0);
  const executeAutoBuy = useCallback((product, { store, price, source = 'live-check' }) => {
    // Guard: don't double-buy the same tracked product. We mark the tracked
    // entry as autoBoughtAt; if already set, skip.
    const already = trackedRef.current?.find?.((p) => p.id === product.id)?.autoBoughtAt;
    if (already) return;

    orderSeqRef.current += 1;
    const baselineAvg = (() => {
      const ps = (product.stores || []).map((s) => Number(s?.price)).filter((p) => Number.isFinite(p) && p > 0);
      if (!ps.length) return null;
      return Math.round(ps.reduce((a, b) => a + b, 0) / ps.length);
    })();
    const order = {
      id: `TT-AUTO-${Date.now()}-${orderSeqRef.current}`,
      productName: product.name,
      image: (product.images && product.images[0]) || null,
      store: store || 'Auto-Buy',
      price: Math.round(Number(price)) || null,
      originalPrice: baselineAvg,
      purchasedAt: new Date().toISOString(),
      status: 'processing',
      method: 'auto-buy',
      eta: 'Confirmation pending',
      source,
    };
    setOrders((prev) => [order, ...prev]);

    // Flag the tracked entry so the polling loop doesn't re-fire on the next tick.
    setTracked((prev) =>
      prev.map((p) => (p.id === product.id ? { ...p, autoBoughtAt: Date.now() } : p)),
    );

    toast.success(
      `Auto-buy executed: ${product.name} at ${Math.round(price).toLocaleString('en-US')} TL from ${store || 'best store'}`,
      { duration: 7000, icon: '🛒', style: { borderRadius: '10px', background: '#0f172a', color: '#fff' } },
    );
    pushNotification({
      type: 'auto-buy',
      title: 'Auto-buy executed',
      message: `${product.name} purchased from ${store || 'cheapest store'} at ${Math.round(price).toLocaleString('en-US')} TL. See Orders page for status.`,
    });
  }, [pushNotification]);

  // ── Live price tracker ──────────────────────────────────────────────────
  // Per-product live-price snapshot (filled in by the rotating poller below).
  // Shape: { [productId]: { fetchedAt, stores:[{site,price,url,...}], lowestStore, lowestPrice, previousLowestPrice, alertFiredAt } }
  const [trackingChecks, setTrackingChecks] = useState({});
  // Hold a ref to the tick function so the interval can call the *latest*
  // closure without re-arming every time `tracked` changes (which would
  // restart the cadence and starve the rotation).
  const trackedRef = useRef(tracked);
  useEffect(() => { trackedRef.current = tracked; }, [tracked]);
  const checksRef = useRef(trackingChecks);
  useEffect(() => { checksRef.current = trackingChecks; }, [trackingChecks]);

  const evaluatePriceAlert = useCallback((product, lowestPrice, lowestStore, previousLowestPrice, existingAlertFiredAt) => {
    const alert = product.priceAlert;
    if (!alert || lowestPrice == null) return null;

    let target = null;
    if (alert.mode === 'target' && Number.isFinite(Number(alert.targetPrice))) {
      target = Number(alert.targetPrice);
    } else if (alert.mode === 'percent' && Number.isFinite(Number(alert.percentDrop))) {
      // Base the percent off the catalog average so the threshold is stable
      // even if a single store happens to be cheap on a given tick.
      const basePrices = (product.stores || [])
        .map((s) => Number(s?.price))
        .filter((p) => Number.isFinite(p) && p > 0);
      if (basePrices.length > 0) {
        const baseAvg = basePrices.reduce((a, b) => a + b, 0) / basePrices.length;
        target = baseAvg * (1 - Number(alert.percentDrop) / 100);
      }
    }
    if (target == null || !(lowestPrice <= target)) return null;

    // Only fire once per crossing — don't keep nagging the user every tick.
    // Re-arm only when the price has gone back ABOVE the target since the last
    // firing (tracked via previousLowestPrice > target).
    if (existingAlertFiredAt && (previousLowestPrice == null || previousLowestPrice <= target)) {
      return null;
    }

    return { target, store: lowestStore, price: lowestPrice };
  }, []);

  const checkSingleTracked = useCallback(async (product) => {
    const stores = (product.stores || []).filter((s) => /^https?:\/\//i.test(s?.url || ''));
    if (stores.length === 0) return; // Nothing to scrape; skip silently.

    let payload;
    try {
      payload = await checkTrackedPrices({
        productName: product.name,
        stores: stores.map((s) => ({ site: s.name, url: s.url })),
      });
    } catch (err) {
      // Network / backend down — don't spam the UI. Just log and move on.
      console.warn('Tracker check failed for', product.name, err?.message || err);
      return;
    }

    const lowestPrice = payload?.lowest_price ?? null;
    const lowestStore = payload?.lowest_site ?? null;
    const previousLowestPrice = checksRef.current?.[product.id]?.lowestPrice ?? null;
    const previousAlertFiredAt = checksRef.current?.[product.id]?.alertFiredAt ?? null;
    const trigger = evaluatePriceAlert(product, lowestPrice, lowestStore, previousLowestPrice, previousAlertFiredAt);

    setTrackingChecks((prev) => ({
      ...prev,
      [product.id]: {
        fetchedAt: payload?.fetched_at || new Date().toISOString(),
        stores: payload?.stores || [],
        lowestStore,
        lowestPrice,
        currency: payload?.currency || 'TRY',
        previousLowestPrice,
        alertFiredAt: trigger ? Date.now() : previousAlertFiredAt,
      },
    }));

    if (trigger) {
      const delta = previousLowestPrice != null && previousLowestPrice > trigger.price
        ? previousLowestPrice - trigger.price
        : null;
      const deltaText = delta != null
        ? ` (down ${Math.round(delta).toLocaleString('en-US')} TL since last check)`
        : '';
      toast.success(
        `${product.name} hit ${Math.round(trigger.price).toLocaleString('en-US')} TL at ${trigger.store}!`,
        { duration: 6000, icon: '🔔', style: { borderRadius: '10px', background: '#0f172a', color: '#fff' } },
      );
      pushNotification({
        type: 'price-drop',
        title: 'Price alert',
        message:
          `${product.name} dropped to ${Math.round(trigger.price).toLocaleString('en-US')} TL at ${trigger.store}` +
          ` — target was ${Math.round(trigger.target).toLocaleString('en-US')} TL${deltaText}.`,
      });

      // Auto-buy on live trigger when the user opted in. The guard inside
      // executeAutoBuy stops us from re-purchasing the same product if the
      // price oscillates across the threshold.
      if (product.trackingActions?.autoBuy) {
        executeAutoBuy(product, { store: trigger.store, price: trigger.price, source: 'live-check' });
      }
    }
  }, [evaluatePriceAlert, executeAutoBuy, pushNotification]);

  // Rotating tracker — picks the SINGLE tracked item with the oldest check
  // every 3 minutes and refreshes its prices. Round-robin keeps HTTP load low
  // and gives every product a turn even with many items in the list.
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      if (cancelled) return;
      const items = trackedRef.current;
      if (!items || items.length === 0) return;

      // Pick the one with the oldest (or absent) check timestamp.
      const checks = checksRef.current || {};
      const next = [...items].sort((a, b) => {
        const ta = Date.parse(checks[a.id]?.fetchedAt || 0) || 0;
        const tb = Date.parse(checks[b.id]?.fetchedAt || 0) || 0;
        return ta - tb;
      })[0];
      if (next) await checkSingleTracked(next);
    };

    // Run once immediately so newly-tracked items don't wait 3 minutes for
    // their first reading, then settle into the slow cadence.
    tick();
    const id = setInterval(tick, 3 * 60 * 1000);
    return () => { cancelled = true; clearInterval(id); };
  }, [checkSingleTracked]);

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
    'Samsung Galaxy Buds4 Pro',
    'Samsung Galaxy Buds3 Pro',
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
    const base = isSearching && committedQuery
      ? filterProducts(committedQuery, sampleProducts)
      : sampleProducts;
    return applyDiscoverFilters(base, discoverFilters);
  }, [isSearching, committedQuery, discoverFilters]);

  if (!hasEnteredApp) {
    return <Landing onEnter={() => setHasEnteredApp(true)} />;
  }

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
              aria-label="Open notifications"
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
                {/* Discover hero */}
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center">
                    <Compass className="w-6 h-6" />
                  </div>
                  <div className="flex-1">
                    <h2 className="text-3xl font-display font-black text-slate-900">Discover</h2>
                    <p className="text-slate-500 text-sm mt-1">
                      Browse categories, or use the filters on the left to pinpoint the niche device you're after.
                    </p>
                  </div>
                  <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                    {displayedProducts.length} products
                  </span>
                </div>

                {/* Horizontal filters */}
                <DiscoverFilters
                  options={filterOptions}
                  filters={discoverFilters}
                  onChange={setDiscoverFilters}
                  onReset={resetDiscoverFilters}
                />

                {/* Grid */}
                <div className="space-y-6">
                  {isSearching && (
                    <h3 className="text-lg font-black text-slate-900">
                      Results for "{committedQuery}" ({displayedProducts.length})
                    </h3>
                  )}

                  {isRunning ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                      {[1, 2, 3, 4].map((i) => (
                        <div key={i} className="h-80 skeleton rounded-2xl" />
                      ))}
                    </div>
                  ) : displayedProducts.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                      {displayedProducts.map((product) => (
                        <ProductCard
                          key={product.id}
                          product={product}
                          onClick={setSelectedProduct}
                          onFavorite={toggleFavorite}
                          onTrack={toggleTracked}
                          isFavorite={favorites.some((f) => f.id === product.id)}
                          isTracked={tracked.some((t) => t.id === product.id)}
                          analyzedPrice={analysisReports?.[product.id]?.lowestPrice ?? null}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="bg-white border border-slate-100 rounded-2xl p-12 text-center">
                      <div className="w-14 h-14 mx-auto rounded-2xl bg-slate-50 flex items-center justify-center text-slate-300 mb-4">
                        <Compass className="w-7 h-7" />
                      </div>
                      <h4 className="text-base font-black text-slate-900 mb-1">
                        No products match your filters
                      </h4>
                      <p className="text-sm text-slate-500 mb-5">
                        Try removing some filters to broaden the results.
                      </p>
                      <button
                        type="button"
                        onClick={resetDiscoverFilters}
                        className="px-4 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover transition-colors"
                      >
                        Reset filters
                      </button>
                    </div>
                  )}
                </div>
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
                  initialVariantSelection={
                    visionVariantOverride?.productId === selectedProduct.id
                      ? visionVariantOverride.selection
                      : null
                  }
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
                          onClick={null}
                          onFavorite={toggleFavorite}
                          onTrack={toggleTracked}
                          isFavorite={favorites.some(f => f.id === product.id)}
                          isTracked={true}
                          trackingExpiresAt={product.trackingExpiresAt}
                          priceAlert={product.priceAlert}
                          trackingActions={product.trackingActions}
                          liveCheck={trackingChecks[product.id] || null}
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
                <Campaigns onDataLoaded={setCampaignsData} />
              </motion.div>
            )}

            {currentPage === 'orders' && (
              <motion.div key="orders" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <Orders userOrders={orders} />
              </motion.div>
            )}

            {currentPage === 'compare' && (
              <motion.div key="compare" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                <DeviceCompare
                  history={comparisonHistory}
                  onComparisonReady={recordComparison}
                  onDeleteHistory={removeComparison}
                />
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
      <ChatWidget
        contextProduct={selectedProduct}
        priceHistoryReport={selectedProduct ? priceHistoryReports?.[selectedProduct.id] : null}
        analystReport={selectedProduct ? analysisReports?.[selectedProduct.id] : null}
        comparisonContext={latestComparison}
        campaignsContext={campaignsData}
      />

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
