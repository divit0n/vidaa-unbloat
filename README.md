# vidaa-unbloat

Debloating, speeding up and de-spying a **Hisense 70A5FE TV running VIDAA 9** (firmware V0000.09.09A.P0930, MTK9602 chipset) — done entirely over the local network, with no physical access to the TV and no userland root.

This repo contains: the technique (DNS spoofing + the JS bridge built into the TV browser), working tools, and documentation of the **dirty practices Hisense/VIDAA ships in its TVs** discovered during the exploration.

---

## 🕵️ What Hisense does with your TV (documented practices)

Everything below was observed on a live device during this project (DNS logs from the router + direct reads of the TV filesystem and processes):

### 1. ACR — Automatic Content Recognition
The TV regularly connects to **`acr.unruly.co`** (14 DNS queries in a short observation window). ACR means the TV analyzes the picture/audio of what you watch and ships signatures to a third party. Enabled by default, with no meaningful on-screen disclosure.

### 2. Telemetry every ~20 seconds
- **`ter-jrnl-eu.vidaahub.com`** — 154 DNS queries over a few hours (VIDAA EU event journal). The TV wakes from idle just to report.
- **`rpt-mntz-azure.vidaahub.com`**, **`rsc-mntz.vidaahub.com`** — reporting/monitoring hosted on Azure.
- **Netflix on a Hisense TV** ships logs to **`logs.netflix.com`** and **`nrdp.push.prod.netflix.com`** roughly every 20 s, whether anyone is watching or not.

### 3. Persistent advertising ID
The system keeps an `adsID` — a permanent user identifier for ad targeting (`kilby.sl2.str.system.adtarget.id`), readable through the native API. Next to it in the menu sits an innocent-looking "Ads Privacy" app.

### 4. Bloatware you're not allowed to remove
- ~45 factory apps (preset). Some carry the `remove:0` flag — **they cannot be uninstalled through any user-facing path**, because the preset list is hardcoded in the native launcher binary (hisenseUI). Shadow entries in `Appinfo.json` are ignored — the merge always prefers preset.
- Apps flagged `remove:1` *can* be removed manually (long-press OK → Delete) and the removal **survives reboot** — but nothing in the UI tells you which is which.
- The system can also leave an app in a **half-removed state**: `isunInstalled: true` is set, yet the icon stays on the home screen and the launcher never hides it.

### 5. A sponsored row you can't touch
The home screen ships a row of sponsored apps (Rakuten, Boosteroid, Blacknut, Game Center…) whose presence no user flag controls. The list comes from the launcher binary — not from a config file, not from a spoofable cloud endpoint.

### 6. System telemetry
A dedicated **`hi_logreport_service`** process runs in the background at all times (log reporting). First-time setup forces EULA acceptance plus a separate advertising consent.

---

## 🛠️ The technique

1. **DNS spoofing**: a custom DNS server answers `vidaahub.com` with the PC's IP and forwards everything else to the router. The TV is pointed at this DNS manually.
2. **HTTPS**: a self-signed cert for `vidaahub.com` (the TV asks once for acceptance).
3. **JS bridge**: the page opened in the TV browser gains access to the `vowOS`/phoenix bridge compiled into hisenseUI — function enumeration, remote JS execution (hotfolder `cnd/NNN.js` → results in `results.jsonl`).
4. **Path traversal in hiutils**: the `fileRead`/`fileWrite` API concatenates a base dir from a fixed list with the user path — `websdk/../../etc/passwd` gives **full filesystem read and write** (RW partitions: `/APPS`, `/data`, `/var/local`, `/OAD`, `/tmp`).
5. **Phoenix API on localhost:9009**: services `hiutils`, `tvinfo` (native "biz" keys: brightness, contrast, MEMC, picture mode, MAC, identifiers), `fetcher` (server-side fetch), `ipchandler`. Called via POST from a page running on the TV.
6. **MQTT (port 36669, TLS with client cert)**: `applist`, `launchapp`, `sendkey` — via the `hisense_tv` library.

**Results**: bloat removed, brightness 100% + max contrast + max MEMC set through native APIs, telemetry blocklisted, full system map (processes, ports, mounts, partitions).

---

## 📁 Repository contents

- [`blocklist/domains.txt`](blocklist/domains.txt) — domains to block (dnsmasq/OpenWrt/AGH/Pi-hole formats)
- [`tools/vidaa-cnc.py`](tools/vidaa-cnc.py) — DNS + HTTPS + C&C server with a JS command hotfolder
- [`tools/tv-relaunch.py`](tools/tv-relaunch.py) — reopens the bridge page via MQTT
- [`docs/FINDINGS.md`](docs/FINDINGS.md) — full technical findings (processes, ports, partitions, APIs, paths)

## 🚀 Quick start

```bash
pip install dnslib
# 1. generate a self-signed cert for vidaahub.com, place it next to the script
# 2. set PC_IP / UPSTREAM in vidaa-cnc.py
python tools/vidaa-cnc.py
# 3. on the TV: set DNS manually to the PC IP, open https://vidaahub.com/ in the browser
# 4. drop JS commands into cnd/001.js, 002.js ... — results land in results.jsonl
```

## ⚖️ Disclaimer
Everything here was done on our own device, on our own network. A TV is a computer sitting in your living room — you have the right to know what it transmits and to decide about it.

License: MIT.
