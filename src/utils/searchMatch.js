// ──────────────────────────────────────────────────────────────
// Token-based fuzzy matching for product search.
// Handles cases like "samsung s24" → "Samsung Galaxy S24 256 GB"
// by checking that every meaningful query token appears anywhere
// in the product name/description.
// ──────────────────────────────────────────────────────────────

const STOP = new Set(['the', 'a', 'an', 'and', 'for', 'with', 'of']);

function tokenize(str) {
  return (str || '')
    .toLowerCase()
    .replace(/[^a-z0-9çğıöşü\s]/gi, ' ')
    .split(/\s+/)
    .filter((t) => t && !STOP.has(t));
}

export function matchesQuery(query, product) {
  const qTokens = tokenize(query);
  if (qTokens.length === 0) return false;

  const haystack = `${product.name} ${product.brand || ''} ${product.description || ''}`.toLowerCase();
  const hayTokens = new Set(tokenize(haystack));

  return qTokens.every((t) => {
    if (hayTokens.has(t)) return true;
    // substring fallback: "s24" within "Samsung Galaxy S24 256 GB"
    return haystack.includes(t);
  });
}

export function filterProducts(query, products) {
  if (!query || !query.trim()) return products;
  return products.filter((p) => matchesQuery(query, p));
}

export function findBestProductMatch(query, products) {
  const q = (query || '').toLowerCase().trim();
  if (!q) return null;

  // 1. exact name
  const exact = products.find((p) => p.name.toLowerCase() === q);
  if (exact) return exact;

  // 2. substring either way
  const substring = products.find(
    (p) => p.name.toLowerCase().includes(q) || q.includes(p.name.toLowerCase()),
  );
  if (substring) return substring;

  // 3. token-overlap: pick highest overlap above threshold
  const qTokens = tokenize(query);
  if (qTokens.length === 0) return null;

  let best = null;
  let bestScore = 0;
  for (const product of products) {
    const hayTokens = new Set(tokenize(`${product.name} ${product.brand || ''}`));
    let hits = 0;
    for (const t of qTokens) {
      if (hayTokens.has(t)) hits += 1;
      else if (`${product.name} ${product.brand || ''}`.toLowerCase().includes(t)) hits += 1;
    }
    const score = hits / qTokens.length;
    if (score > bestScore) {
      bestScore = score;
      best = product;
    }
  }
  return bestScore >= 0.6 ? best : null;
}

// ──────────────────────────────────────────────────────────────
// Google-style varied autocomplete suggestions.
// Produces a mix of: product variants, comparisons, intent phrases
// (price, review, buy advice, alternatives, accessories).
// ──────────────────────────────────────────────────────────────

const INTENT_TEMPLATES_TR = [
  '{q} price',
  '{q} review',
  '{q} user reviews',
  '{q} when to buy',
  '{q} deals',
  '{q} specs',
  '{q} user experience',
  '{q} best price',
];

const INTENT_TEMPLATES_EN = [
  '{q} review',
  '{q} price',
  '{q} vs',
  '{q} specs',
  '{q} best deal',
  '{q} alternatives',
];

const COMPARISON_PAIRS = {
  'samsung galaxy s24': ['iPhone 15', 'Google Pixel 8'],
  'iphone 15': ['Samsung Galaxy S24', 'Google Pixel 8'],
  'macbook air': ['MacBook Pro', 'Dell XPS 13'],
  'playstation 5': ['Xbox Series X', 'Nintendo Switch OLED'],
};

function pickComparison(query) {
  const q = query.toLowerCase().trim();
  for (const key of Object.keys(COMPARISON_PAIRS)) {
    if (q.includes(key)) return COMPARISON_PAIRS[key];
  }
  return [];
}

export function buildSuggestions(query, catalog, productNames, max = 7) {
  if (!query || query.length < 2) return [];
  const q = query.toLowerCase().trim();

  const seen = new Set();
  const out = [];
  const push = (s) => {
    const key = s.toLowerCase();
    if (!key || seen.has(key) || key === q) return;
    seen.add(key);
    out.push(s);
  };

  // 1. Real catalog products that match the query (highest priority)
  for (const p of catalog) {
    if (out.length >= max) break;
    if (matchesQuery(query, p)) push(p.name);
  }

  // 2. Curated product-name database (substring match on tokens)
  for (const name of productNames) {
    if (out.length >= max) break;
    const tokensIn = tokenize(query);
    if (tokensIn.every((t) => name.toLowerCase().includes(t))) {
      push(name);
    }
  }

  // 3. Intent phrases (Google-style): price, review, when to buy, etc.
  const baseForIntent = out[0] || query;
  for (const tpl of INTENT_TEMPLATES_TR) {
    if (out.length >= max) break;
    push(tpl.replace('{q}', baseForIntent));
  }
  for (const tpl of INTENT_TEMPLATES_EN) {
    if (out.length >= max) break;
    push(tpl.replace('{q}', baseForIntent));
  }

  // 4. Comparisons ("X vs Y")
  for (const other of pickComparison(baseForIntent)) {
    if (out.length >= max) break;
    push(`${baseForIntent} vs ${other}`);
  }

  return out.slice(0, max);
}
