const { app, BrowserWindow, WebContentsView, ipcMain, Menu, session, dialog, shell, net } = require('electron');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { pathToFileURL } = require('node:url');
const { DNS, resolveAddress, isWebURL, internalPage } = require('./core.cjs');
const HEADER = 118;
const SHELL = path.join(__dirname, 'renderer/index.html');
const SHELL_URL = pathToFileURL(SHELL).href;
const windows = new Map();
const smokeMode = process.argv.includes('--smoke-test');
let store = { bookmarks: [], history: [], sessions: [] };
let saveTimer;
app.setName('SunXBrowser');
app.setAppUserModelId('app.sunxbrowser.browser');
app.enableSandbox();
if (process.env.SUNX_TEST_DATA) app.setPath('userData', process.env.SUNX_TEST_DATA);
const storeFile = () => path.join(app.getPath('userData'), 'browser-data.json');
function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    try { fs.mkdirSync(app.getPath('userData'), { recursive: true }); fs.writeFileSync(storeFile() + '.tmp', JSON.stringify(store)); fs.renameSync(storeFile() + '.tmp', storeFile()); }
    catch (error) { console.error('Could not save browser data:', error.message); }
  }, 150);
}
function stateOf(ctx) {
  const active = ctx.tabs.find(t => t.id === ctx.active);
  return { platform: process.platform, private: ctx.private, tabs: ctx.tabs.map(({ id, title, url, loading, error }) => ({ id, title, url, loading, error })), active: ctx.active,
    back: !!active?.view?.webContents.navigationHistory.canGoBack(), forward: !!active?.view?.webContents.navigationHistory.canGoForward(),
    bookmarks: store.bookmarks, history: store.history, downloads: ctx.downloads, version: app.getVersion(), dns: DNS.secureDnsServers[0] };
}
function update(ctx) {
  if (!ctx.win.isDestroyed()) ctx.win.webContents.send('sunx:state', stateOf(ctx));
}
function updateAll() { for (const ctx of windows.values()) update(ctx); }
function persistTabs(ctx) {
  if (!ctx.private) { store.sessions = ctx.tabs.map(t => isWebURL(t.url) ? t.url : 'sunx://newtab'); save(); }
}
function layout(ctx) {
  if (ctx.win.isDestroyed()) return;
  const { width, height } = ctx.win.getContentBounds();
  for (const tab of ctx.tabs) if (tab.view) {
    tab.view.setBounds({ x: 0, y: HEADER, width, height: Math.max(0, height - HEADER) });
    tab.view.setVisible(tab.id === ctx.active && !internalPage(tab.url) && !tab.error);
  }
}
function select(ctx, id) { if (!ctx.tabs.some(t => t.id === id)) return; ctx.active = id; layout(ctx); update(ctx); }
function closeTab(ctx, id) {
  const index = ctx.tabs.findIndex(t => t.id === id);
  if (index < 0) return;
  const [tab] = ctx.tabs.splice(index, 1);
  if (tab.view) { ctx.win.contentView.removeChildView(tab.view); tab.view.webContents.close(); }
  if (!ctx.tabs.length) return ctx.win.close();
  if (ctx.active === id) ctx.active = ctx.tabs[Math.min(index, ctx.tabs.length - 1)].id;
  persistTabs(ctx); layout(ctx); update(ctx);
}
function createView(ctx, tab) {
  const view = new WebContentsView({ webPreferences: { session: ctx.session, nodeIntegration: false, contextIsolation: true, sandbox: true, webSecurity: true } });
  tab.view = view; ctx.win.contentView.addChildView(view);
  const wc = view.webContents;
  wc.setWindowOpenHandler(({ url }) => { if (isWebURL(url)) createTab(ctx, url); return { action: 'deny' }; });
  wc.on('will-navigate', (event, url) => { if (!isWebURL(url)) event.preventDefault(); });
  wc.on('will-redirect', (event, url) => { if (!isWebURL(url)) event.preventDefault(); });
  wc.on('did-start-loading', () => { tab.loading = true; update(ctx); });
  wc.on('did-stop-loading', () => { tab.loading = false; update(ctx); });
  const navigated = () => { if (internalPage(tab.url)) return; const url = wc.getURL(); if (isWebURL(url)) { tab.url = url; tab.error = ''; persistTabs(ctx); } update(ctx); };
  wc.on('did-navigate', navigated); wc.on('did-navigate-in-page', navigated);
  wc.on('page-title-updated', (_event, title) => { if (internalPage(tab.url)) return; tab.title = title.slice(0, 250); update(ctx); });
  wc.on('did-finish-load', () => {
    if (internalPage(tab.url)) return;
    tab.title = wc.getTitle() || tab.url;
    if (!ctx.private && isWebURL(wc.getURL())) { store.history = [{ url: wc.getURL(), title: tab.title, time: Date.now() }, ...store.history.filter(h => h.url !== wc.getURL())].slice(0, 1000); save(); }
    update(ctx);
  });
  wc.on('did-fail-load', (_e, code, description, url, mainFrame) => {
    if (mainFrame && code !== -3) { tab.error = `${description} (${code})`; tab.loading = false; tab.url = isWebURL(url) ? url : tab.url; layout(ctx); update(ctx); }
  });
  wc.on('render-process-gone', () => { tab.error = 'หน้าเว็บหยุดทำงาน กรุณาโหลดใหม่'; tab.loading = false; layout(ctx); update(ctx); });
  wc.on('before-input-event', (event, input) => {
    if (input.type !== 'keyDown') return;
    const modifier = process.platform === 'darwin' ? input.meta : input.control;
    if (modifier && ['l', 't', 'w', 'r', 'f'].includes(input.key.toLowerCase())) {
      event.preventDefault(); shortcut(ctx, input.key.toLowerCase(), input.shift);
    }
  });
  wc.on('context-menu', (_event, info) => {
    const template = [];
    if (isWebURL(info.linkURL)) template.push({ label: 'เปิดลิงก์ในแท็บใหม่', click: () => createTab(ctx, info.linkURL) }, { type: 'separator' });
    if (info.isEditable) template.push({ role: 'cut' }, { role: 'copy' }, { role: 'paste' });
    else if (info.selectionText) template.push({ role: 'copy' });
    template.push({ label: 'ย้อนกลับ', enabled: wc.navigationHistory.canGoBack(), click: () => wc.navigationHistory.goBack() }, { label: 'โหลดใหม่', click: () => navigate(ctx, tab, tab.url) });
    Menu.buildFromTemplate(template).popup({ window: ctx.win });
  });
  return view;
}
function navigate(ctx, tab, input) {
  const url = resolveAddress(input);
  if (!url) { tab.error = 'รองรับเฉพาะที่อยู่ HTTP และ HTTPS'; layout(ctx); update(ctx); return; }
  tab.error = ''; tab.url = url;
  const page = internalPage(url);
  if (page) { if (tab.view) tab.view.webContents.stop(); tab.title = { newtab: 'แท็บใหม่', history: 'ประวัติ', bookmarks: 'บุ๊กมาร์ก', downloads: 'ดาวน์โหลด', settings: 'การตั้งค่า' }[page]; tab.loading = false; }
  else {
    const view = tab.view || createView(ctx, tab);
    tab.title = new URL(url).hostname;
    view.webContents.loadURL(url).catch(() => {});
  }
  persistTabs(ctx); layout(ctx); update(ctx);
}
function createTab(ctx, url = 'sunx://newtab', activate = true) {
  const tab = { id: crypto.randomUUID(), title: 'แท็บใหม่', url, loading: false, error: '', view: null };
  ctx.tabs.push(tab); if (activate) ctx.active = tab.id;
  navigate(ctx, tab, url); return tab;
}
function shortcut(ctx, key, shift = false) {
  const tab = ctx.tabs.find(t => t.id === ctx.active);
  if (key === 'l') { ctx.win.webContents.focus(); ctx.win.webContents.send('sunx:focus-address'); }
  if (key === 't') shift ? createWindow(true) : createTab(ctx);
  if (key === 'w') closeTab(ctx, ctx.active);
  if (key === 'r') navigate(ctx, tab, tab.url);
  if (key === 'f') { ctx.win.webContents.focus(); ctx.win.webContents.send('sunx:find'); }
}
function permissions(ctx) {
  ctx.session.setPermissionCheckHandler(() => false);
  ctx.session.setPermissionRequestHandler(async (wc, permission, callback) => {
    const owner = [...windows.values()].find(c => c.tabs.some(t => t.view?.webContents === wc));
    const tab = owner?.tabs.find(t => t.view?.webContents === wc);
    if (!tab || !['media', 'geolocation', 'notifications', 'clipboard-read'].includes(permission)) return callback(false);
    const result = await dialog.showMessageBox(owner.win, { type: 'question', title: 'สิทธิ์เว็บไซต์', message: `${new URL(tab.url).hostname} ต้องการใช้ ${permission}`, buttons: ['ไม่อนุญาต', 'อนุญาต'], defaultId: 0, cancelId: 0 });
    callback(result.response === 1);
  });
}
function createWindow(isPrivate = false) {
  const win = new BrowserWindow({ width: 1280, height: 820, minWidth: 760, minHeight: 540, show: false, backgroundColor: '#ffffff', icon: path.join(__dirname, 'assets/icon.png'),
    ...(process.platform === 'darwin' ? { titleBarStyle: 'hidden', trafficLightPosition: { x: 14, y: 13 } } : { frame: false }),
    webPreferences: { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true } });
  const ctx = { win, private: isPrivate, tabs: [], active: '', downloads: [], session: session.fromPartition(isPrivate ? `private-${crypto.randomUUID()}` : 'persist:sunx') };
  const windowId = win.webContents.id;
  windows.set(windowId, ctx);
  // Normal windows share the browser session; attach its handlers only once.
  if (!ctx.session.sunxConfigured) {
    ctx.session.sunxConfigured = true;
    permissions(ctx);
    ctx.session.on('will-download', (_event, item, source) => {
      const owner = [...windows.values()].find(c => c.tabs.some(t => t.view?.webContents === source)) || ctx;
      const entry = { id: crypto.randomUUID(), name: item.getFilename(), received: 0, total: item.getTotalBytes(), status: 'progressing', path: '' };
      owner.downloads.unshift(entry);
      item.on('updated', (_event, status) => { entry.status = status; entry.received = item.getReceivedBytes(); update(owner); });
      item.once('done', (_event, status) => { entry.status = status; entry.path = status === 'completed' ? item.getSavePath() : ''; update(owner); });
      update(owner);
    });
  }
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  win.webContents.on('will-navigate', event => event.preventDefault());
  win.webContents.on('did-finish-load', () => update(ctx));
  win.on('resize', () => layout(ctx));
  win.on('closed', () => {
    for (const tab of ctx.tabs) if (tab.view && !tab.view.webContents.isDestroyed()) tab.view.webContents.close();
    windows.delete(windowId);
    if (ctx.private) ctx.session.clearStorageData().catch(() => {});
  });
  win.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && (process.platform === 'darwin' ? input.meta : input.control) && ['l', 't', 'w', 'r', 'f'].includes(input.key.toLowerCase())) { event.preventDefault(); shortcut(ctx, input.key.toLowerCase(), input.shift); }
  });
  win.loadFile(SHELL);
  win.once('ready-to-show', () => { if (!smokeMode) win.show(); });
  const restored = !isPrivate && windows.size === 1 ? store.sessions.filter(isWebURL).slice(0, 20) : [];
  for (const url of restored.length ? restored : ['sunx://newtab']) createTab(ctx, url);
  return ctx;
}
ipcMain.handle('sunx:command', async (event, action, value) => {
  const ctx = windows.get(event.sender.id);
  if (!ctx || event.senderFrame !== ctx.win.webContents.mainFrame || event.senderFrame.url !== SHELL_URL) throw new Error('Untrusted browser command');
  const tab = ctx.tabs.find(t => t.id === ctx.active);
  if (action === 'state') return stateOf(ctx);
  if (action === 'navigate' && typeof value === 'string') navigate(ctx, tab, value);
  else if (action === 'new-tab') createTab(ctx);
  else if (action === 'select-tab') select(ctx, value);
  else if (action === 'close-tab') closeTab(ctx, value);
  else if (action === 'back' && tab.view?.webContents.navigationHistory.canGoBack()) tab.view.webContents.navigationHistory.goBack();
  else if (action === 'forward' && tab.view?.webContents.navigationHistory.canGoForward()) tab.view.webContents.navigationHistory.goForward();
  else if (action === 'reload') tab.loading && tab.view ? tab.view.webContents.stop() : navigate(ctx, tab, tab.url);
  else if (action === 'bookmark' && isWebURL(tab.url)) {
    const exists = store.bookmarks.some(b => b.url === tab.url);
    store.bookmarks = exists ? store.bookmarks.filter(b => b.url !== tab.url) : [...store.bookmarks, { url: tab.url, title: tab.title }]; save(); updateAll();
  } else if (action === 'remove-bookmark' && typeof value === 'string') { store.bookmarks = store.bookmarks.filter(b => b.url !== value); save(); updateAll(); }
  else if (action === 'clear-history') {
    const answer = await dialog.showMessageBox(ctx.win, { message: 'ล้างประวัติการเข้าชมทั้งหมด?', buttons: ['ยกเลิก', 'ล้างประวัติ'], cancelId: 0 });
    if (answer.response === 1) { store.history = []; save(); updateAll(); }
  } else if (action === 'find' && typeof value === 'string' && value.trim()) tab.view?.webContents.findInPage(value.slice(0, 200));
  else if (action === 'stop-find') tab.view?.webContents.stopFindInPage('clearSelection');
  else if (action === 'open-download') { const item = ctx.downloads.find(d => d.id === value && d.status === 'completed'); if (item) shell.showItemInFolder(item.path); }
  else if (action === 'minimize') ctx.win.minimize();
  else if (action === 'maximize') ctx.win.isMaximized() ? ctx.win.unmaximize() : ctx.win.maximize();
  else if (action === 'close-window') ctx.win.close();
  else if (action === 'menu') Menu.buildFromTemplate([
    { label: 'แท็บใหม่', accelerator: 'CmdOrCtrl+T', click: () => createTab(ctx) },
    { label: 'หน้าต่างใหม่', click: () => createWindow() },
    { label: 'หน้าต่างไม่ระบุตัวตน', accelerator: 'CmdOrCtrl+Shift+N', click: () => createWindow(true) }, { type: 'separator' },
    ...[['history', 'ประวัติ'], ['bookmarks', 'บุ๊กมาร์ก'], ['downloads', 'ดาวน์โหลด'], ['settings', 'การตั้งค่า']].map(([page, label]) => ({ label, click: () => navigate(ctx, tab, 'sunx://' + page) })),
    { label: 'ค้นหาในหน้าเว็บ', click: () => shortcut(ctx, 'f') }, { type: 'separator' },
    { label: 'เกี่ยวกับ SunXBrowser', click: () => app.showAboutPanel() }, { label: 'ออก', click: () => app.quit() }
  ]).popup({ window: ctx.win });
  return true;
});
app.whenReady().then(async () => {
  // Configure before creating any window, session view, or network request.
  app.configureHostResolver(DNS);
  app.setAboutPanelOptions({ applicationName: 'SunXBrowser', applicationVersion: app.getVersion(), copyright: 'SunXBrowser · Electron / Chromium' });
  if (process.platform === 'darwin') Menu.setApplicationMenu(Menu.buildFromTemplate([{ label: 'SunXBrowser', submenu: [{ role: 'about' }, { type: 'separator' }, { role: 'quit' }] }, { label: 'Edit', submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }, { role: 'selectAll' }] }]));
  else Menu.setApplicationMenu(null);
  try { const data = JSON.parse(fs.readFileSync(storeFile(), 'utf8')); store = { bookmarks: Array.isArray(data.bookmarks) ? data.bookmarks.filter(b => isWebURL(b.url)).slice(0, 1000) : [], history: Array.isArray(data.history) ? data.history.filter(h => isWebURL(h.url)).slice(0, 1000) : [], sessions: Array.isArray(data.sessions) ? data.sessions.filter(isWebURL).slice(0, 20) : [] }; } catch {}
  const ctx = createWindow();
  if (smokeMode) require('./scripts/smoke-runtime.cjs').run({ app, ctx, createTab, select, closeTab, createWindow, windows, DNS, session, net }).catch(error => { console.error(error); app.exit(1); });
});
app.on('activate', () => { if (!windows.size) createWindow(); });
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit(); });
