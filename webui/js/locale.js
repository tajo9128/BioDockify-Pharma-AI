/**
 * BioDockify locale — reads BIODOCKIFY_LOCALE env (via /api/locale) and
 * exposes currency symbol, date format, unit system.
 */
(function() {
  const LOCALE_MAP = {
    "en-IN": { currency: "INR", symbol: "₹", tz: "Asia/Kolkata" },
    "en-US": { currency: "USD", symbol: "$", tz: "America/New_York" },
    "en-GB": { currency: "GBP", symbol: "£", tz: "Europe/London" },
    "en-EU": { currency: "EUR", symbol: "€", tz: "Europe/Berlin" },
    "ja-JP": { currency: "JPY", symbol: "¥", tz: "Asia/Tokyo" },
    "en-AU": { currency: "AUD", symbol: "A$", tz: "Australia/Sydney" },
  };
  window.BioDockifyLocale = { locale: "en-IN", currencySymbol: "₹", unitSystem: "metric" };
  fetch("/api/locale").then(r => r.json()).then(cfg => {
    if (cfg && cfg.symbol) {
      window.BioDockifyLocale = cfg;
    }
  }).catch(() => {});
})();
