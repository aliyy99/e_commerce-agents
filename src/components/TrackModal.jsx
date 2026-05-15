import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, CalendarClock, Clock, X, Minus, Plus } from 'lucide-react';

const UNITS = [
  { key: 'second', label: 'Saniye', ms: 1000 },
  { key: 'minute', label: 'Dakika', ms: 60 * 1000 },
  { key: 'hour', label: 'Saat', ms: 60 * 60 * 1000 },
  { key: 'day', label: 'Gün', ms: 24 * 60 * 60 * 1000 },
];

const formatDuration = (totalMs) => {
  if (totalMs <= 0) return '0 saniye';
  const parts = [];
  let remaining = Math.floor(totalMs / 1000);
  const days = Math.floor(remaining / 86400); remaining %= 86400;
  const hours = Math.floor(remaining / 3600); remaining %= 3600;
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  if (days) parts.push(`${days} gün`);
  if (hours) parts.push(`${hours} saat`);
  if (minutes) parts.push(`${minutes} dk`);
  if (seconds && parts.length < 2) parts.push(`${seconds} sn`);
  return parts.slice(0, 2).join(' ');
};

const pad = (n) => String(n).padStart(2, '0');
const toLocalInputValue = (date) => {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
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
  const preview = isValid ? formatDuration(computedMs) : 'Geçersiz süre';

  if (!isOpen || !product) return null;

  const handleConfirm = () => {
    if (!isValid) return;
    onConfirm({ durationMs: computedMs, label: preview });
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
            className="bg-white rounded-3xl shadow-2xl w-full max-w-md relative z-10 overflow-hidden"
          >
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <div className="flex gap-4 items-center">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                    <Bell className="w-6 h-6 fill-current" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-slate-900">Ürünü Takibe Al</h3>
                    <p className="text-sm font-medium text-slate-500 line-clamp-1">{product.name}</p>
                  </div>
                </div>
                <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex p-1 bg-slate-100 rounded-xl mb-5">
                <button
                  type="button"
                  onClick={() => setMode('duration')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${mode === 'duration' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  <Clock className="w-4 h-4" />
                  Süre
                </button>
                <button
                  type="button"
                  onClick={() => setMode('date')}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-bold transition-all ${mode === 'date' ? 'bg-white text-primary shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
                >
                  <CalendarClock className="w-4 h-4" />
                  Tarih
                </button>
              </div>

              {mode === 'duration' ? (
                <div className="space-y-4 mb-6">
                  <div>
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Birim</label>
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
                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Miktar</label>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => bump(-1)}
                        className="w-11 h-11 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center transition-colors"
                        aria-label="Azalt"
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
                        aria-label="Arttır"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mb-6">
                  <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Bitiş Tarihi</label>
                  <input
                    type="datetime-local"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    min={toLocalInputValue(new Date())}
                    className="w-full h-11 bg-slate-50 border border-slate-200 rounded-xl px-4 text-slate-900 font-bold focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                </div>
              )}

              <div className={`rounded-xl px-4 py-3 mb-6 text-center text-sm font-bold ${isValid ? 'bg-primary/5 text-primary' : 'bg-rose-50 text-rose-500'}`}>
                {isValid ? `${preview} boyunca takip edilecek` : preview}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-3 rounded-xl font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
                >
                  Vazgeç
                </button>
                <button
                  onClick={handleConfirm}
                  disabled={!isValid}
                  className="flex-1 px-4 py-3 rounded-xl font-bold text-white bg-primary hover:bg-primary-hover shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Takibe Başla
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
