const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');const http=require('node:http');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<100;i++){if(await fn())return;await wait(100)}throw Error('Timed out waiting for browser state')}
exports.run=async({app,ctx,createTab,select,closeTab,createWindow,DNS})=>{
 const out=process.env.SUNX_TEST_OUTPUT;fs.mkdirSync(out,{recursive:true});await until(()=>!ctx.win.webContents.isLoading());await wait(300);
 assert.equal(await ctx.win.webContents.executeJavaScript('typeof window.sunx'),'object');
 for(const width of [1280,800]){ctx.win.setSize(width,820);await wait(250);fs.writeFileSync(path.join(out,`home-${width}.png`),(await ctx.win.webContents.capturePage()).toPNG())}
 await ctx.win.webContents.executeJavaScript("document.querySelector('.home-search input').focus()");await wait(100);fs.writeFileSync(path.join(out,'focus-search.png'),(await ctx.win.webContents.capturePage()).toPNG());
 ctx.win.show();ctx.win.focus();ctx.win.webContents.focus();await wait(300);console.log(await ctx.win.webContents.executeJavaScript("document.querySelector('.tab').focus(); JSON.stringify({active:document.activeElement.className,outline:getComputedStyle(document.querySelector('.tab')).outline,visible:document.querySelector('.tab').matches(':focus')})"));await wait(250);fs.writeFileSync(path.join(out,'focus-tab.png'),(await ctx.win.webContents.capturePage()).toPNG());
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end('<title>SunX fixture</title><h1>Browser test</h1><script>document.body.dataset.node=typeof require</script>')});await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const tab=createTab(ctx,`http://127.0.0.1:${server.address().port}/`);await until(()=>tab.title==='SunX fixture');assert.equal(await tab.view.webContents.executeJavaScript('typeof require'),'undefined');assert.equal(await tab.view.webContents.executeJavaScript('typeof window.sunx'),'undefined');assert.equal(tab.view.webContents.getLastWebPreferences().sandbox,true);
 const priv=createWindow(true);assert.notEqual(priv.session,ctx.session);priv.win.close();closeTab(ctx,tab.id);select(ctx,ctx.tabs[0].id);
 const dns=await ctx.session.resolveHost('example.com',{source:'dns',cacheUsage:'disallowed'});assert.ok(dns.endpoints.length);
 fs.writeFileSync(path.join(out,'smoke.json'),JSON.stringify({platform:process.platform,dns:DNS,resolved:dns,checks:['shell IPC','guest sandbox','no guest Node or bridge','tabs','private session isolation','Cloudflare DNS resolution']},null,2));
 server.close();console.log('SUNX_SMOKE_OK');app.exit(0);
};
