import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RotateCcw, SlidersHorizontal, ChevronDown } from 'lucide-react';
import { countActiveFilters } from '../utils/productFilters';

const Section = ({ title, children }) => (
  <div className="min-w-0">
    <h4 className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-2">
      {title}
    </h4>
    {children}
  </div>
);

const Chip = ({ active, onClick, children }) => (
  <button
    type="button"
    onClick={onClick}
    className={`px-2.5 py-1 rounded-full text-[11px] font-bold transition-all whitespace-nowrap ${
      active
        ? 'bg-primary text-white shadow-sm'
        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
    }`}
  >
    {children}
  </button>
);

const toggle = (arr, value) =>
  arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];

const DiscoverFilters = ({ options, filters, onChange, onReset }) => {
  const active = countActiveFilters(filters);
  // Auto-open when the user already has filters active so they can see what's
  // being applied at a glance; otherwise keep the panel compact by default.
  const [isOpen, setIsOpen] = useState(active > 0);

  const setArr = (key, value) =>
    onChange({ ...filters, [key]: toggle(filters[key] || [], value) });

  return (
    <div className="bg-white border border-slate-100 rounded-2xl shadow-sm overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-expanded={isOpen}
        className="w-full flex items-center justify-between gap-3 p-5 text-left hover:bg-slate-50/60 transition-colors"
      >
        <h3 className="font-display font-black text-slate-900 flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-primary" />
          Filters
          {active > 0 && (
            <span className="ml-1 px-1.5 py-0.5 bg-primary/10 text-primary text-[10px] font-black rounded-full">
              {active}
            </span>
          )}
        </h3>
        <div className="flex items-center gap-3">
          {active > 0 && (
            <span
              role="button"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                onReset();
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  e.stopPropagation();
                  onReset();
                }
              }}
              className="text-[11px] font-bold text-slate-400 hover:text-primary inline-flex items-center gap-1 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-3 h-3" /> Reset
            </span>
          )}
          <motion.span
            animate={{ rotate: isOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="w-7 h-7 rounded-lg bg-slate-100 text-slate-500 flex items-center justify-center"
          >
            <ChevronDown className="w-4 h-4" />
          </motion.span>
        </div>
      </button>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            key="filters-body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 pt-1 border-t border-slate-100">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-x-6 gap-y-5 pt-4">
                {options.brands.length > 0 && (
                  <Section title="Brand">
                    <div className="flex flex-wrap gap-1.5">
                      {options.brands.map((b) => (
                        <Chip key={b} active={(filters.brands || []).includes(b)} onClick={() => setArr('brands', b)}>
                          {b}
                        </Chip>
                      ))}
                    </div>
                  </Section>
                )}

                <Section title="Price range (₺)">
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      inputMode="numeric"
                      placeholder="Min"
                      value={filters.priceMin ?? ''}
                      onChange={(e) =>
                        onChange({
                          ...filters,
                          priceMin: e.target.value === '' ? null : Number(e.target.value),
                        })
                      }
                      className="w-full min-w-0 px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary/50"
                    />
                    <span className="text-slate-300 text-xs">–</span>
                    <input
                      type="number"
                      inputMode="numeric"
                      placeholder="Max"
                      value={filters.priceMax ?? ''}
                      onChange={(e) =>
                        onChange({
                          ...filters,
                          priceMax: e.target.value === '' ? null : Number(e.target.value),
                        })
                      }
                      className="w-full min-w-0 px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg outline-none focus:border-primary/50"
                    />
                  </div>
                  {options.priceMax > 0 && (
                    <div className="text-[10px] text-slate-400 mt-1.5">
                      Catalog: {options.priceMin.toLocaleString('en-US')} – {options.priceMax.toLocaleString('en-US')} ₺
                    </div>
                  )}
                </Section>

                {options.rams.length > 0 && (
                  <Section title="RAM">
                    <div className="flex flex-wrap gap-1.5">
                      {options.rams.map((r) => (
                        <Chip key={r} active={(filters.rams || []).includes(r)} onClick={() => setArr('rams', r)}>
                          {r}
                        </Chip>
                      ))}
                    </div>
                  </Section>
                )}

                {options.storages.length > 0 && (
                  <Section title="Storage">
                    <div className="flex flex-wrap gap-1.5">
                      {options.storages.map((s) => (
                        <Chip key={s} active={(filters.storages || []).includes(s)} onClick={() => setArr('storages', s)}>
                          {s}
                        </Chip>
                      ))}
                    </div>
                  </Section>
                )}

                {options.strategies.length > 0 && (
                  <Section title="Buy recommendation">
                    <div className="flex flex-wrap gap-1.5">
                      {options.strategies.map((s) => (
                        <Chip key={s} active={(filters.strategies || []).includes(s)} onClick={() => setArr('strategies', s)}>
                          {s}
                        </Chip>
                      ))}
                    </div>
                  </Section>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default DiscoverFilters;
