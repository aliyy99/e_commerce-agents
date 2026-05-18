// ──────────────────────────────────────────────────────────────
// Vision-to-catalog matching helpers.
// Given a Vision Agent response, find the best-matching product in
// our catalog. Returns null when nothing matches well enough — at
// which point App.jsx hands off to the disambiguation modal or to
// a regular text search, so we never silently force-select a wrong
// product.
// ──────────────────────────────────────────────────────────────

// Intentionally TINY stop-list. Keep ``pro``, ``max``, ``ultra``, ``plus``,
// ``gb``, ``tb`` as real tokens — they're the very words that disambiguate
// Galaxy S24 from S24 Ultra, MacBook Air from MacBook Pro, etc.
const STOPWORDS = new Set([
  'the', 'a', 'an', 'with', 'for', 'and', 'of', 'inch', 'ram',
]);

// Minimum vision confidence we trust for a direct auto-select. Below this we
// hand off to the disambiguation modal so the user picks the actual model.
export const VISION_AUTO_MATCH_MIN_CONFIDENCE = 0.55;

// Colour vocabulary: maps every form the model (or the user's locale) could
// emit to a canonical English token used by our variant `shortValue`s.
// Includes Turkish synonyms so a TR-locale vision response still resolves.
const COLOR_SYNONYMS = {
  black:    ['black', 'siyah', 'graphite', 'grafit', 'space black', 'jet black', 'midnight', 'gece yarisi'],
  white:    ['white', 'beyaz', 'silver', 'gumus', 'starlight', 'yildiz isigi'],
  blue:     ['blue', 'mavi', 'navy', 'lacivert', 'sierra blue', 'pacific blue', 'titanium blue'],
  pink:     ['pink', 'pembe', 'rose', 'rose gold', 'gul', 'gül'],
  yellow:   ['yellow', 'sari', 'sarı', 'gold', 'altin', 'altın'],
  green:    ['green', 'yesil', 'yeşil', 'alpine green', 'mint'],
  red:      ['red', 'kirmizi', 'kırmızı', '(product)red', 'productred'],
  purple:   ['purple', 'mor', 'lila', 'deep purple'],
  orange:   ['orange', 'turuncu'],
  titanium: ['titanium', 'titanyum', 'natural titanium'],
};

function normalizeColorToken(value) {
  if (!value) return null;
  const lower = String(value).toLowerCase().trim();
  if (!lower) return null;
  for (const [canonical, synonyms] of Object.entries(COLOR_SYNONYMS)) {
    if (synonyms.some((s) => lower === s || lower.includes(s))) return canonical;
  }
  return lower; // fall back to the raw token — option matching does a contains check below.
}

/**
 * Given a catalog product and a Vision response, pick the option shortValue
 * for each variant group that best matches the detected attributes. Today
 * this resolves the Color group via the vision agent's `color` field; in the
 * future we can extend it to RAM/Storage if the model reliably reads labels.
 *
 * Returns an object like { Color: 'White' } that can be fed directly into
 * ProductAnalysis's variantSelection state. Returns `null` if there are no
 * variants we can confidently override.
 */
export function pickInitialVariantSelection(product, vision) {
  if (!product?.variants?.length || !vision) return null;
  const target = normalizeColorToken(vision.color);
  if (!target) return null;

  const selection = {};
  for (const group of product.variants) {
    if ((group.label || '').toLowerCase() !== 'color') continue;
    let bestOption = null;
    for (const opt of group.options) {
      const optCanonical = normalizeColorToken(opt.shortValue) || normalizeColorToken(opt.value);
      if (!optCanonical) continue;
      // Direct canonical hit wins immediately.
      if (optCanonical === target) {
        bestOption = opt;
        break;
      }
      // Fuzzy contains both ways: covers "Sierra Blue" → "blue" etc.
      if (!bestOption && (optCanonical.includes(target) || target.includes(optCanonical))) {
        bestOption = opt;
      }
    }
    if (bestOption) selection[group.label] = bestOption.shortValue;
  }
  return Object.keys(selection).length ? selection : null;
}

function tokens(str) {
  return (str || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .split(/\s+/)
    .filter((t) => t && !STOPWORDS.has(t));
}

function brandKey(value) {
  return String(value || '').toLowerCase().trim();
}

function brandsMatch(visionBrand, productBrand) {
  const a = brandKey(visionBrand);
  const b = brandKey(productBrand);
  if (!a || !b) return null; // unknown either side → caller decides
  return a === b || a.includes(b) || b.includes(a);
}

function overlap(candidate, productTokens) {
  if (!candidate.length || !productTokens.length) {
    return { score: 0, hits: 0 };
  }
  const set = new Set(productTokens);
  let hits = 0;
  for (const t of candidate) if (set.has(t)) hits += 1;
  return { score: hits / candidate.length, hits };
}

export function matchProductFromVision(vision, catalog) {
  if (!vision || !Array.isArray(catalog) || catalog.length === 0) return null;

  // Low-confidence vision output shouldn't silently force a catalog hit —
  // the model itself is admitting it doesn't know the model.
  const confidence = typeof vision.confidence === 'number' ? vision.confidence : 1.0;
  if (confidence < VISION_AUTO_MATCH_MIN_CONFIDENCE) return null;

  const candidates = [vision.product_name, vision.search_keywords]
    .filter(Boolean)
    .map((s) => String(s).trim())
    .filter(Boolean);
  if (candidates.length === 0) return null;

  let best = null;
  let bestScore = 0;
  let bestHits = 0;

  for (const product of catalog) {
    // Brand gate: if the vision agent named a brand AND the product also has
    // a brand, they must match. Skips the classic failure mode where a Sony
    // headphone hits "Samsung Galaxy" because the overlap accidentally favours
    // generic tokens like "wireless" / "black".
    const bm = brandsMatch(vision.brand, product.brand);
    if (bm === false) continue;

    const productTokens = tokens(product.name);
    for (const candidate of candidates) {
      const candTokens = tokens(candidate);
      if (candTokens.length < 2) continue; // need real signal
      const { score, hits } = overlap(candTokens, productTokens);
      // Require at least 2 token hits — a single common word ("apple") is not
      // enough to commit to a catalog row.
      if (hits >= 2 && score > bestScore) {
        bestScore = score;
        bestHits = hits;
        best = product;
      }
    }
  }

  // When the vision agent supplied a confident brand, require a 65% overlap.
  // Without a brand to anchor on, demand a much tighter 80% match.
  const visionBrandKnown = !!brandKey(vision.brand);
  const threshold = visionBrandKnown ? 0.65 : 0.8;
  if (bestScore >= threshold && bestHits >= 2) return best;
  return null;
}

export function brandKeyFromVision(vision, brandModels) {
  if (!vision?.brand) return null;
  const b = brandKey(vision.brand);
  for (const key of Object.keys(brandModels)) {
    if (key.toLowerCase() === b) return key;
  }
  // Soft match (e.g. "Apple Inc." → "Apple"). Two-way containment catches
  // both "Apple Inc" → "Apple" and brand → expanded forms.
  for (const key of Object.keys(brandModels)) {
    const k = key.toLowerCase();
    if (b.includes(k) || k.includes(b)) return key;
  }
  return null;
}
