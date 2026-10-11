let state;
const $ = selector => document.querySelector(selector);
const svg = name => { const node = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); const use = document.createElementNS(node.namespaceURI, 'use'); use.setAttribute('href', '#i-' + name); node.append(use); return node; };
const el = (tag, text, className) => { const node = document.createElement(tag); if (text !== undefined) node.textContent = text; if (className) node.className = className; return node; };
const send = (action, value) => window.sunx.command(action, value).catch(console.error);
const activeTab = () => state?.tabs.find(t => t.id === state.active);
document.addEventListener('click', event => { const control = event.target.closest('[data-action]'); if (control) send(control.dataset.action); });
$('#address-form').addEventListener('submit', event => { event.preventDefault(); send('navigate', $('#address').value); $('#address').blur(); });
$('#address').addEventListener('focus', () => $('#address').select());
$('#find-bar').addEventListener('submit', event => { event.preventDefault(); send('find', $('#find-text').value); });
$('#close-find').addEventListener('click', () => { $('#find-bar').hidden = true; send('stop-find'); });
window.sunx.onFocusAddress?.(() => { $('#address').focus(); $('#address').select(); });
window.sunx.onFind?.(() => { $('#find-bar').hidden = false; $('#find-text').focus(); });
function searchForm() {
  const form = el('form', undefined, 'home-search'); form.append(svg('search'));
  const input = el('input'); input.placeholder = 'ค้นหาด้วย Google หรือป้อน URL'; input.setAttribute('aria-label', 'ค้นหาเว็บไซต์'); form.append(input);
  form.addEventListener('submit', event => { event.preventDefault(); send('navigate', input.value); }); return form;
}
function renderTabs() {
  const tabs = $('#tabs'); tabs.replaceChildren();
  for (const tab of state.tabs) {
    const wrap = el('div', undefined, 'tab' + (tab.id === state.active ? ' active' : ''));
    wrap.setAttribute('role', 'tab'); wrap.setAttribute('aria-selected', String(tab.id === state.active)); wrap.tabIndex = 0;
    const icon = svg(tab.loading ? 'reload' : 'globe'); icon.classList.add('tab-icon'); if (tab.loading) icon.classList.add('loading');
    const label = el('span', tab.title, 'tab-title');
    const close = el('button', undefined, 'tab-close'); close.setAttribute('aria-label', 'ปิดแท็บ ' + tab.title); close.title = 'ปิดแท็บ'; close.append(svg('close'));
    close.addEventListener('click', event => { event.stopPropagation(); send('close-tab', tab.id); });
    wrap.addEventListener('click', () => send('select-tab', tab.id));
    wrap.addEventListener('keydown', event => { if (['Enter', ' '].includes(event.key)) { event.preventDefault(); send('select-tab', tab.id); } });
    wrap.addEventListener('auxclick', event => { if (event.button === 1) send('close-tab', tab.id); });
    wrap.append(icon, label, close); tabs.append(wrap);
  }
}
function renderBookmarks() {
  const bar = $('#bookmarks-bar'); bar.replaceChildren();
  if (!state.bookmarks.length) bar.append(el('span', 'บันทึกเว็บไซต์โปรดด้วยปุ่มดาวในช่องที่อยู่'));
  for (const mark of state.bookmarks) {
    const button = el('button'); button.title = mark.url; button.append(svg('globe'), el('span', mark.title));
    button.addEventListener('click', () => send('navigate', mark.url)); bar.append(button);
  }
}
let pageKey = '';
function renderPage() {
  const tab = activeTab(); if (!tab) return;
  const page = $('#page');
  const internal = tab.url.startsWith('sunx://') ? tab.url.slice(7) : '';
  if (!internal && !tab.error) { page.replaceChildren(); pageKey = ''; return; }
  const key = JSON.stringify([internal, tab.error, state.private, internal === 'history' ? state.history : internal === 'bookmarks' ? state.bookmarks : internal === 'downloads' ? state.downloads : null]);
  if (key === pageKey) return; pageKey = key; page.replaceChildren();
  if (tab.error) {
    const section = el('section', undefined, 'error-page'); section.append(svg('globe'), el('h1', 'ไม่สามารถเปิดเว็บไซต์นี้ได้'), el('p', tab.url), el('p', tab.error));
    const button = el('button', 'ลองอีกครั้ง', 'primary'); button.addEventListener('click', () => send('reload')); section.append(button);
    section.append(el('p', 'หากเครือข่ายบล็อก Cloudflare Secure DNS การเชื่อมต่อเว็บไซต์อาจไม่สำเร็จ')); page.append(section); return;
  }
  if (internal === 'newtab') {
    if (state.private) {
      const section = el('section', undefined, 'content-page private-home'); const icon = svg('private'); icon.classList.add('private-symbol');
      section.append(icon, el('h1', 'คุณอยู่ในโหมดไม่ระบุตัวตน'), el('p', 'SunXBrowser จะไม่บันทึกประวัติการเข้าชมในหน้าต่างนี้ คุกกี้ของเซสชันจะถูกล้างเมื่อปิดหน้าต่าง ไฟล์ที่ดาวน์โหลดและบุ๊กมาร์กที่คุณบันทึกยังคงอยู่'), el('p', 'เว็บไซต์ ผู้ให้บริการอินเทอร์เน็ต และผู้ดูแลเครือข่ายยังอาจเห็นกิจกรรมของคุณได้'), searchForm()); page.append(section); return;
    }
    const section = el('section', undefined, 'newtab-page'); section.append(el('h1', 'SunXBrowser', 'wordmark'), searchForm());
    const shortcuts = el('div', undefined, 'shortcuts');
    for (const [name, letter, url] of [['Google', 'G', 'https://www.google.com'], ['YouTube', 'Y', 'https://www.youtube.com'], ['Gmail', 'M', 'https://mail.google.com'], ['GitHub', 'GH', 'https://github.com']]) {
      const button = el('button', undefined, 'shortcut'); button.append(el('span', letter, 'shortcut-mark'), el('span', name)); button.addEventListener('click', () => send('navigate', url)); shortcuts.append(button);
    }
    section.append(shortcuts); const note = el('div', undefined, 'dns-footnote'); note.append(svg('shield'), el('span', 'Cloudflare Secure DNS · 1.1.1.1')); section.append(note); page.append(section); return;
  }
  const section = el('section', undefined, 'content-page');
  section.append(el('h1', { history: 'ประวัติการเข้าชม', bookmarks: 'บุ๊กมาร์ก', downloads: 'ดาวน์โหลด', settings: 'การตั้งค่า' }[internal] || 'SunXBrowser'));
  if (internal === 'settings') {
    section.append(el('h2', 'ความเป็นส่วนตัวและความปลอดภัย'));
    const row = el('div', undefined, 'row'); const text = el('div', undefined, 'row-text'); text.append(el('div', 'ใช้ Secure DNS'), el('div', 'Cloudflare · https://1.1.1.1/dns-query', 'detail')); row.append(svg('shield'), text, el('span', 'เปิดอัตโนมัติ', 'setting-value')); section.append(row);
    section.append(el('p', 'DNS ใช้เฉพาะภายใน SunXBrowser ไม่เปลี่ยนการตั้งค่าของระบบ หาก Cloudflare ใช้งานไม่ได้ เบราว์เซอร์จะไม่เปลี่ยนไปใช้ DNS แบบไม่เข้ารหัส', 'empty'), el('h2', 'เกี่ยวกับ SunXBrowser'), el('p', 'เวอร์ชัน ' + state.version + ' · Electron / Chromium', 'empty'), el('p', 'ข้อมูลถูกเก็บในเครื่อง ไม่มี Chrome Sync หรือการซิงก์บัญชี Google', 'empty'));
  } else {
    const items = internal === 'history' ? state.history : internal === 'bookmarks' ? state.bookmarks : state.downloads;
    if (!items.length) section.append(el('p', { history: 'ยังไม่มีประวัติการเข้าชม', bookmarks: 'ยังไม่มีบุ๊กมาร์ก เปิดเว็บไซต์แล้วกดดาวเพื่อบันทึก', downloads: 'ยังไม่มีรายการดาวน์โหลดในหน้าต่างนี้' }[internal], 'empty'));
    if (internal === 'history' && items.length) { const clear = el('button', 'ล้างประวัติการเข้าชม', 'text-button'); clear.addEventListener('click', () => send('clear-history')); section.append(clear); }
    for (const item of items) {
      const row = el('div', undefined, 'row'); const text = el('div', undefined, 'row-text'); const button = el('button', item.title || item.name || item.url, 'open-link');
      button.addEventListener('click', () => internal === 'downloads' ? send('open-download', item.id) : send('navigate', item.url));
      text.append(button, el('div', internal === 'downloads' ? `${{ progressing: 'กำลังดาวน์โหลด', completed: 'ดาวน์โหลดเสร็จแล้ว', cancelled: 'ยกเลิก', interrupted: 'ดาวน์โหลดไม่สำเร็จ' }[item.status] || item.status} · ${(item.received / 1048576).toFixed(1)} MB` : item.url, 'detail')); row.append(svg(internal === 'downloads' ? 'download' : 'globe'), text);
      if (item.time) row.append(el('time', new Date(item.time).toLocaleString('th-TH')));
      if (internal === 'bookmarks') { const remove = el('button', 'นำออก', 'text-button'); remove.addEventListener('click', () => send('remove-bookmark', item.url)); row.append(remove); }
      section.append(row);
    }
  }
  page.append(section);
}
function render(next) {
  state = next;
  document.body.classList.toggle('mac', state.platform === 'darwin'); document.body.classList.toggle('private', state.private);
  const tab = activeTab(); if (!tab) return;
  renderTabs(); renderBookmarks(); renderPage();
  if (document.activeElement !== $('#address')) $('#address').value = tab.url === 'sunx://newtab' ? '' : tab.url;
  $('#back').disabled = !state.back; $('#forward').disabled = !state.forward;
  $('#star').disabled = !/^https?:/.test(tab.url); $('#star').classList.toggle('saved', state.bookmarks.some(b => b.url === tab.url));
  $('#reload use').setAttribute('href', tab.loading ? '#i-close' : '#i-reload');
  const mode = $('#mode'); mode.replaceChildren(); if (state.private) mode.append(svg('private'), el('span', 'ไม่ระบุตัวตน')); else { const image = el('img'); image.src = '../assets/icon.png'; image.alt = ''; mode.append(image, el('span', 'SunXBrowser')); }
  document.title = tab.title + ' — SunXBrowser';
}
window.sunx.onState(render);
window.sunx.command('state').then(render).catch(console.error);
