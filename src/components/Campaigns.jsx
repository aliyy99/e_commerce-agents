import React, { useEffect, useMemo, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Tag,
  Ticket,
  Newspaper,
  Copy,
  Check,
  RefreshCw,
  ExternalLink,
  Sparkles,
  TrendingDown,
  Megaphone,
  Rocket,
  Flame,
  Globe,
  AlertCircle,
} from 'lucide-react';
import { fetchCampaigns } from '../services/api';
import { ECOMMERCE_ACCOUNTS, getConnectedAccounts } from '../data/ecommerceAccounts';

// Look up the store metadata (gradient, initials) by id so coupons can render
// a consistent badge that matches the connected-accounts list on the profile.
const STORE_LOOKUP = ECOMMERCE_ACCOUNTS.reduce((acc, s) => {
  acc[s.id] = s;
  return acc;
}, {});

// News category → icon + accent colour. Falls back to a neutral "industry"
// look so unknown categories still render cleanly.
const NEWS_CATEGORY_META = {
  'price-drop':  { label: 'Price Drop',  icon: TrendingDown, badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', accent: 'bg-emerald-500' },
  'new-product': { label: 'New Product', icon: Rocket,       badge: 'bg-violet-50 text-violet-700 border-violet-200',    accent: 'bg-violet-500' },
  'launch':      { label: 'Launch',      icon: Megaphone,    badge: 'bg-blue-50 text-blue-700 border-blue-200',          accent: 'bg-blue-500' },
  'deal':        { label: 'Deal',        icon: Flame,        badge: 'bg-orange-50 text-orange-700 border-orange-200',    accent: 'bg-orange-500' },
  'industry':    { label: 'Industry',    icon: Globe,        badge: 'bg-slate-50 text-slate-600 border-slate-200',       accent: 'bg-slate-500' },
};

const TABS = [
  { id: 'coupons', label: 'Coupons', icon: Ticket },
  { id: 'news',    label: 'News',    icon: Newspaper },
];

const StoreBadge = ({ storeId, fallbackName }) => {
  const meta = STORE_LOOKUP[storeId];
  const name = meta?.name || fallbackName || storeId;
  const color = meta?.color || 'from-slate-500 to-slate-700';
  const initials = meta?.initials || name.slice(0, 2).toUpperCase();
  return (
    <div className="inline-flex items-center gap-2 pl-1 pr-3 py-1 rounded-full bg-white border border-slate-200 shadow-sm">
      <span className={`w-6 h-6 rounded-full bg-gradient-to-br ${color} text-white text-[10px] font-black flex items-center justify-center`}>
        {initials}
      </span>
      <span className="text-[11px] font-bold text-slate-700">{name}</span>
    </div>
  );
};

const CouponCard = ({ coupon, copiedId, onCopy }) => {
  const copied = copiedId === coupon.id;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-primary/30 transition-all overflow-hidden flex flex-col"
    >
      <div className="absolute -right-12 -top-12 w-32 h-32 rounded-full bg-primary/5" />
      <div className="relative flex items-start justify-between gap-3 mb-4">
        <StoreBadge storeId={coupon.store_id} fallbackName={coupon.store_name} />
        {coupon.discount_label && (
          <span className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-black uppercase tracking-wide whitespace-nowrap">
            {coupon.discount_label}
          </span>
        )}
      </div>

      <h4 className="text-base font-black text-slate-900 leading-snug mb-1.5">
        {coupon.title}
      </h4>
      <p className="text-[13px] text-slate-500 leading-relaxed mb-4 flex-1">
        {coupon.description}
      </p>

      <div className="flex flex-wrap items-center gap-2 mb-4">
        {coupon.category && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 uppercase tracking-wider">
            {coupon.category}
          </span>
        )}
        {coupon.expires_label && (
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-50 text-rose-600 uppercase tracking-wider">
            {coupon.expires_label}
          </span>
        )}
      </div>

      {coupon.code ? (
        <div className="flex items-center justify-between gap-2 p-3 bg-slate-50 border border-dashed border-slate-300 rounded-xl">
          <span className="font-mono font-bold text-slate-800 tracking-wider text-sm truncate">
            {coupon.code}
          </span>
          <button
            type="button"
            onClick={() => onCopy(coupon)}
            className="shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-[11px] font-bold text-slate-600 hover:text-primary hover:border-primary/40 transition-colors"
          >
            {copied ? <><Check className="w-3.5 h-3.5 text-emerald-500" /> Copied</> : <><Copy className="w-3.5 h-3.5" /> Copy</>}
          </button>
        </div>
      ) : coupon.url ? (
        <a
          href={coupon.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-primary text-white text-xs font-bold hover:bg-primary-hover transition-colors"
        >
          Go to deal <ExternalLink className="w-3.5 h-3.5" />
        </a>
      ) : (
        <div className="px-3 py-2 rounded-xl bg-slate-50 border border-slate-100 text-[11px] text-slate-500 text-center">
          No coupon code — discount is applied automatically.
        </div>
      )}
    </motion.article>
  );
};

const NewsCard = ({ item }) => {
  const meta = NEWS_CATEGORY_META[item.category] || NEWS_CATEGORY_META.industry;
  const Icon = meta.icon;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative bg-white border border-slate-100 rounded-2xl p-5 shadow-sm hover:shadow-md hover:border-primary/30 transition-all overflow-hidden"
    >
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${meta.accent}`} />
      <div className="flex items-center justify-between gap-3 mb-3">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-black uppercase tracking-wide ${meta.badge}`}>
          <Icon className="w-3.5 h-3.5" />
          {meta.label}
        </span>
        {item.date_label && (
          <span className="text-[11px] text-slate-400 font-bold uppercase tracking-wider">
            {item.date_label}
          </span>
        )}
      </div>
      <h4 className="text-base font-black text-slate-900 leading-snug mb-2">
        {item.title}
      </h4>
      <p className="text-[13px] text-slate-500 leading-relaxed mb-3">
        {item.summary}
      </p>
      <div className="flex items-center justify-between gap-3 pt-2 border-t border-slate-100">
        <span className="text-[11px] text-slate-400 truncate">
          {item.source ? `Source: ${item.source}` : 'From the web'}
        </span>
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-[11px] font-bold text-primary hover:underline whitespace-nowrap"
          >
            Read more <ExternalLink className="w-3 h-3" />
          </a>
        )}
      </div>
    </motion.article>
  );
};

const SkeletonGrid = () => (
  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
    {[0, 1, 2, 3, 4, 5].map((i) => (
      <div key={i} className="h-56 bg-white border border-slate-100 rounded-2xl animate-pulse">
        <div className="h-full p-5 flex flex-col gap-3">
          <div className="h-5 w-24 bg-slate-100 rounded-full" />
          <div className="h-4 w-3/4 bg-slate-100 rounded" />
          <div className="h-3 w-full bg-slate-100 rounded" />
          <div className="h-3 w-5/6 bg-slate-100 rounded" />
          <div className="mt-auto h-10 bg-slate-100 rounded-xl" />
        </div>
      </div>
    ))}
  </div>
);

const EmptyState = ({ icon: Icon, title, hint }) => (
  <div className="flex flex-col items-center justify-center text-center bg-white border border-slate-100 rounded-2xl py-16 px-6">
    <div className="w-16 h-16 rounded-2xl bg-slate-50 flex items-center justify-center text-slate-300 mb-4">
      <Icon className="w-7 h-7" />
    </div>
    <h4 className="text-base font-black text-slate-900 mb-1">{title}</h4>
    <p className="text-sm text-slate-500 max-w-xs">{hint}</p>
  </div>
);

const Campaigns = ({ onDataLoaded }) => {
  const [activeTab, setActiveTab] = useState('coupons');
  const [coupons, setCoupons] = useState([]);
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [grounded, setGrounded] = useState(false);
  const [generatedAt, setGeneratedAt] = useState(null);

  const connected = useMemo(() => getConnectedAccounts(), []);

  const loadCampaigns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCampaigns({ connectedAccounts: connected });
      setCoupons(Array.isArray(data?.coupons) ? data.coupons : []);
      setNews(Array.isArray(data?.news) ? data.news : []);
      setGrounded(!!data?.grounded);
      setGeneratedAt(new Date());
      onDataLoaded?.({
        coupons: data?.coupons || [],
        news: data?.news || [],
        connectedAccounts: connected,
        generatedAt: new Date().toISOString(),
        grounded: !!data?.grounded,
      });
    } catch (err) {
      console.error('Campaigns fetch failed:', err);
      setError(err?.message || 'Could not load campaigns.');
    } finally {
      setLoading(false);
    }
  }, [connected, onDataLoaded]);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  const handleCopy = (coupon) => {
    if (!coupon.code) return;
    navigator.clipboard?.writeText(coupon.code).catch(() => {});
    setCopiedId(coupon.id);
    setTimeout(() => setCopiedId(null), 1800);
  };

  const tabCounts = { coupons: coupons.length, news: news.length };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-100 pb-6">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-primary/10 text-primary rounded-2xl flex items-center justify-center">
            <Tag className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-3xl font-display font-black text-slate-900">Campaigns</h2>
            <p className="text-slate-500 mt-1 text-sm">
              Coupons tailored to your connected accounts, plus the latest tech-world news.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {generatedAt && (
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] text-slate-400 font-bold uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-primary" />
              {grounded ? 'From the web' : 'AI summary'} · {generatedAt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <button
            type="button"
            onClick={loadCampaigns}
            disabled={loading}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-xs font-bold text-slate-600 hover:text-primary hover:border-primary/40 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Connected accounts strip */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mr-1">
          Connected accounts:
        </span>
        {connected.length > 0 ? (
          connected.map((acc) => (
            <span
              key={acc.id}
              className="inline-flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full bg-white border border-slate-200 shadow-sm"
            >
              <span className={`w-5 h-5 rounded-full bg-gradient-to-br ${acc.color} text-white text-[9px] font-black flex items-center justify-center`}>
                {acc.initials}
              </span>
              <span className="text-[11px] font-bold text-slate-700">{acc.name}</span>
            </span>
          ))
        ) : (
          <span className="text-[11px] text-slate-400">
            Connect your e-commerce accounts from the Profile page to see personalised coupons.
          </span>
        )}
      </div>

      {/* Tab switcher */}
      <div className="inline-flex p-1 bg-slate-100 rounded-xl">
        {TABS.map((tab) => {
          const TabIcon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-4 sm:px-5 py-2 rounded-lg text-xs font-black transition-colors flex items-center gap-2 ${
                active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <TabIcon className="w-4 h-4" />
              {tab.label}
              <span className={`text-[10px] font-black px-1.5 py-0.5 rounded-full ${active ? 'bg-primary/10 text-primary' : 'bg-slate-200 text-slate-500'}`}>
                {tabCounts[tab.id] ?? 0}
              </span>
            </button>
          );
        })}
      </div>

      {/* Error banner */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-rose-50 border border-rose-200 rounded-xl">
          <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-bold text-rose-700">Could not load campaigns</p>
            <p className="text-xs text-rose-600 mt-0.5">{error}</p>
          </div>
          <button
            type="button"
            onClick={loadCampaigns}
            className="text-xs font-bold text-rose-700 hover:underline whitespace-nowrap"
          >
            Try again
          </button>
        </div>
      )}

      {/* Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab + (loading ? '-loading' : '-ready')}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2 }}
        >
          {loading ? (
            <SkeletonGrid />
          ) : activeTab === 'coupons' ? (
            coupons.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {coupons.map((coupon) => (
                  <CouponCard
                    key={coupon.id}
                    coupon={coupon}
                    copiedId={copiedId}
                    onCopy={handleCopy}
                  />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Ticket}
                title="No active coupons right now"
                hint="No active campaigns for your connected accounts. Check back in a few minutes or connect another store."
              />
            )
          ) : news.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
              {news.map((item) => (
                <NewsCard key={item.id} item={item} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Newspaper}
              title="No news yet"
              hint="Couldn't pull fresh tech headlines from the web. Please try again in a moment."
            />
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  );
};

export default Campaigns;
