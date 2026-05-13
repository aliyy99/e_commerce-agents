const fallbackSvg = encodeURIComponent(`
  <svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">
    <rect width="640" height="640" fill="#f8fafc"/>
    <rect x="96" y="96" width="448" height="448" rx="28" fill="#e2e8f0"/>
    <circle cx="248" cy="256" r="42" fill="#94a3b8"/>
    <path d="M144 464l120-136 72 84 78-64 82 116H144z" fill="#cbd5e1"/>
    <text x="320" y="542" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" fill="#64748b">
      Image unavailable
    </text>
  </svg>
`);

export const PRODUCT_IMAGE_FALLBACK = `data:image/svg+xml;charset=UTF-8,${fallbackSvg}`;
