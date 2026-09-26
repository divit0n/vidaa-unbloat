# vidaa-unbloat

Debloating, speeding up and de-spying a **Hisense 70A5FE TV running VIDAA 9** (firmware V0000.09.09A.P0930, MTK9602 chipset) — done entirely over the local network, with no physical access to the TV and no userland root.

This repo contains: the technique (DNS spoofing + the JS bridge built into the TV browser), working tools, and documentation of the **dirty practices Hisense/VIDAA ships in its TVs** discovered during the exploration.

> ## ⚠️ Disclaimer — read first
> This repository is published **strictly for educational and research purposes**: to document the telemetry and data-collection behavior of consumer smart TVs and to help owners understand what devices they purchased are doing on their own networks.
>
> - Use everything here **only on devices you own**, and **only on networks you are authorized to test**.
> - Pointing TVs, routers or other people's equipment at tools from this repo **without the owner's explicit consent may be illegal** in your jurisdiction (unauthorized access, wiretapping, computer misuse acts — e.g. CFAA, polish art. 267 kk, EU equivalents).
> - Modifying TV firmware/settings can brick the device or void warranty. **You take full responsibility** for anything you run.
> - We are not affiliated with, or endorsed by, Hisense or VIDAA. All trademarks belong to their respective owners.
> - Everything described here was performed on **our own TV, on our own LAN, with full consent of the network owner**.

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

## 🔍 How to verify on your own TV

No exploit needed — your router already sees every DNS query the TV makes. Three levels of verification, from read-only upwards:

### Level 1 — Read-only: watch the DNS log (5 minutes)
Point your TV at your router's DNS (default), leave it **idle on the home screen for 30–60 minutes**, and watch the queries:

```bash
# OpenWrt / GL.iNet router:
tcpdump -i br-lan port 53 -n | grep -iE 'vidaahub|unruly|netflix'

# or check the query log in Pi-hole / AdGuard Home / OpenWrt dnsmasq log
```

If your TV is a Hisense VIDAA, you should see most of these within the hour:

| Domain | What it is |
|---|---|
| `ter-jrnl-eu.vidaahub.com` | VIDAA EU event journal — the most talkative one |
| `ter-jrnl-na.vidaahub.com` | VIDAA North-America journal |
| `rpt-mntz-azure.vidaahub.com` / `rsc-mntz.vidaahub.com` | Monitoring/reporting (Azure) |
| `acr.unruly.co` | **Automatic Content Recognition** — watch what you watch |
| `logs.netflix.com`, `nrdp.push.prod.netflix.com` | Netflix client logging (appears with the Netflix app installed) |
| `img.vidaahub.com`, `layout-ui-eu.vidaahub.com` | legit app-store/UI traffic — needed for the home screen |

**No capture, no claim** — that's all the evidence you need that your TV phones home, regardless of what any settings screen says.

### Level 2 — Block and confirm behavior
Add the domains from [`blocklist/domains.txt`](blocklist/domains.txt) to your router (dnsmasq `address=/domain/0.0.0.0`, Pi-hole, or AdGuard Home custom rules). Everything keeps working — the TV just stops reporting. Netflix plays fine; only its log spigot closes.

### Level 3 — Reproduce the full exploration
Only on a TV you own, on your own network:

```bash
pip install dnslib
# 1. generate a self-signed cert for vidaahub.com, place it next to the script
openssl req -x509 -newkey rsa:2048 -keyout vidaahub.com.key -out vidaahub.com.crt \
  -days 365 -nodes -subj "/CN=vidaahub.com"
# 2. set PC_IP / UPSTREAM in tools/vidaa-cnc.py
python tools/vidaa-cnc.py
# 3. on the TV: set DNS manually to the PC IP, open https://vidaahub.com/ in the browser
# 4. drop JS commands into cnd/001.js, 002.js ... — results land in results.jsonl
```

The bridge page enumerates the exposed `Hisense_*` functions, and the hotfolder lets you send arbitrary JS that runs inside the TV browser context — including `vowOS.service.syncExecute('hiutils', {api:'fileRead', args:{path:'websdk/../../etc/passwd', mode:6}})` for a full filesystem read. See [`docs/FINDINGS.md`](docs/FINDINGS.md) for everything we mapped.

---

## 🛠️ The technique (summary)

1. **DNS spoofing**: a custom DNS server answers `vidaahub.com` with the PC's IP and forwards everything else to the router. The TV is pointed at this DNS manually.
2. **HTTPS**: a self-signed cert for `vidaahub.com` (the TV asks once for acceptance).
3. **JS bridge**: the page opened in the TV browser gains access to the `vowOS`/phoenix bridge compiled into hisenseUI — function enumeration, remote JS execution.
4. **Path traversal in hiutils**: the `fileRead`/`fileWrite` API concatenates a base dir from a fixed list with the user path — `websdk/../../etc/passwd` gives **full filesystem read and write** (RW partitions: `/APPS`, `/data`, `/var/local`, `/OAD`, `/tmp`).
5. **Phoenix API on localhost:9009**: services `hiutils`, `tvinfo` (native "biz" keys: brightness, contrast, MEMC, picture mode, MAC, identifiers), `fetcher` (server-side fetch), `ipchandler`.
6. **MQTT (port 36669, TLS with client cert)**: `applist`, `launchapp`, `sendkey` — via the `hisense_tv` library.

**Results on our unit**: bloat removed, brightness 100% + max contrast + max MEMC set through native APIs, telemetry blocklisted, full system map (processes, ports, mounts, partitions).

---

## 📁 Repository contents

- [`blocklist/domains.txt`](blocklist/domains.txt) — domains to block (dnsmasq/OpenWrt/AGH/Pi-hole formats)
- [`tools/vidaa-cnc.py`](tools/vidaa-cnc.py) — DNS + HTTPS + C&C server with a JS command hotfolder
- [`tools/tv-relaunch.py`](tools/tv-relaunch.py) — reopens the bridge page via MQTT
- [`docs/FINDINGS.md`](docs/FINDINGS.md) — full technical findings (processes, ports, partitions, APIs, paths)

## ⚖️ Final note
A TV is a computer sitting in your living room, permanently connected to your network. You have the right to know what it transmits, to decide what it may transmit, and to remove software you never asked for. This repo exists so you don't have to take the manufacturer's word for it.

License: MIT.
