import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Package,
  Truck,
  CheckCircle2,
  Clock,
  ShoppingBag,
  Search,
  ArrowUpRight,
  Sparkles,
  TrendingDown,
} from 'lucide-react';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';

// Status-driven styling so badges, icons, and progress bars stay in lockstep.
const STATUS_META = {
  delivered: {
    label: 'Delivered',
    icon: CheckCircle2,
    chip: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    accent: 'from-emerald-400 to-emerald-600',
    progress: 1,
  },
  shipped: {
    label: 'Shipped',
    icon: Truck,
    chip: 'bg-indigo-100 text-indigo-700 border-indigo-200',
    accent: 'from-indigo-400 to-indigo-600',
    progress: 0.66,
  },
  processing: {
    label: 'Processing',
    icon: Clock,
    chip: 'bg-amber-100 text-amber-700 border-amber-200',
    accent: 'from-amber-400 to-amber-600',
    progress: 0.33,
  },
  scheduled: {
    label: 'Awaiting Auto-Buy',
    icon: Sparkles,
    chip: 'bg-fuchsia-100 text-fuchsia-700 border-fuchsia-200',
    accent: 'from-fuchsia-400 to-pink-600',
    progress: 0.1,
  },
};

const MOCK_ORDERS = [
  {
    id: 'TT-2026-0512',
    productName: 'Samsung Galaxy S25 Ultra 512 GB',
    image: 'https://cdn.dsmcdn.com/ty1626/product/media/images/prod/PIM/20250121/07/17ba277b-3bea-4c35-9aef-2d9f08b02ce9/1_org_zoom.jpg',
    store: 'Hepsiburada',
    price: 78990,
    originalPrice: 86000,
    purchasedAt: '2026-05-12T11:42:00',
    status: 'shipped',
    method: 'auto-buy',
    eta: 'May 17 Wed',
  },
  {
    id: 'TT-2026-0508',
    productName: 'Sony WH-1000XM5',
    image: 'https://cdn.dsmcdn.com/ty1015/product/media/images/prod/PIM/20231004/02/0a9bdf8e-a18f-4b8e-8c47-cf8b4ab1bf7c/1_org_zoom.jpg',
    store: 'Amazon',
    price: 11250,
    originalPrice: 13499,
    purchasedAt: '2026-05-08T18:13:00',
    status: 'delivered',
    method: 'manual',
    eta: 'Delivered',
  },
  {
    id: 'TT-2026-0504',
    productName: 'Dyson V15 Detect Absolute',
    image: 'https://cdn.dsmcdn.com/ty903/product/media/images/prod/SPM/PIM/20230531/01/d4d24818-7da8-3f5b-9ec4-8a2f7f08b41a/1_org_zoom.jpg',
    store: 'Vatan Bilgisayar',
    price: 26999,
    originalPrice: 29999,
    purchasedAt: '2026-05-04T09:01:00',
    status: 'processing',
    method: 'auto-buy',
    eta: 'May 20 Fri',
  },
  {
    id: 'TT-AUTO-PEND-031',
    productName: 'MacBook Pro 14" M4',
    image: 'https://cdn.dsmcdn.com/ty1233/product/media/images/prod/PIM/20240520/09/4f3a2c81-6f3b-49a1-9c1b-77e2f47b5e0a/1_org_zoom.jpg',
    store: 'Trendyol',
    price: null,
    originalPrice: 65999,
    targetPrice: 58000,
    status: 'scheduled',
    method: 'auto-buy',
    eta: 'When target price hits',
  },
];

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'auto-buy', label: 'Auto-Buys' },
  { key: 'scheduled', label: 'Pending' },
  { key: 'delivered', label: 'Delivered' },
];

const formatCurrency = (n) => (n == null ? '—' : `${Number(n).toLocaleString()} TL`);
const formatDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
};

const Orders = ({ userOrders = [] }) => {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');

  // Live auto-buy orders (from App state) take priority over the seed list,
  // so a fresh purchase always shows up at the top with the most-recent
  // timestamp without the user needing to refresh.
  const allOrders = useMemo(
    () => [...userOrders, ...MOCK_ORDERS],
    [userOrders],
  );

  const filtered = useMemo(() => {
    return allOrders.filter((o) => {
      if (filter === 'auto-buy' && o.method !== 'auto-buy') return false;
      if (filter === 'scheduled' && o.status !== 'scheduled') return false;
      if (filter === 'delivered' && o.status !== 'delivered') return false;
      if (query.trim()) {
        const q = query.toLowerCase();
        return (
          o.productName.toLowerCase().includes(q) ||
          o.store.toLowerCase().includes(q) ||
          o.id.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [filter, query, allOrders]);

  const totals = useMemo(() => {
    const completed = allOrders.filter((o) => o.status === 'delivered');
    const inFlight = allOrders.filter((o) => ['shipped', 'processing'].includes(o.status));
    const scheduled = allOrders.filter((o) => o.status === 'scheduled');
    const savedTotal = allOrders
      .filter((o) => o.price != null && o.originalPrice != null)
      .reduce((acc, o) => acc + (o.originalPrice - o.price), 0);
    return {
      completed: completed.length,
      inFlight: inFlight.length,
      scheduled: scheduled.length,
      saved: savedTotal,
    };
  }, [allOrders]);

  return (
    <motion.div
      key="orders"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-8"
    >
      {/* Header / hero */}
      <div className="relative overflow-hidden rounded-3xl border border-slate-100 bg-gradient-to-br from-primary via-emerald-500 to-indigo-500 text-white p-8 shadow-xl shadow-primary/20">
        <div className="absolute -top-12 -right-10 w-64 h-64 rounded-full bg-white/10 blur-3xl" />
        <div className="absolute -bottom-16 left-1/3 w-72 h-72 rounded-full bg-white/10 blur-3xl" />
        <div className="relative flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
                <Package className="w-6 h-6" />
              </div>
              <span className="text-[11px] font-black uppercase tracking-[0.3em] text-white/80">
                Techno Track · Orders
              </span>
            </div>
            <h2 className="text-4xl font-display font-black leading-tight">My Orders</h2>
            <p className="text-white/80 text-sm mt-2 max-w-md">
              Track auto-buys, pending targets, and delivered products in one place.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 lg:gap-4 min-w-[320px]">
            <Stat label="Completed" value={totals.completed} icon={CheckCircle2} />
            <Stat label="In Transit" value={totals.inFlight} icon={Truck} />
            <Stat label="Pending" value={totals.scheduled} icon={Clock} />
            <Stat
              label="Savings"
              value={`${totals.saved.toLocaleString()} TL`}
              icon={TrendingDown}
            />
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-4 py-2 rounded-xl text-sm font-bold border transition-all ${
                filter === f.key
                  ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                  : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="relative flex items-center gap-2 bg-white border border-slate-200 px-4 py-2.5 rounded-xl w-full md:max-w-sm shadow-sm focus-within:border-primary/40 transition-colors">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search orders, products, or stores…"
            className="bg-transparent border-none outline-none text-sm w-full text-slate-900 placeholder:text-slate-400"
          />
        </div>
      </div>

      {/* Orders */}
      <AnimatePresence mode="popLayout">
        {filtered.length > 0 ? (
          <motion.div
            key="list"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="grid grid-cols-1 xl:grid-cols-2 gap-5"
          >
            {filtered.map((order) => (
              <OrderCard key={order.id} order={order} />
            ))}
          </motion.div>
        ) : (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="glass-card p-16 text-center bg-white border-slate-100 flex flex-col items-center gap-4 shadow-sm"
          >
            <Package className="w-10 h-10 text-slate-300" />
            <p className="text-slate-500 font-medium">No orders match this filter.</p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const Stat = ({ label, value, icon: Icon }) => (
  <div className="bg-white/10 backdrop-blur rounded-2xl px-4 py-3 border border-white/20">
    <div className="flex items-center gap-2 text-white/80 text-[10px] font-black uppercase tracking-wider">
      <Icon className="w-3.5 h-3.5" />
      {label}
    </div>
    <p className="text-2xl font-black mt-1">{value}</p>
  </div>
);

const OrderCard = ({ order }) => {
  const meta = STATUS_META[order.status] || STATUS_META.processing;
  const StatusIcon = meta.icon;
  const savings =
    order.price != null && order.originalPrice != null
      ? order.originalPrice - order.price
      : null;
  const savingsPct =
    savings != null && order.originalPrice > 0
      ? Math.round((savings / order.originalPrice) * 100)
      : null;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      className="group relative overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-sm hover:shadow-lg transition-all"
    >
      <div className={`h-1 w-full bg-gradient-to-r ${meta.accent}`} />
      <div className="p-5 flex gap-5">
        <div className="w-24 h-24 flex-shrink-0 rounded-2xl bg-slate-50 border border-slate-100 p-3 flex items-center justify-center">
          <img
            src={order.image || PRODUCT_IMAGE_FALLBACK}
            alt={order.productName}
            onError={(e) => {
              if (e.currentTarget.dataset.fb === '1') return;
              e.currentTarget.dataset.fb = '1';
              e.currentTarget.src = PRODUCT_IMAGE_FALLBACK;
            }}
            className="w-full h-full object-contain mix-blend-multiply"
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[10px] font-black tracking-widest uppercase text-slate-400">
                #{order.id}
              </p>
              <h3 className="text-base font-black text-slate-900 leading-tight truncate">
                {order.productName}
              </h3>
              <p className="text-xs text-slate-500 font-medium mt-0.5">
                {order.store} · {formatDate(order.purchasedAt)}
              </p>
            </div>
            <span
              className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold ${meta.chip}`}
            >
              <StatusIcon className="w-3.5 h-3.5" />
              {meta.label}
            </span>
          </div>

          <div className="mt-3 flex items-center justify-between gap-3">
            <div>
              {order.price != null ? (
                <>
                  <p className="text-[10px] font-black uppercase tracking-wider text-emerald-500">
                    Paid
                  </p>
                  <p className="text-lg font-black text-slate-900 leading-tight">
                    {formatCurrency(order.price)}
                  </p>
                </>
              ) : (
                <>
                  <p className="text-[10px] font-black uppercase tracking-wider text-fuchsia-500">
                    Target
                  </p>
                  <p className="text-lg font-black text-slate-900 leading-tight">
                    {formatCurrency(order.targetPrice)}
                  </p>
                </>
              )}
              {savings != null && savings > 0 && (
                <p className="text-[11px] font-bold text-emerald-600 mt-0.5">
                  -{savings.toLocaleString()} TL{savingsPct ? ` (${savingsPct}%)` : ''} saved
                </p>
              )}
            </div>

            <div className="flex flex-col items-end gap-1.5">
              {order.method === 'auto-buy' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-fuchsia-100 text-fuchsia-700 text-[10px] font-bold">
                  <Sparkles className="w-3 h-3" /> Auto-Buy
                </span>
              )}
              <span className="text-[11px] text-slate-500 font-medium">{order.eta}</span>
            </div>
          </div>

          {/* Progress bar */}
          <div className="mt-4 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${meta.progress * 100}%` }}
              transition={{ duration: 0.7, ease: 'easeOut' }}
              className={`h-full bg-gradient-to-r ${meta.accent}`}
            />
          </div>

          <div className="mt-4 flex items-center justify-between">
            <button className="text-[11px] font-black text-slate-500 uppercase tracking-wider hover:text-slate-900 inline-flex items-center gap-1.5">
              Order Details <ArrowUpRight className="w-3 h-3" />
            </button>
            <button className="text-[11px] font-black text-primary uppercase tracking-wider hover:underline inline-flex items-center gap-1.5">
              <ShoppingBag className="w-3 h-3" /> Buy Again
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default Orders;
