// Discovery-page filter helpers. Derive filter options from the catalog,
// apply the user's selected filters to a product list, and expose the small
// spec-extraction primitives the sidebar uses for chip labels.

import { deriveCategory } from './productCategory';

const RAM_RE = /(\d+(?:\.\d+)?)\s*GB/i;
const STORAGE_RE = /(\d+(?:\.\d+)?)\s*(GB|TB)\b/i;

const parseFirstNumber = (str) => {
  const m = String(str ?? '').match(/(\d+(?:[.,]\d+)?)/);
  return m ? parseFloat(m[1].replace(',', '.')) : null;
};

function getSpec(product, label) {
  const list = Array.isArray(product?.specs) ? product.specs : [];
  const target = String(label).toLowerCase();
  const found = list.find((s) => String(s?.label || '').toLowerCase() === target);
  return found?.value ?? null;
}

export function getRam(product) {
  const raw = getSpec(product, 'RAM');
  const match = raw && raw.match(RAM_RE);
  return match ? `${parseInt(match[1], 10)} GB` : null;
}

export function getStorage(product) {
  const raw = getSpec(product, 'Storage');
  const match = raw && raw.match(STORAGE_RE);
  if (!match) return null;
  const value = parseFloat(match[1]);
  const unit = match[2].toUpperCase();
  return `${unit === 'TB' ? value : Math.round(value)} ${unit}`;
}

export function getMinPrice(product) {
  const prices = (product?.stores || [])
    .map((s) => Number(s?.price))
    .filter((n) => Number.isFinite(n) && n > 0);
  return prices.length ? Math.min(...prices) : null;
}

const storageWeight = (label) => {
  const n = parseFirstNumber(label) ?? 0;
  return /TB/i.test(label) ? n * 1024 : n;
};

export function extractFilterOptions(products) {
  const brands = new Set();
  const rams = new Set();
  const storages = new Set();
  const strategies = new Set();
  const categories = new Set();
  let priceMin = Infinity;
  let priceMax = 0;

  for (const p of products) {
    if (p.brand) brands.add(p.brand);
    const ram = getRam(p);
    if (ram) rams.add(ram);
    const storage = getStorage(p);
    if (storage) storages.add(storage);
    if (p.strategy) strategies.add(p.strategy);
    categories.add(deriveCategory(p));
    const mp = getMinPrice(p);
    if (mp != null) {
      priceMin = Math.min(priceMin, mp);
      priceMax = Math.max(priceMax, mp);
    }
  }

  return {
    brands: [...brands].sort(),
    rams: [...rams].sort((a, b) => (parseFirstNumber(a) ?? 0) - (parseFirstNumber(b) ?? 0)),
    storages: [...storages].sort((a, b) => storageWeight(a) - storageWeight(b)),
    strategies: [...strategies],
    categories: [...categories],
    priceMin: Number.isFinite(priceMin) ? Math.floor(priceMin) : 0,
    priceMax: Math.ceil(priceMax),
  };
}

export const EMPTY_DISCOVER_FILTERS = {
  category: null,
  brands: [],
  priceMin: null,
  priceMax: null,
  rams: [],
  storages: [],
  strategies: [],
};

export function applyDiscoverFilters(products, filters = EMPTY_DISCOVER_FILTERS) {
  const {
    category = null,
    brands = [],
    priceMin = null,
    priceMax = null,
    rams = [],
    storages = [],
    strategies = [],
  } = filters;

  return products.filter((p) => {
    if (category && deriveCategory(p) !== category) return false;
    if (brands.length && !brands.includes(p.brand)) return false;

    const mp = getMinPrice(p);
    if (priceMin != null && (mp == null || mp < priceMin)) return false;
    if (priceMax != null && (mp == null || mp > priceMax)) return false;

    if (rams.length) {
      const r = getRam(p);
      if (!r || !rams.includes(r)) return false;
    }
    if (storages.length) {
      const s = getStorage(p);
      if (!s || !storages.includes(s)) return false;
    }
    if (strategies.length) {
      if (!p.strategy || !strategies.includes(p.strategy)) return false;
    }
    return true;
  });
}

export function countActiveFilters(filters = EMPTY_DISCOVER_FILTERS) {
  let n = 0;
  if (filters.category) n += 1;
  if (filters.brands?.length) n += 1;
  if (filters.priceMin != null || filters.priceMax != null) n += 1;
  if (filters.rams?.length) n += 1;
  if (filters.storages?.length) n += 1;
  if (filters.strategies?.length) n += 1;
  return n;
}
