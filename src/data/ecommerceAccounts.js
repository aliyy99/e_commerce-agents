// Single source of truth for the e-commerce accounts the user has linked
// to Techno Track. The Profile page lets the user toggle these on/off and
// the Campaigns page reads the connected ones to fetch personalised coupons.
// ``loginUrl`` is where the Profile "Connect" button sends the user — the
// real OAuth flows would live behind these pages in production.
export const ECOMMERCE_ACCOUNTS = [
  { id: 'hepsiburada', name: 'Hepsiburada',      color: 'from-orange-400 to-orange-600',   initials: 'HB',  email: 'alex.rivera@hepsi.com', connected: true,  domain: 'hepsiburada.com',     loginUrl: 'https://giris.hepsiburada.com/' },
  { id: 'trendyol',    name: 'Trendyol',         color: 'from-orange-500 to-red-500',      initials: 'TY',  email: 'alex@trendyol.com',     connected: true,  domain: 'trendyol.com',        loginUrl: 'https://www.trendyol.com/giris' },
  { id: 'amazon',      name: 'Amazon',           color: 'from-slate-700 to-slate-900',     initials: 'AM',  email: null,                    connected: false, domain: 'amazon.com.tr',       loginUrl: 'https://www.amazon.com.tr/ap/signin' },
  { id: 'vatan',       name: 'Vatan Bilgisayar', color: 'from-yellow-400 to-amber-600',    initials: 'VB',  email: 'rivera@vatan.com',      connected: true,  domain: 'vatanbilgisayar.com', loginUrl: 'https://www.vatanbilgisayar.com/uye/giris' },
  { id: 'mediamarkt',  name: 'MediaMarkt',       color: 'from-red-500 to-rose-600',        initials: 'MM',  email: null,                    connected: false, domain: 'mediamarkt.com.tr',   loginUrl: 'https://www.mediamarkt.com.tr/tr/myaccount/login.html' },
  { id: 'n11',         name: 'N11',              color: 'from-fuchsia-500 to-violet-600',  initials: 'N11', email: null,                    connected: false, domain: 'n11.com',             loginUrl: 'https://www.n11.com/giris-yap' },
];

export const getConnectedAccounts = () =>
  ECOMMERCE_ACCOUNTS.filter((acc) => acc.connected);
