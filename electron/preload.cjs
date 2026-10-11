const { contextBridge, ipcRenderer } = require('electron');
contextBridge.exposeInMainWorld('sunx', {
  command: (action, value) => ipcRenderer.invoke('sunx:command', action, value),
  onState: callback => ipcRenderer.on('sunx:state', (_event, state) => callback(state)),
  onFocusAddress: callback => ipcRenderer.on('sunx:focus-address', () => callback()),
  onFind: callback => ipcRenderer.on('sunx:find', () => callback())
});
