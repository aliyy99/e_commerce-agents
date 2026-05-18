import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import {
  Scale, Sparkles, Trophy, ArrowRight, RefreshCw, Zap, Layers,
  Cpu, Monitor, Camera, Battery, Smartphone, Wifi, Shield, Speaker,
  Fingerprint, DollarSign, Search, X, Check, AlertCircle, History, Trash2,
} from 'lucide-react';
import { sampleProducts } from '../data/products';
import { compareDevices } from '../services/api';
import { CATEGORY_META, deriveCategory } from '../utils/productCategory';
import { PRODUCT_IMAGE_FALLBACK } from '../utils/productImage';

const ICON_MAP = {
  Cpu, Monitor, Camera, Battery, Smartphone, Wifi, Shield, Speaker,
  Fingerprint, RefreshCw, Sparkles, DollarSign, Layers,
};

const pickIcon = (name) => ICON_MAP[name] || Layers;

const PickerRow = ({ item, onPick, muted = false }) => {
  const { product: p, meta } = item;
  return (
    <button
      onClick={() => onPick(p)}
      className={`w-full flex items-center gap-4 p-3 rounded-2xl text-left transition-colors hover:bg-slate-50 ${
        muted ? 'opacity-80' : ''
      }`}
    >
      <div className="w-14 h-14 rounded-xl bg-slate-50 flex items-center justify-center overflow-hidden flex-shrink-0">
        <img
          src={(p.images && p.images[0]) || PRODUCT_IMAGE_FALLBACK}
          alt={p.name}
          className="w-full h-full object-contain"
          onError={(e) => { e.currentTarget.src = PRODUCT_IMAGE_FALLBACK; }}
        />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
            {p.brand}
          </span>
          <span className="px-1.5 py-0.5 rounded-full bg-slate-100 text-[10px] font-bold text-slate-500 flex items-center gap-1">
            <span>{meta.icon}</span>
            {meta.label}
          </span>
        </div>
        <div className="font-bold text-sm text-slate-900 truncate mt-0.5">
          {p.name}
        </div>
      </div>
      <ArrowRight className="w-4 h-4 text-slate-300 flex-shrink-0" />
    </button>
  );
};

const DeviceSlot = ({
  side,
  product,
  onPick,
  onClear,
  available,            // all products this slot can consider
  excludeId = null,     // the other slot's selection (filtered out)
  preferredCategory = null, // soft hint — same-category items float to the top
  accent,
}) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  // Every device is selectable from both slots. When the OTHER slot already
  // has a pick we float same-category items to the top under a "Best match"
  // header, but never hide or disable cross-category options — small catalogs
  // would otherwise leave the user stranded.
  const { matches, others } = useMemo(() => {
    const q = query.trim().toLowerCase();
    const rows = available
      .filter((p) => p.id !== excludeId)
      .map((p) => {
        const cat = deriveCategory(p);
        const meta = CATEGORY_META[cat] || { label: cat, icon: '✨' };
        const hay = `${p.name} ${p.brand || ''} ${meta.label}`.toLowerCase();
        return { product: p, cat, meta, matches: !q || hay.includes(q) };
      })
      .filter((it) => it.matches);
    const sameCat = preferredCategory
      ? rows.filter((it) => it.cat === preferredCategory)
      : [];
    const otherCat = preferredCategory
      ? rows.filter((it) => it.cat !== preferredCategory)
      : rows;
    return { matches: sameCat, others: otherCat };
  }, [available, excludeId, preferredCategory, query]);

  return (
    <div className="relative">
      <div
        className={`relative rounded-3xl overflow-hidden bg-white border-2 transition-all duration-500 ${
          product
            ? 'border-transparent shadow-xl'
            : 'border-dashed border-slate-200 hover:border-primary/40 hover:bg-slate-50/50'
        }`}
        style={
          product
            ? { boxShadow: `0 25px 60px -20px ${accent}55, 0 0 0 1px ${accent}25` }
            : {}
        }
      >
        {/* Side label */}
        <div className="absolute top-4 left-4 z-10">
          <span
            className="px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider text-white shadow-md"
            style={{ background: accent }}
          >
            DEVICE {side}
          </span>
        </div>

        {product ? (
          <div className="p-6 pt-14">
            <button
              onClick={onClear}
              className="absolute top-4 right-4 z-10 p-1.5 rounded-full bg-white/90 backdrop-blur text-slate-400 hover:text-rose-500 hover:bg-rose-50 transition-colors shadow-sm"
              title="Clear"
            >
              <X className="w-4 h-4" />
            </button>
            <div
              className="aspect-square rounded-2xl flex items-center justify-center mb-4 overflow-hidden"
              style={{ background: `linear-gradient(135deg, ${accent}10, ${accent}05)` }}
            >
              <img
                src={(product.images && product.images[0]) || PRODUCT_IMAGE_FALLBACK}
                alt={product.name}
                className="w-full h-full object-contain p-6 drop-shadow-xl"
                onError={(e) => { e.currentTarget.src = PRODUCT_IMAGE_FALLBACK; }}
              />
            </div>
            <div className="text-[11px] font-bold text-slate-400 tracking-widest uppercase">
              {product.brand}
            </div>
            <h3 className="font-display text-lg font-black text-slate-900 leading-tight mt-1">
              {product.name}
            </h3>
            <p className="text-xs text-slate-500 mt-2 line-clamp-2">
              {product.description}
            </p>
            <button
              onClick={() => setOpen(true)}
              className="mt-4 w-full px-4 py-2 rounded-xl border border-slate-200 text-xs font-bold text-slate-600 hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Change device
            </button>
          </div>
        ) : (
          <button
            onClick={() => setOpen(true)}
            className="w-full p-8 pt-14 text-center group"
          >
            <div
              className="aspect-square mx-auto rounded-2xl flex items-center justify-center mb-4 transition-transform group-hover:scale-[1.02]"
              style={{ background: `linear-gradient(135deg, ${accent}10, ${accent}05)` }}
            >
              <div
                className="w-20 h-20 rounded-2xl flex items-center justify-center"
                style={{ background: `${accent}20`, color: accent }}
              >
                <Sparkles className="w-10 h-10" />
              </div>
            </div>
            <p className="font-black text-slate-900">Select a device</p>
            <p className="text-xs text-slate-500 mt-1">
              {preferredCategory
                ? `Best with ${CATEGORY_META[preferredCategory]?.label || preferredCategory}, but any device works`
                : 'Click to browse the full catalog'}
            </p>
          </button>
        )}
      </div>

      {/* Picker drawer */}
      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-[80]"
            />
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.98 }}
              className="fixed inset-x-0 top-20 mx-auto max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-100 z-[81] overflow-hidden"
            >
              <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
                <Search className="w-4 h-4 text-slate-400" />
                <input
                  autoFocus
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search any device by name, brand or category..."
                  className="flex-1 outline-none text-sm text-slate-900 placeholder:text-slate-400"
                />
                <button onClick={() => setOpen(false)} className="text-xs text-slate-400 hover:text-slate-600 font-bold px-2">
                  CLOSE
                </button>
              </div>
              {preferredCategory && (
                <div className="px-5 py-2 bg-emerald-50 border-b border-emerald-100 text-[11px] text-emerald-700 flex items-center gap-2">
                  <span>{CATEGORY_META[preferredCategory]?.icon}</span>
                  <span>
                    Best matches: <b>{CATEGORY_META[preferredCategory]?.label || preferredCategory}</b> · other categories still selectable below.
                  </span>
                </div>
              )}
              <div className="max-h-[60vh] overflow-y-auto p-2">
                {matches.length === 0 && others.length === 0 ? (
                  <div className="p-8 text-center text-sm text-slate-400">
                    No devices match your search.
                  </div>
                ) : (
                  <>
                    {matches.length > 0 && (
                      <>
                        <div className="px-3 pt-2 pb-1 text-[10px] font-black text-emerald-600 uppercase tracking-widest flex items-center gap-2">
                          <Check className="w-3 h-3" />
                          Best match
                        </div>
                        {matches.map((it) => (
                          <PickerRow
                            key={it.product.id}
                            item={it}
                            onPick={(p) => { onPick(p); setOpen(false); setQuery(''); }}
                          />
                        ))}
                      </>
                    )}
                    {others.length > 0 && (
                      <>
                        {matches.length > 0 && (
                          <div className="px-3 pt-3 pb-1 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                            Other categories
                          </div>
                        )}
                        {others.map((it) => (
                          <PickerRow
                            key={it.product.id}
                            item={it}
                            onPick={(p) => { onPick(p); setOpen(false); setQuery(''); }}
                            muted={preferredCategory != null}
                          />
                        ))}
                      </>
                    )}
                  </>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};

const WinnerPill = ({ winner, accentA, accentB }) => {
  if (winner === 'tie') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider bg-slate-100 text-slate-500">
        Tie
      </span>
    );
  }
  const color = winner === 'A' ? accentA : accentB;
  return (
    <span
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider text-white shadow-sm"
      style={{ background: color }}
    >
      <Trophy className="w-3 h-3" />
      {winner === 'A' ? 'Device A' : 'Device B'}
    </span>
  );
};

const ScoreBar = ({ label, score, color }) => (
  <div>
    <div className="flex items-center justify-between mb-1.5">
      <span className="text-[10px] font-black uppercase tracking-wider text-slate-500">{label}</span>
      <span className="text-sm font-black" style={{ color }}>{score}</span>
    </div>
    <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${score}%` }}
        transition={{ duration: 1.0, ease: 'easeOut' }}
        className="h-full rounded-full"
        style={{ background: `linear-gradient(90deg, ${color}, ${color}CC)` }}
      />
    </div>
  </div>
);

const DeviceCompare = ({ history = {}, onComparisonReady, onDeleteHistory }) => {
  const [deviceA, setDeviceA] = useState(null);
  const [deviceB, setDeviceB] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);
  const [phase, setPhase] = useState('idle'); // idle | running | done

  // Sorted history entries (most recent first) — rendered above the picker as
  // a quick-restore strip so the user can revisit any comparison they've run.
  const historyEntries = useMemo(() => {
    return Object.entries(history)
      .map(([key, value]) => ({ key, ...value }))
      .sort((a, b) => (b.savedAt || 0) - (a.savedAt || 0));
  }, [history]);

  const handleRestore = (entry) => {
    setDeviceA(entry.deviceA);
    setDeviceB(entry.deviceB);
    setReport(entry.report);
    setError(null);
    setPhase('done');
    onComparisonReady?.({
      deviceA: entry.deviceA,
      deviceB: entry.deviceB,
      report: entry.report,
    });
    // Scroll the user toward the restored report.
    if (typeof window !== 'undefined') {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const ACCENT_A = '#0ea5e9';
  const ACCENT_B = '#f97316';

  // Soft preference — same-category items float to the top in the OTHER
  // slot's picker, but cross-category picks are always allowed. With a small
  // catalog (e.g. only one laptop) we never want to leave a user stranded.
  const preferredA = deviceB ? deriveCategory(deviceB) : null;
  const preferredB = deviceA ? deriveCategory(deviceA) : null;
  const activeCategory = deviceA
    ? deriveCategory(deviceA)
    : deviceB
      ? deriveCategory(deviceB)
      : null;
  const categoriesMatch =
    !deviceA || !deviceB || deriveCategory(deviceA) === deriveCategory(deviceB);

  const canCompare = deviceA && deviceB && !loading;

  const handleCompare = async () => {
    if (!canCompare) return;
    setLoading(true);
    setError(null);
    setReport(null);
    setPhase('running');
    try {
      const a = { ...deviceA, category: deriveCategory(deviceA) };
      const b = { ...deviceB, category: deriveCategory(deviceB) };
      const result = await compareDevices({ deviceA: a, deviceB: b, locale: 'tr' });
      setReport(result);
      setPhase('done');
      onComparisonReady?.({ deviceA: a, deviceB: b, report: result });
    } catch (err) {
      setError(err.message || 'Comparison failed.');
      setPhase('idle');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setReport(null);
    setError(null);
    setPhase('idle');
  };

  const heroAccent = activeCategory && CATEGORY_META[activeCategory]
    ? CATEGORY_META[activeCategory].accent
    : '#10b981';

  return (
    <div className="space-y-10">
      {/* Hero */}
      <div className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-8">
        <div
          className="absolute -top-24 -right-24 w-96 h-96 rounded-full blur-3xl opacity-30"
          style={{ background: heroAccent }}
        />
        <div
          className="absolute -bottom-24 -left-24 w-96 h-96 rounded-full blur-3xl opacity-20"
          style={{ background: ACCENT_A }}
        />

        <div className="relative flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-white/10 backdrop-blur flex items-center justify-center border border-white/20">
            <Scale className="w-7 h-7 text-white" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest text-emerald-300 mb-2">
              <Sparkles className="w-3.5 h-3.5" />
              AI-Powered Spec Analysis
            </div>
            <h2 className="text-4xl font-display font-black tracking-tight">
              Device Compare
            </h2>
            <p className="text-sm text-slate-300 mt-2 max-w-2xl leading-relaxed">
              Pick two devices from the same category and we'll run an
              exhaustive head-to-head: every spec, every angle, with a clear
              winner per row, an overall score and a long-form recommendation.
              Then ask the chat anything about the result.
            </p>
          </div>
        </div>

        {deviceA && deviceB && !categoriesMatch && (
          <div className="relative mt-6 flex items-center gap-2 flex-wrap">
            <span className="px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider bg-amber-500/20 text-amber-200 border border-amber-300/30">
              CROSS-CATEGORY MIX
            </span>
          </div>
        )}
      </div>

      {/* Previous comparisons */}
      {historyEntries.length > 0 && (
        <div className="rounded-3xl bg-white border border-slate-100 shadow-sm p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 text-primary flex items-center justify-center">
              <History className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="text-[10px] font-black uppercase tracking-widest text-primary">
                Recents
              </div>
              <h3 className="font-display text-lg font-black text-slate-900">
                Previous comparisons
              </h3>
            </div>
            <span className="px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider bg-primary/10 text-primary">
              {historyEntries.length}
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {historyEntries.map((entry) => {
              const winner = entry.report?.overall_winner;
              const winnerName = winner === 'A'
                ? entry.deviceA.name
                : winner === 'B'
                  ? entry.deviceB.name
                  : 'Tie';
              return (
                <div
                  key={entry.key}
                  className="group relative rounded-2xl border border-slate-100 bg-slate-50/40 hover:bg-white hover:border-primary/40 transition-colors p-4"
                >
                  <button
                    type="button"
                    onClick={() => handleRestore(entry)}
                    className="w-full text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex -space-x-3">
                        <div className="w-12 h-12 rounded-xl bg-white border border-slate-200 overflow-hidden flex items-center justify-center shadow-sm">
                          <img
                            src={(entry.deviceA.images && entry.deviceA.images[0]) || PRODUCT_IMAGE_FALLBACK}
                            alt={entry.deviceA.name}
                            className="w-full h-full object-contain"
                            onError={(e) => { e.currentTarget.src = PRODUCT_IMAGE_FALLBACK; }}
                          />
                        </div>
                        <div className="w-12 h-12 rounded-xl bg-white border border-slate-200 overflow-hidden flex items-center justify-center shadow-sm">
                          <img
                            src={(entry.deviceB.images && entry.deviceB.images[0]) || PRODUCT_IMAGE_FALLBACK}
                            alt={entry.deviceB.name}
                            className="w-full h-full object-contain"
                            onError={(e) => { e.currentTarget.src = PRODUCT_IMAGE_FALLBACK; }}
                          />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                          {entry.deviceA.brand} vs {entry.deviceB.brand}
                        </div>
                        <div className="text-sm font-black text-slate-900 truncate mt-0.5">
                          {entry.deviceA.name}
                        </div>
                        <div className="text-sm font-black text-slate-700 truncate">
                          {entry.deviceB.name}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 flex items-center justify-between">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-50 border border-emerald-100 text-[10px] font-black uppercase tracking-wider text-emerald-700">
                        <Trophy className="w-3 h-3" />
                        {winner === 'tie' || !winner ? 'Tie' : winnerName}
                      </span>
                      <span className="text-[11px] font-bold text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                        View →
                      </span>
                    </div>
                  </button>
                  {onDeleteHistory && (
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); onDeleteHistory(entry.key); }}
                      className="absolute top-2 right-2 p-1.5 rounded-lg text-slate-300 hover:text-rose-500 hover:bg-rose-50 transition-colors"
                      title="Remove from history"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* VS picker */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-6 items-center">
        <DeviceSlot
          side="A"
          product={deviceA}
          onPick={setDeviceA}
          onClear={() => setDeviceA(null)}
          available={sampleProducts}
          excludeId={deviceB?.id}
          preferredCategory={preferredA}
          accent={ACCENT_A}
        />

        <div className="flex flex-col items-center justify-center gap-4">
          <motion.div
            animate={{ rotate: loading ? 360 : 0 }}
            transition={{ duration: 1.5, repeat: loading ? Infinity : 0, ease: 'linear' }}
            className="w-20 h-20 rounded-full bg-white shadow-xl flex items-center justify-center border-2 border-slate-100 relative"
          >
            <div className="absolute inset-1 rounded-full bg-gradient-to-br from-primary via-emerald-500 to-emerald-600 opacity-90" />
            <span className="relative font-display font-black text-white text-2xl tracking-tight">VS</span>
          </motion.div>

          <button
            onClick={handleCompare}
            disabled={!canCompare}
            className={`px-6 py-3 rounded-2xl text-sm font-black tracking-wide transition-all flex items-center gap-2 shadow-lg ${
              canCompare
                ? 'bg-gradient-to-r from-primary to-emerald-600 text-white shadow-primary/30 hover:shadow-primary/50 active:scale-95'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
            }`}
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Analyzing
              </>
            ) : (
              <>
                <Zap className="w-4 h-4" />
                Compare Now
              </>
            )}
          </button>

          {deviceA && deviceB && !categoriesMatch && (
            <div className="text-[11px] text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2 max-w-[200px] text-center leading-relaxed">
              Different categories — comparison will focus on the dimensions they share.
            </div>
          )}

          {report && (
            <button
              onClick={handleReset}
              className="text-[11px] font-bold text-slate-400 hover:text-slate-700 transition-colors"
            >
              ↺ Reset
            </button>
          )}
        </div>

        <DeviceSlot
          side="B"
          product={deviceB}
          onPick={setDeviceB}
          onClear={() => setDeviceB(null)}
          available={sampleProducts}
          excludeId={deviceA?.id}
          preferredCategory={preferredB}
          accent={ACCENT_B}
        />
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 p-4 rounded-2xl bg-rose-50 border border-rose-100 text-sm text-rose-700"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading state */}
      <AnimatePresence>
        {phase === 'running' && !report && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-3xl bg-gradient-to-br from-slate-50 to-white border border-slate-100 p-10 text-center"
          >
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
              Analyzing every spec…
            </h3>
            <p className="text-sm text-slate-500 mt-2">
              Comparing performance, display, camera, battery, software, build and value.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      <AnimatePresence>
        {report && deviceA && deviceB && (
          <motion.div
            key="report"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="space-y-8"
          >
            {/* Verdict card */}
            <div
              className="relative rounded-3xl overflow-hidden p-8 text-white"
              style={{
                background: report.overall_winner === 'A'
                  ? `linear-gradient(135deg, ${ACCENT_A}, #0369a1)`
                  : report.overall_winner === 'B'
                    ? `linear-gradient(135deg, ${ACCENT_B}, #c2410c)`
                    : 'linear-gradient(135deg, #475569, #1e293b)',
              }}
            >
              <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/10 blur-3xl" />
              <div className="relative flex flex-col md:flex-row items-start md:items-center gap-6">
                <div className="w-16 h-16 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
                  <Trophy className="w-8 h-8 text-white" />
                </div>
                <div className="flex-1">
                  <div className="text-[11px] font-black uppercase tracking-widest opacity-80 mb-2">
                    Overall verdict
                  </div>
                  <h3 className="font-display text-3xl font-black leading-tight">
                    {report.overall_winner === 'tie'
                      ? "It's a tie"
                      : (report.overall_winner === 'A' ? deviceA.name : deviceB.name)}
                  </h3>
                  <p className="text-sm opacity-90 mt-2 max-w-3xl">
                    {report.overall_verdict}
                  </p>
                </div>
                <div className="w-full md:w-72 space-y-3 bg-white/10 backdrop-blur rounded-2xl p-5">
                  <ScoreBar label={`A · ${deviceA.brand}`} score={report.score_a} color="#fff" />
                  <ScoreBar label={`B · ${deviceB.brand}`} score={report.score_b} color="#fff" />
                </div>
              </div>
            </div>

            {/* Spec groups */}
            <div className="space-y-6">
              {report.groups.map((g, gi) => {
                const Icon = pickIcon(g.icon);
                const aWins = g.rows.filter((r) => r.winner === 'A').length;
                const bWins = g.rows.filter((r) => r.winner === 'B').length;
                return (
                  <motion.div
                    key={`${g.title}-${gi}`}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: gi * 0.05 }}
                    className="rounded-3xl bg-white border border-slate-100 shadow-sm overflow-hidden"
                  >
                    <div className="flex items-center gap-4 px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
                      <div className="w-11 h-11 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                        <Icon className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-display text-lg font-black text-slate-900">{g.title}</h4>
                        <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-0.5">
                          {g.rows.length} criteria · A wins {aWins} · B wins {bWins}
                        </p>
                      </div>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="text-[10px] font-black uppercase tracking-wider text-slate-400">
                            <th className="text-left px-6 py-3 w-[180px]">Feature</th>
                            <th className="text-left px-6 py-3" style={{ color: ACCENT_A }}>Device A</th>
                            <th className="text-left px-6 py-3" style={{ color: ACCENT_B }}>Device B</th>
                            <th className="text-left px-6 py-3 w-[110px]">Winner</th>
                          </tr>
                        </thead>
                        <tbody>
                          {g.rows.map((row, ri) => (
                            <tr
                              key={`${row.feature}-${ri}`}
                              className="border-t border-slate-50 hover:bg-slate-50/40 transition-colors"
                            >
                              <td className="px-6 py-4 align-top">
                                <div className="text-sm font-bold text-slate-900">{row.feature}</div>
                                {row.explanation && (
                                  <div className="text-xs text-slate-500 mt-1 leading-relaxed max-w-md">
                                    {row.explanation}
                                  </div>
                                )}
                              </td>
                              <td className="px-6 py-4 align-top">
                                <div
                                  className={`text-sm leading-relaxed ${row.winner === 'A' ? 'font-bold text-slate-900' : 'text-slate-600'}`}
                                >
                                  {row.winner === 'A' && (
                                    <Check className="inline w-4 h-4 mr-1.5" style={{ color: ACCENT_A }} />
                                  )}
                                  {row.value_a}
                                </div>
                              </td>
                              <td className="px-6 py-4 align-top">
                                <div
                                  className={`text-sm leading-relaxed ${row.winner === 'B' ? 'font-bold text-slate-900' : 'text-slate-600'}`}
                                >
                                  {row.winner === 'B' && (
                                    <Check className="inline w-4 h-4 mr-1.5" style={{ color: ACCENT_B }} />
                                  )}
                                  {row.value_b}
                                </div>
                              </td>
                              <td className="px-6 py-4 align-top">
                                <WinnerPill winner={row.winner} accentA={ACCENT_A} accentB={ACCENT_B} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </motion.div>
                );
              })}
            </div>

            {/* Pros / cons grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="rounded-3xl bg-white border border-slate-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100" style={{ background: `${ACCENT_A}10` }}>
                  <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: ACCENT_A }}>
                    Device A
                  </div>
                  <h4 className="font-display text-lg font-black text-slate-900 leading-tight">
                    {deviceA.name}
                  </h4>
                </div>
                <div className="p-6 space-y-5">
                  <div>
                    <h5 className="text-[11px] font-black uppercase tracking-widest text-emerald-600 mb-2">Strengths</h5>
                    <ul className="space-y-1.5">
                      {report.pros_a.map((p, i) => (
                        <li key={i} className="text-sm text-slate-700 flex gap-2">
                          <span className="text-emerald-500 mt-0.5">＋</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h5 className="text-[11px] font-black uppercase tracking-widest text-rose-600 mb-2">Trade-offs</h5>
                    <ul className="space-y-1.5">
                      {report.cons_a.map((p, i) => (
                        <li key={i} className="text-sm text-slate-700 flex gap-2">
                          <span className="text-rose-400 mt-0.5">－</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {report.best_for_a && (
                    <div className="pt-4 border-t border-slate-100">
                      <h5 className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-2">Best for</h5>
                      <p className="text-sm text-slate-600 leading-relaxed">{report.best_for_a}</p>
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-3xl bg-white border border-slate-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100" style={{ background: `${ACCENT_B}10` }}>
                  <div className="text-[10px] font-black uppercase tracking-widest" style={{ color: ACCENT_B }}>
                    Device B
                  </div>
                  <h4 className="font-display text-lg font-black text-slate-900 leading-tight">
                    {deviceB.name}
                  </h4>
                </div>
                <div className="p-6 space-y-5">
                  <div>
                    <h5 className="text-[11px] font-black uppercase tracking-widest text-emerald-600 mb-2">Strengths</h5>
                    <ul className="space-y-1.5">
                      {report.pros_b.map((p, i) => (
                        <li key={i} className="text-sm text-slate-700 flex gap-2">
                          <span className="text-emerald-500 mt-0.5">＋</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h5 className="text-[11px] font-black uppercase tracking-widest text-rose-600 mb-2">Trade-offs</h5>
                    <ul className="space-y-1.5">
                      {report.cons_b.map((p, i) => (
                        <li key={i} className="text-sm text-slate-700 flex gap-2">
                          <span className="text-rose-400 mt-0.5">－</span>
                          <span>{p}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  {report.best_for_b && (
                    <div className="pt-4 border-t border-slate-100">
                      <h5 className="text-[11px] font-black uppercase tracking-widest text-slate-500 mb-2">Best for</h5>
                      <p className="text-sm text-slate-600 leading-relaxed">{report.best_for_b}</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Long-form summary */}
            {report.summary && (
              <div className="rounded-3xl bg-gradient-to-br from-white to-slate-50 border border-slate-100 p-8 shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                      Analyst's deep dive
                    </div>
                    <h4 className="font-display text-xl font-black text-slate-900">
                      The full story
                    </h4>
                  </div>
                </div>
                <div className="prose prose-sm max-w-none text-slate-700 leading-relaxed">
                  <ReactMarkdown>{report.summary}</ReactMarkdown>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-end text-[11px] text-slate-400">
                  <span className="flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Ask the chat anything about this comparison →
                  </span>
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DeviceCompare;
