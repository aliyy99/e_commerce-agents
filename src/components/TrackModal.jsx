import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, CalendarClock, Clock, X, Minus, Plus, Tag, Percent, ShoppingBag, BellRing } from 'lucide-react';

const UNITS = [
  { key: 'second', label: 'Second', ms: 1000 },
  { key: 'minute', label: 'Minute', ms: 60 * 1000 },
  { key: 'hour', label: 'Hour', ms: 60 * 60 * 1000 },
  { key: 'day', label: 'Day', ms: 24 * 60 * 60 * 1000 },
];

const formatDuration = (totalMs) => {
  if (totalMs <= 0) return '0 seconds';
  const parts = [];
  let remaining = Math.floor(totalMs / 1000);
  const days = Math.floor(remaining / 86400); remaining %= 86400;
  const hours = Math.floor(remaining / 3600); remaining %= 3600;
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  if (days) parts.push(`${days}d`);
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  if (seconds && parts.length < 2) parts.push(`${seconds}s`);
  return parts.slice(0, 2).join(' ');
};

const pad = (n) => String(n).padStart(2, '0');
const toLocalInputValue = (date) => {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

const computeBaselinePrice = (product) => {
  if (!product) return null;
  const prices = (product.stores || [])
    .map((s) => Number(s?.price))
    .filter((p) => Number.isFinite(p) && p > 0);
  if (prices.length === 0) return null;
  return Math.round(prices.reduce((a, b) => a + b, 0) / prices.length);
};

const TrackModal = ({ isOpen, product, onClose, onConfirm }) => {
  const [mode, setMode] = useState('duration');
  const [unit, setUnit] = useState('day');
  const [amount, setAmount] = useState(7);
  const [endDate, setEndDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    return toLocalInputValue(d);
  });

  // ── Price alert config ────────────────────────────────────────────────
  const baselinePrice = useMemo(() => computeBaselinePrice(product), [product]);
  const [alertMode, setAlertMode] = useState('price'); // 'price' | 'percent'
  const [alertPrice, setAlertPrice] = useState(() =>
    baselinePrice ? Math.round(baselinePrice * 0.9) : 0,
  );
  const [alertPercent, setAlertPercent] = useState(10);

  // Re-seed alert price when the modal is opened for a new product that has
  // a different baseline. Avoids stale values from a previous open.
  React.useEffect(() => {
    if (baselinePrice && !alertPrice) {
      setAlertPrice(Math.round(baselinePrice * 0.9));
    }
  }, [baselinePrice]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Action mode (notify / auto-buy / both) ────────────────────────────
  const [notifyOnHit, setNotifyOnHit] = useState(true);
  const [autoBuyOnHit, setAutoBuyOnHit] = useState(false);

  const unitMs = useMemo(() => UNITS.find(u => u.key === unit)?.ms ?? 86400000, [unit]);

  const computedMs = useMemo(() => {
    if (mode === 'duration') {
      const safe = Math.max(1, Number(amount) || 0);
      return safe * unitMs;
    }
    const target = new Date(endDate).getTime();
    return target - Date.now();
  }, [mode, amount, unit, unitMs, endDate]);

  const isValid = computedMs > 0;
  const preview = isValid ? formatDuration(computedMs) : 'Invalid duration';

  // Derived target price for the percent case so we can show users what the
  // % actually translates to in TL — keeps the choice concrete.
  const targetPriceTL = useMemo(() => {
    if (alertMode === 'price') return Math.max(0, Number(alertPrice) || 0);
    if (!baselinePrice) return null;
    const pct = Math.max(0, Math.min(100, Number(alertPercent) || 0));
    return Math.round(baselinePrice * (1 - pct / 100));
  }, [alertMode, alertPrice, alertPercent, baselinePrice]);

  const atLeastOneAction = notifyOnHit || autoBuyOnHit;
  const priceAlertValid =
    alertMode === 'price'
      ? Number(alertPrice) > 0
      : Number(alertPercent) > 0 && Number(alertPercent) <= 100;

  if (!isOpen || !product) return null;

  const handleConfirm = () => {
    if (!isValid || !priceAlertValid || !atLeastOneAction) return;
    onConfirm({
      durationMs: computedMs,
      label: preview,
      priceAlert: {
        mode: alertMode,
        targetPrice: alertMode === 'price' ? Number(alertPrice) : targetPriceTL,
        percentDrop: alertMode === 'percent' ? Number(alertPercent) : null,
        baselinePrice,
      },
      actions: {
        notify: notifyOnHit,
        autoBuy: autoBuyOnHit,
      },
    });
  };

  const bump = (delta) => {
    setAmount(prev => Math.max(1, (Number(prev) || 0) + delta));
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="bg-white rounded-3xl shadow-2xl w-full max-w-lg relative z-10 overflow-hidden max-h-[92vh] flex flex-col"
          >
            <div className="p-6 overflow-y-auto">
              <div className="flex justify-between items-start mb-6">
                <div className="flex gap-4 items-center">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                    <Bell className="w-6 h-6 fill-current" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-slate-900">Track Product</h3>
                    <p className="text-sm font-medium text-slate-500 line-clamp-1">{product.name}</p>
                  </div>
                </div>
                <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* ── Duration ─────────────────────────────────────────── */}
              <div className="flex p-1 bg-slate-100 rounded-xl mb-5">
                <button
                  type="button"
                  onClick={() => setMode('duration')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${mode === 'duration' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  <Clock className="w-4 h-4" />
                  Duration
                </button>
                <button
                  type="button"
                  onClick={() => setMode('date')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${mode === 'date' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  <CalendarClock className="w-4 h-4" />
                  Date
                </button>
              </div>

              {mode === 'duration' ? (
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Unit</label>
                    <div className="grid grid-cols-4 gap-1.5">
                      {UNITS.map(u => (
                        <button
                          key={u.key}
                          type="button"
                          onClick={() => setUnit(u.key)}
                          className={`py-2 rounded-lg text-xs font-bold transition-all ${unit === u.key ? 'bg-primary text-white shadow-sm' : 'bg-slate-50 text-slate-600 hover:bg-slate-100'}`}
                        >
                          {u.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Amount</label>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => bump(-1)}
                        className="w-11 h-11 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center transition-colors"
                        aria-label="Decrease"
                      >
                        <Minus className="w-4 h-4" />
                      </button>
                      <input
                        type="number"
                        min="1"
                        value={amount}
                        onChange={(e) => setAmount(e.target.value === '' ? '' : Number(e.target.value))}
                        onBlur={() => { if (!amount || amount < 1) setAmount(1); }}
                        className="flex-1 h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-center text-slate-900 font-black text-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      />
                      <button
                        type="button"
                        onClick={() => bump(1)}
                        className="w-11 h-11 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center transition-colors"
                        aria-label="Increase"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mb-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">End Date</label>
                  <input
                    type="datetime-local"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    min={toLocalInputValue(new Date())}
                    className="w-full h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-slate-900 font-bold focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                </div>
              )}

              {/* ── Price alert section ──────────────────────────────── */}
              <div className="mb-6 border-t border-slate-100 pt-5">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Price Alert</label>
                  {baselinePrice && (
                    <span className="text-[11px] font-bold text-slate-400">
                      Average: <span className="text-slate-700">{baselinePrice.toLocaleString()} TL</span>
                    </span>
                  )}
                </div>

                <div className="flex p-1 bg-slate-100 rounded-xl mb-3">
                  <button
                    type="button"
                    onClick={() => setAlertMode('price')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${alertMode === 'price' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                  >
                    <Tag className="w-4 h-4" />
                    Target Price (TL)
                  </button>
                  <button
                    type="button"
                    onClick={() => setAlertMode('percent')}
                    className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${alertMode === 'percent' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                  >
                    <Percent className="w-4 h-4" />
                    Percent (%) Drop
                  </button>
                </div>

                {alertMode === 'price' ? (
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min="0"
                      value={alertPrice}
                      onChange={(e) => setAlertPrice(e.target.value === '' ? '' : Number(e.target.value))}
                      className="flex-1 h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-slate-900 font-black text-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                      placeholder="Target price"
                    />
                    <span className="text-sm font-bold text-slate-500">TL</span>
                  </div>
                ) : (
                  <div>
                    <div className="flex items-center gap-2">
                      <input
                        type="number"
                        min="1"
                        max="100"
                        value={alertPercent}
                        onChange={(e) => setAlertPercent(e.target.value === '' ? '' : Number(e.target.value))}
                        className="flex-1 h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-slate-900 font-black text-lg focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                        placeholder="Percent"
                      />
                      <span className="text-sm font-bold text-slate-500">%</span>
                    </div>
                    {baselinePrice && targetPriceTL != null && (
                      <p className="text-[11px] text-slate-500 font-medium mt-2">
                        Triggers around <span className="font-black text-slate-800">{targetPriceTL.toLocaleString()} TL</span>.
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* ── Action mode ──────────────────────────────────────── */}
              <div className="mb-6">
                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Action</label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setNotifyOnHit(v => !v)}
                    className={`p-4 rounded-2xl border-2 transition-all text-left ${
                      notifyOnHit
                        ? 'border-primary bg-primary/5 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-2 ${notifyOnHit ? 'bg-primary text-white' : 'bg-slate-100 text-slate-500'}`}>
                      <BellRing className="w-4 h-4" />
                    </div>
                    <p className={`text-sm font-bold ${notifyOnHit ? 'text-primary' : 'text-slate-800'}`}>Notify Me</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Alert when price hits target.</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => setAutoBuyOnHit(v => !v)}
                    className={`p-4 rounded-2xl border-2 transition-all text-left ${
                      autoBuyOnHit
                        ? 'border-emerald-500 bg-emerald-50 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center mb-2 ${autoBuyOnHit ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-500'}`}>
                      <ShoppingBag className="w-4 h-4" />
                    </div>
                    <p className={`text-sm font-bold ${autoBuyOnHit ? 'text-emerald-700' : 'text-slate-800'}`}>Auto-Buy</p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Purchase automatically when target hits.</p>
                  </button>
                </div>
                {!atLeastOneAction && (
                  <p className="text-[11px] text-rose-500 font-bold mt-2">Pick at least one action.</p>
                )}
              </div>

              {/* ── Summary ─────────────────────────────────────────── */}
              <div className={`rounded-xl px-4 py-3 mb-6 text-center text-sm font-bold ${isValid ? 'bg-primary/5 text-primary' : 'bg-rose-50 text-rose-500'}`}>
                {isValid ? `Tracked for ${preview}` : preview}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-3 rounded-xl font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={!isValid || !priceAlertValid || !atLeastOneAction}
                  className="flex-1 px-4 py-3 rounded-xl font-bold text-white bg-primary hover:bg-primary-hover shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Start Tracking
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export { formatDuration };
export default TrackModal;
