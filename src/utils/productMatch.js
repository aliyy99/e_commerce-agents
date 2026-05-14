// ──────────────────────────────────────────────────────────────
// Vision-to-catalog matching helpers.
// Given a Vision Agent response, find the best-matching product in
// our catalog. Returns null when nothing matches well enough.
// ──────────────────────────────────────────────────────────────

const STOPWORDS = new Set([
  'the', 'a', 'an', 'with', 'for', 'and', 'of', 'gb', 'tb', 'ram',
  'ssd', 'inch', 'pro', 'max', 'ultra', 'plus',
]);

function tokens(str) {
  return (str || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, ' ')
    .split(/\s+/)
    .filter((t) => t && !STOPWORDS.has(t));
}

function overlapScore(a, b) {
  if (!a.length || !b.length) return 0;
  const setB = new Set(b);
  let hits = 0;
  for (const t of a) if (setB.has(t)) hits += 1;
  return hits / a.length;
}

export function matchProductFromVision(vision, catalog) {
  if (!vision || !Array.isArray(catalog) || catalog.length === 0) return null;

  const candidates = [
    vision.product_name,
    vision.search_keywords,
  ]
    .filter(Boolean)
    .map((s) => s.trim())
    .filter(Boolean);

  if (candidates.length === 0) return null;

  let best = null;
  let bestScore = 0;

  for (const product of catalog) {
    const productTokens = tokens(product.name);
    for (const candidate of candidates) {
      const candidateTokens = tokens(candidate);
      const score = overlapScore(candidateTokens, productTokens);
      if (score > bestScore) {
        bestScore = score;
        best = product;
      }
    }
  }

  // Require at least ~50% of meaningful candidate tokens to overlap.
  if (bestScore >= 0.5) return best;
  return null;
}

export function brandKeyFromVision(vision, brandModels) {
  if (!vision?.brand) return null;
  const b = vision.brand.toLowerCase();
  for (const key of Object.keys(brandModels)) {
    if (key.toLowerCase() === b) return key;
  }
  // Soft match (e.g. "Apple Inc." → "Apple")
  for (const key of Object.keys(brandModels)) {
    if (b.includes(key.toLowerCase())) return key;
  }
  return null;
}
