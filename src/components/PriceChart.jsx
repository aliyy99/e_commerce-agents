import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';

const formatPrice = (value, currency = 'TRY') => {
  if (value == null || Number.isNaN(value)) return '-';
  const rounded = Math.round(value);
  const formatted = rounded.toLocaleString('tr-TR');
  if (currency === 'TRY') return `${formatted} ₺`;
  return `${formatted} ${currency}`;
};

const buildSmoothPath = (points, getX, getY) => {
  if (points.length === 0) return '';
  if (points.length === 1) {
    const [p] = points;
    return `M ${getX(0)} ${getY(p.price)}`;
  }
  const path = [`M ${getX(0)} ${getY(points[0].price)}`];
  for (let i = 0; i < points.length - 1; i++) {
    const x0 = getX(i);
    const x1 = getX(i + 1);
    const y0 = getY(points[i].price);
    const y1 = getY(points[i + 1].price);
    const cx = (x0 + x1) / 2;
    path.push(`C ${cx} ${y0} ${cx} ${y1} ${x1} ${y1}`);
  }
  return path.join(' ');
};

const niceStep = (rawStep) => {
  if (rawStep <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const norm = rawStep / pow;
  let step;
  if (norm < 1.5) step = 1;
  else if (norm < 3) step = 2;
  else if (norm < 7) step = 5;
  else step = 10;
  return step * pow;
};

const buildYTicks = (minVal, maxVal, count = 5) => {
  if (minVal === maxVal) {
    const pad = Math.max(maxVal * 0.1, 1);
    minVal -= pad;
    maxVal += pad;
  }
  const step = niceStep((maxVal - minVal) / count);
  const start = Math.floor(minVal / step) * step;
  const end = Math.ceil(maxVal / step) * step;
  const ticks = [];
  for (let v = start; v <= end + step * 0.001; v += step) {
    ticks.push(Number(v.toFixed(2)));
  }
  return { ticks, niceMin: start, niceMax: end };
};

const PriceChart = ({ points = [], currency = 'TRY' }) => {
  const [hoverIdx, setHoverIdx] = useState(null);

  const view = useMemo(() => {
    const width = 760;
    const height = 360;
    const padding = { top: 28, right: 36, bottom: 56, left: 72 };
    const innerW = width - padding.left - padding.right;
    const innerH = height - padding.top - padding.bottom;

    if (points.length === 0) {
      return { width, height, padding, innerW, innerH };
    }

    const prices = points.map((p) => p.price);
    const minVal = Math.min(...prices);
    const maxVal = Math.max(...prices);
    const { ticks, niceMin, niceMax } = buildYTicks(minVal, maxVal, 5);

    const xStep = points.length > 1 ? innerW / (points.length - 1) : 0;
    const getX = (idx) => padding.left + idx * xStep;
    const getY = (price) =>
      padding.top + innerH - ((price - niceMin) / (niceMax - niceMin || 1)) * innerH;

    const linePath = buildSmoothPath(points, getX, getY);
    const areaPath = linePath
      ? `${linePath} L ${getX(points.length - 1)} ${padding.top + innerH} L ${getX(0)} ${padding.top + innerH} Z`
      : '';

    return {
      width,
      height,
      padding,
      innerW,
      innerH,
      getX,
      getY,
      linePath,
      areaPath,
      yTicks: ticks,
      niceMin,
      niceMax,
      minVal,
      maxVal,
    };
  }, [points]);

  if (points.length === 0) return null;

  const firstPrice = points[0].price;
  const lastPrice = points[points.length - 1].price;
  const delta = lastPrice - firstPrice;
  const deltaPct = firstPrice ? (delta / firstPrice) * 100 : 0;
  const isDown = delta < 0;
  const minPoint = points.reduce((acc, p) => (p.price < acc.price ? p : acc), points[0]);
  const maxPoint = points.reduce((acc, p) => (p.price > acc.price ? p : acc), points[0]);

  const labelEveryNth = points.length > 8 ? 2 : 1;
  const hover = hoverIdx != null ? points[hoverIdx] : null;

  return (
    <div className="w-full">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <div className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Current</p>
          <p className="text-xl font-black text-slate-900 mt-1">{formatPrice(lastPrice, currency)}</p>
          <p className={`text-[11px] font-bold mt-1 ${isDown ? 'text-emerald-500' : delta > 0 ? 'text-accent-rose' : 'text-slate-400'}`}>
            {isDown ? '▼' : delta > 0 ? '▲' : '■'} {Math.abs(deltaPct).toFixed(1)}% / 12 mo
          </p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Lowest</p>
          <p className="text-xl font-black text-emerald-500 mt-1">{formatPrice(minPoint.price, currency)}</p>
          <p className="text-[11px] font-bold text-slate-500 mt-1">{minPoint.label}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Highest</p>
          <p className="text-xl font-black text-accent-rose mt-1">{formatPrice(maxPoint.price, currency)}</p>
          <p className="text-[11px] font-bold text-slate-500 mt-1">{maxPoint.label}</p>
        </div>
        <div className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Average</p>
          <p className="text-xl font-black text-slate-900 mt-1">
            {formatPrice(points.reduce((s, p) => s + p.price, 0) / points.length, currency)}
          </p>
          <p className="text-[11px] font-bold text-slate-500 mt-1">{points.length} months</p>
        </div>
      </div>

      <div className="w-full overflow-hidden bg-white border border-slate-100 rounded-2xl shadow-sm p-5">
        <div className="relative w-full">
        <svg
          viewBox={`0 0 ${view.width} ${view.height}`}
          width="100%"
          className="block"
          preserveAspectRatio="xMidYMid meet"
          onMouseLeave={() => setHoverIdx(null)}
        >
          <defs>
            <linearGradient id="priceChartArea" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.35" />
              <stop offset="60%" stopColor="#6366f1" stopOpacity="0.1" />
              <stop offset="100%" stopColor="#6366f1" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="priceChartStroke" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#8b5cf6" />
            </linearGradient>
            <filter id="priceChartGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2" />
              <feMerge>
                <feMergeNode />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Y axis gridlines + labels */}
          {view.yTicks.map((tickValue) => {
            const y = view.getY(tickValue);
            return (
              <g key={tickValue}>
                <line
                  x1={view.padding.left}
                  x2={view.width - view.padding.right}
                  y1={y}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeDasharray="3 4"
                  strokeWidth="1"
                />
                <text
                  x={view.padding.left - 12}
                  y={y + 4}
                  textAnchor="end"
                  fontSize="11"
                  fontWeight="600"
                  fill="#94a3b8"
                >
                  {formatPrice(tickValue, currency)}
                </text>
              </g>
            );
          })}

          {/* Area fill */}
          <motion.path
            d={view.areaPath}
            fill="url(#priceChartArea)"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
          />

          {/* Line */}
          <motion.path
            d={view.linePath}
            fill="none"
            stroke="url(#priceChartStroke)"
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
            filter="url(#priceChartGlow)"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 1.1, ease: 'easeOut' }}
          />

          {/* Hover marker line */}
          {hoverIdx != null && (
            <line
              x1={view.getX(hoverIdx)}
              x2={view.getX(hoverIdx)}
              y1={view.padding.top}
              y2={view.padding.top + view.innerH}
              stroke="#6366f1"
              strokeOpacity="0.3"
              strokeDasharray="4 4"
            />
          )}

          {/* X axis labels */}
          {points.map((p, idx) => {
            if (idx % labelEveryNth !== 0 && idx !== points.length - 1) return null;
            const shortLabel = (p.label || p.month).split(' ');
            return (
              <text
                key={p.month}
                x={view.getX(idx)}
                y={view.height - view.padding.bottom + 22}
                textAnchor="middle"
                fontSize="11"
                fontWeight="700"
                fill="#64748b"
              >
                {shortLabel[0]?.slice(0, 3)}
                <tspan x={view.getX(idx)} dy="14" fill="#94a3b8" fontWeight="600">
                  {shortLabel[1] || ''}
                </tspan>
              </text>
            );
          })}

          {/* Point dots + hover hit area */}
          {points.map((p, idx) => {
            const x = view.getX(idx);
            const y = view.getY(p.price);
            const isActive = hoverIdx === idx;
            const isMin = p.month === minPoint.month;
            const isMax = p.month === maxPoint.month;
            return (
              <g key={p.month}>
                <circle
                  cx={x}
                  cy={y}
                  r={isActive ? 7 : isMin || isMax ? 6 : 4}
                  fill={isMin ? '#10b981' : isMax ? '#f43f5e' : '#ffffff'}
                  stroke={isMin ? '#10b981' : isMax ? '#f43f5e' : '#6366f1'}
                  strokeWidth={isActive ? 3 : 2.5}
                  style={{ transition: 'r 120ms ease' }}
                />
                <rect
                  x={x - 18}
                  y={view.padding.top}
                  width="36"
                  height={view.innerH}
                  fill="transparent"
                  onMouseEnter={() => setHoverIdx(idx)}
                />
              </g>
            );
          })}
        </svg>

        {/* Hover tooltip */}
        {hover && view.getX && (
          <div
            className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full bg-slate-900 text-white text-xs font-bold px-3 py-2 rounded-xl shadow-lg whitespace-nowrap"
            style={{
              left: `${(view.getX(hoverIdx) / view.width) * 100}%`,
              top: `calc(${(view.getY(hover.price) / view.height) * 100}% - 8px)`,
            }}
          >
            <div className="text-[10px] uppercase tracking-widest text-slate-300 mb-0.5">{hover.label}</div>
            <div className="text-sm font-black">{formatPrice(hover.price, currency)}</div>
            {hover.note && <div className="text-[10px] text-slate-300 font-medium mt-1 max-w-[220px] whitespace-normal">{hover.note}</div>}
          </div>
        )}
        </div>
      </div>
    </div>
  );
};

export default PriceChart;
