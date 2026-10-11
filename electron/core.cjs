const INTERNAL = new Set(['newtab', 'history', 'bookmarks', 'downloads', 'settings']);
const DNS = Object.freeze({ enableBuiltInResolver: true, secureDnsMode: 'secure', secureDnsServers: ['https://1.1.1.1/dns-query'] });
function resolveAddress(input) {
  const value = String(input || '').trim().slice(0, 8192);
  if (!value) return 'sunx://newtab';
  if (value.startsWith('sunx://') && INTERNAL.has(value.slice(7))) return value;
  if (/^https?:\/\//i.test(value)) { try { return new URL(value).href; } catch { return null; } }
  if (/^[a-z][a-z0-9+.-]*:/i.test(value) && !/^[\w.-]+:\d+(\/|$)/.test(value)) return null;
  if (!/\s/.test(value) && (/^[\w.-]+\.[a-z]{2,}([/:?#]|$)/i.test(value) || /^localhost([/:?#]|$)/.test(value) || /^\d+\.\d+\.\d+\.\d+([/:?#]|$)/.test(value))) {
    try { return new URL((/^localhost/.test(value) ? 'http://' : 'https://') + value).href; } catch { return null; }
  }
  return 'https://www.google.com/search?q=' + encodeURIComponent(value);
}
function isWebURL(value) { try { return ['https:', 'http:'].includes(new URL(value).protocol); } catch { return false; } }
function internalPage(value) { return value.startsWith('sunx://') && INTERNAL.has(value.slice(7)) ? value.slice(7) : null; }
module.exports = { DNS, resolveAddress, isWebURL, internalPage };
