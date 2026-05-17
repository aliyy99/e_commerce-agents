import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  ShieldCheck, ShieldAlert, AlertTriangle, EyeOff, Quote, Sparkles,
  ThumbsUp, ThumbsDown, Trophy, Flame, Award, TrendingDown, ExternalLink,
  CheckCircle2, XCircle, Globe,
} from 'lucide-react';

const VERDICT_META = {
  BUY: {
    label: 'AL',
    sublabel: 'Strong buy signal',
    icon: Trophy,
    gradient: 'linear-gradient(135deg, #059669, #047857)',
    chip: 'bg-emerald-500/20 text-emerald-100 border-emerald-300/40',
  },
  WAIT: {
    label: 'BEKLE',
    sublabel: 'Hold and reassess',
    icon: TrendingDown,
    gradient: 'linear-gradient(135deg, #f59e0b, #d97706)',
    chip: 'bg-amber-500/20 text-amber-100 border-amber-300/40',
  },
  AVOID: {
    label: 'KAÇIN',
    sublabel: 'Skip this purchase',
    icon: ShieldAlert,
    gradient: 'linear-gradient(135deg, #e11d48, #be123c)',
    chip: 'bg-rose-500/20 text-rose-100 border-rose-300/40',
  },
};

const SEVERITY_META = {
  high:   { color: '#e11d48', label: 'HIGH', tint: 'bg-rose-50 text-rose-700 border-rose-100' },
  medium: { color: '#f59e0b', label: 'MEDIUM', tint: 'bg-amber-50 text-amber-700 border-amber-100' },
  low:    { color: '#64748b', label: 'LOW', tint: 'bg-slate-100 text-slate-600 border-slate-200' },
};

const TrustGauge = ({ trust }) => {
  const score = Math.max(0, Math.min(100, trust?.trust_score ?? 0));
  // Smooth red → amber → emerald gradient based on score.
  const color =
    score >= 75 ? '#059669' :
    score >= 50 ? '#f59e0b' :
                  '#e11d48';
  const ringSize = 140;
  const stroke = 12;
  const radius = (ringSize - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - score / 100);

  return (
    <div className="flex items-center gap-5">
      <div className="relative" style={{ width: ringSize, height: ringSize }}>
        <svg width={ringSize} height={ringSize} className="-rotate-90">
          <circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            stroke="#f1f5f9"
            strokeWidth={stroke}
            fill="none"
          />
          <motion.circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.1, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-3xl font-display font-black" style={{ color }}>
            {score}
          </div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
            Trust score
          </div>
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-display text-lg font-black text-slate-900 mb-2">
          Review trust pool
        </h4>
        <div className="space-y-2">
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold mb-1">
              <span className="text-emerald-600">ORGANIC</span>
              <span className="text-slate-700">{trust?.organic_pct ?? 0}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${trust?.organic_pct ?? 0}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
                className="h-full bg-emerald-500 rounded-full"
              />
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between text-[11px] font-bold mb-1">
              <span className="text-rose-600">SUSPICIOUS</span>
              <span className="text-slate-700">{trust?.suspicious_pct ?? 0}%</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${trust?.suspicious_pct ?? 0}%` }}
                transition={{ duration: 1, ease: 'easeOut' }}
                className="h-full bg-rose-500 rounded-full"
              />
            </div>
          </div>
        </div>
        <div className="text-[11px] text-slate-500 mt-3">
          Based on <b className="text-slate-700">{trust?.total_reviews_seen ?? 0}</b> reviews analysed across sites.
        </div>
      </div>
    </div>
  );
};

const Section = ({ icon: Icon, accent, title, count, children }) => (
  <div className="rounded-3xl bg-white border border-slate-100 shadow-sm overflow-hidden">
    <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50/70 to-white">
      <div
        className="w-10 h-10 rounded-xl flex items-center justify-center"
        style={{ background: `${accent}15`, color: accent, border: `1px solid ${accent}30` }}
      >
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1">
        <h4 className="font-display text-lg font-black text-slate-900 leading-tight">{title}</h4>
      </div>
      {count != null && (
        <span
          className="px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider"
          style={{ background: `${accent}15`, color: accent }}
        >
          {count}
        </span>
      )}
    </div>
    <div className="p-6">{children}</div>
  </div>
);

const AnalystReport = ({ analysis, modelUsed }) => {
  const verdict = VERDICT_META[analysis?.verdict] || VERDICT_META.WAIT;
  const VerdictIcon = verdict.icon;
  const confidencePct = Math.round(((analysis?.confidence ?? 0.5) * 100));

  const sortedSites = useMemo(() => {
    const sites = Array.isArray(analysis?.site_summaries) ? [...analysis.site_summaries] : [];
    return sites.sort((a, b) => {
      const ap = typeof a.price === 'number' ? a.price : Infinity;
      const bp = typeof b.price === 'number' ? b.price : Infinity;
      return ap - bp;
    });
  }, [analysis?.site_summaries]);

  if (!analysis) return null;

  return (
    <div className="space-y-6">
      {/* Verdict banner */}
      <div
        className="relative rounded-3xl overflow-hidden p-7 text-white"
        style={{ background: verdict.gradient }}
      >
        <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/10 blur-3xl" />
        <div className="relative flex flex-col md:flex-row md:items-center gap-6">
          <div className="w-16 h-16 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center flex-shrink-0">
            <VerdictIcon className="w-8 h-8 text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2.5 py-1 rounded-full text-[10px] font-black tracking-widest border ${verdict.chip}`}>
                {verdict.label}
              </span>
              <span className="text-[11px] font-bold opacity-80">
                {verdict.sublabel} · confidence {confidencePct}%
              </span>
            </div>
            <h3 className="font-display text-2xl font-black leading-tight">
              {analysis.headline}
            </h3>
            {analysis.cheapest_site && analysis.cheapest_price != null && (
              <div className="mt-3 inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/15 backdrop-blur text-[12px] font-bold">
                <Award className="w-3.5 h-3.5" />
                Cheapest: <span className="opacity-90">{analysis.cheapest_site}</span>
                <span>· {Math.round(analysis.cheapest_price).toLocaleString()} TL</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Trust + Site strip */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-6">
        <div className="rounded-3xl bg-white border border-slate-100 shadow-sm p-6">
          <TrustGauge trust={analysis.trust_report} />
          {(analysis.trust_report?.suspicious_signals || []).length > 0 && (
            <div className="mt-5 pt-4 border-t border-slate-100">
              <div className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">
                Suspicious patterns
              </div>
              <div className="flex flex-wrap gap-1.5">
                {analysis.trust_report.suspicious_signals.map((s, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-full bg-rose-50 border border-rose-100 text-rose-700 text-[11px] font-bold">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-3xl bg-white border border-slate-100 shadow-sm p-6">
          <h4 className="font-display text-lg font-black text-slate-900 mb-4">Site comparison</h4>
          <div className="space-y-2.5">
            {sortedSites.length === 0 ? (
              <div className="text-sm text-slate-400">No site data captured.</div>
            ) : sortedSites.map((s, i) => {
              const isCheapest = i === 0 && typeof s.price === 'number';
              return (
                <div
                  key={`${s.site}-${i}`}
                  className={`flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border transition-colors ${
                    isCheapest ? 'bg-emerald-50 border-emerald-200' : 'bg-slate-50 border-slate-100'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {isCheapest && (
                      <Award className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                    )}
                    <span className="font-bold text-sm text-slate-900 truncate">{s.site}</span>
                    {typeof s.rating === 'number' && (
                      <span className="text-[11px] text-slate-500 font-bold">★ {s.rating.toFixed(1)}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    {typeof s.price === 'number' && (
                      <span className="font-black text-sm text-slate-900">
                        {Math.round(s.price).toLocaleString()} TL
                      </span>
                    )}
                    {s.url && (
                      <a
                        href={s.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="w-7 h-7 rounded-lg bg-white border border-slate-200 flex items-center justify-center text-slate-500 hover:text-primary hover:border-primary transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Red flags */}
      {(analysis.red_flags || []).length > 0 && (
        <div className="rounded-3xl bg-rose-50 border border-rose-100 p-5">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-xl bg-rose-100 flex items-center justify-center text-rose-600 flex-shrink-0">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <h4 className="font-display text-lg font-black text-rose-700">Red flags</h4>
              <ul className="mt-2 space-y-1">
                {analysis.red_flags.map((rf, i) => (
                  <li key={i} className="text-sm text-rose-700 flex gap-2">
                    <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                    <span>{rf}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Blind spots */}
      {(analysis.blind_spots || []).length > 0 && (
        <Section
          icon={EyeOff}
          accent="#6366f1"
          title="Blind spots — what the seller doesn't tell you"
          count={analysis.blind_spots.length}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {analysis.blind_spots.map((bs, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="rounded-2xl border border-slate-100 bg-gradient-to-br from-indigo-50/40 to-white p-4"
              >
                <div className="text-[10px] font-black uppercase tracking-widest text-indigo-600 mb-1">
                  Marketing says
                </div>
                <div className="text-sm font-bold text-slate-900 mb-3">{bs.claim}</div>
                <div className="text-[10px] font-black uppercase tracking-widest text-slate-500 mb-1">
                  Reality
                </div>
                <div className="text-sm text-slate-600 leading-relaxed">{bs.reality}</div>
                <div className="mt-3 text-[10px] text-slate-400 font-bold">
                  Source: {bs.source}
                </div>
              </motion.div>
            ))}
          </div>
        </Section>
      )}

      {/* Chronic issues */}
      {(analysis.chronic_issues || []).length > 0 && (
        <Section
          icon={Flame}
          accent="#e11d48"
          title="Chronic issues — what keeps coming up"
          count={analysis.chronic_issues.length}
        >
          <div className="space-y-3">
            {analysis.chronic_issues.map((ci, i) => {
              const sev = SEVERITY_META[ci.severity] || SEVERITY_META.medium;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="rounded-2xl border border-slate-100 p-4 bg-white"
                >
                  <div className="flex items-start gap-3">
                    <div
                      className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: `${sev.color}15`, color: sev.color }}
                    >
                      <Flame className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-bold text-sm text-slate-900">{ci.issue}</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-black tracking-wider border ${sev.tint}`}>
                          {sev.label}
                        </span>
                        <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold">
                          ×{ci.frequency} reviews
                        </span>
                      </div>
                      {(ci.evidence || []).length > 0 && (
                        <ul className="mt-2 space-y-1">
                          {ci.evidence.map((q, qi) => (
                            <li key={qi} className="text-xs text-slate-500 flex gap-1.5 leading-relaxed">
                              <Quote className="w-3 h-3 mt-0.5 flex-shrink-0 text-slate-300" />
                              <span className="italic">"{q}"</span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </Section>
      )}

      {/* Honest pros / cons */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Section
          icon={ThumbsUp}
          accent="#059669"
          title="3 genuinely good things"
          count={(analysis.honest_pros || []).length}
        >
          <ul className="space-y-3">
            {(analysis.honest_pros || []).map((p, i) => (
              <li key={i} className="flex gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm text-slate-900">{p.label}</div>
                  <div className="text-xs text-slate-600 leading-relaxed mt-0.5">{p.explanation}</div>
                  {p.evidence && (
                    <div className="mt-1.5 text-[11px] italic text-slate-400 border-l-2 border-emerald-200 pl-2">
                      "{p.evidence}"
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>

        <Section
          icon={ThumbsDown}
          accent="#e11d48"
          title="3 things you'll have to live with"
          count={(analysis.honest_cons || []).length}
        >
          <ul className="space-y-3">
            {(analysis.honest_cons || []).map((p, i) => (
              <li key={i} className="flex gap-3">
                <XCircle className="w-5 h-5 text-rose-500 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold text-sm text-slate-900">{p.label}</div>
                  <div className="text-xs text-slate-600 leading-relaxed mt-0.5">{p.explanation}</div>
                  {p.evidence && (
                    <div className="mt-1.5 text-[11px] italic text-slate-400 border-l-2 border-rose-200 pl-2">
                      "{p.evidence}"
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      </div>

      {/* Grounding sources */}
      {(analysis.grounding_sources || []).length > 0 && (
        <div className="rounded-3xl bg-white border border-slate-100 shadow-sm p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-sky-50 border border-sky-100 text-sky-600 flex items-center justify-center">
              <Globe className="w-5 h-5" />
            </div>
            <div className="flex-1">
              <div className="text-[10px] font-black uppercase tracking-widest text-sky-600">
                Google Search ile doğrulandı
              </div>
              <h4 className="font-display text-lg font-black text-slate-900">Kaynaklar</h4>
            </div>
            <span className="px-2.5 py-1 rounded-full text-[10px] font-black tracking-wider bg-sky-50 text-sky-700">
              {analysis.grounding_sources.length}
            </span>
          </div>
          <ul className="space-y-1.5">
            {analysis.grounding_sources.map((src, i) => (
              <li key={i}>
                <a
                  href={src.uri}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-slate-50 text-sm text-slate-700 hover:text-primary transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />
                  <span className="truncate">{src.title || src.uri}</span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Final recommendation */}
      {analysis.final_recommendation && (
        <div className="rounded-3xl bg-gradient-to-br from-slate-900 to-slate-800 text-white p-7">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-white/10 backdrop-blur flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="text-[10px] font-black uppercase tracking-widest text-emerald-300">
                Analyst's verdict
              </div>
              <h4 className="font-display text-xl font-black">Final recommendation</h4>
            </div>
          </div>
          <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">
            {analysis.final_recommendation}
          </div>
          {modelUsed && (
            <div className="mt-5 pt-4 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-400">
              <span>Model: <span className="font-bold text-slate-200">{modelUsed}</span></span>
              <span className="flex items-center gap-1">
                <Sparkles className="w-3 h-3" /> Ask the chat for follow-ups →
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default AnalystReport;
