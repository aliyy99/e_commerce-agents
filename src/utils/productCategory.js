// Category derivation for the Device Comparison page.
// We only allow two devices in the SAME category to be compared.
//
// Categories: smartphone | laptop | tablet | wearable | headphones | console | tv | accessory

export const CATEGORY_META = {
  smartphone: { label: 'Smartphones',  icon: '📱', accent: '#0ea5e9' },
  laptop:     { label: 'Laptops',      icon: '💻', accent: '#8b5cf6' },
  tablet:     { label: 'Tablets',      icon: '🖥️', accent: '#10b981' },
  wearable:   { label: 'Wearables',    icon: '⌚', accent: '#f59e0b' },
  headphones: { label: 'Headphones',   icon: '🎧', accent: '#ec4899' },
  console:    { label: 'Game Consoles',icon: '🎮', accent: '#ef4444' },
  tv:         { label: 'TVs',          icon: '📺', accent: '#6366f1' },
  accessory:  { label: 'Accessories',  icon: '🧩', accent: '#64748b' },
};

const RULES = [
  { cat: 'tablet',     re: /\b(tab|tablet|ipad)\b/i },
  { cat: 'laptop',     re: /\b(macbook|laptop|notebook|xps|thinkpad|zenbook|ideapad|surface\s*laptop)\b/i },
  { cat: 'wearable',   re: /\b(watch|band|fitbit|smartwatch)\b/i },
  { cat: 'headphones', re: /\b(airpods|headphones?|earbuds|buds|wh-\d+|wf-\d+|quietcomfort)\b/i },
  { cat: 'console',    re: /\b(playstation|xbox|nintendo|switch|steam\s*deck)\b/i },
  { cat: 'tv',         re: /\b(tv|oled|qled|television)\b/i },
  { cat: 'smartphone', re: /\b(iphone|galaxy\s*(s|z|note|a|m)|pixel|xiaomi|redmi|oneplus|honor|huawei|nothing\s*phone|smartphone|telefon)\b/i },
];

export function deriveCategory(product) {
  if (!product) return 'accessory';
  if (product.category) return product.category;

  const haystacks = [
    product.name,
    product.nameTemplate,
    product.brand,
    ...(Array.isArray(product.specs) ? product.specs.map((s) => `${s?.label} ${s?.value}`) : []),
  ].filter(Boolean).join(' ');

  for (const rule of RULES) {
    if (rule.re.test(haystacks)) return rule.cat;
  }
  return 'accessory';
}

export function groupProductsByCategory(products) {
  const out = {};
  for (const p of products) {
    const cat = deriveCategory(p);
    (out[cat] ||= []).push(p);
  }
  return out;
}
