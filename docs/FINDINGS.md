# Technical findings — VIDAA 9 (Hisense 70A5FE, MTK9602)

## Architecture
- Launcher and all apps: a single `./bin/hisenseUI` binary (Chromium-based) started with `--remote_debugging_port=9666 --webdriver_port=4445 --url=file:///hisenseUI/index.html`. DevTools **do not work** (port is dead in the production build).
- JS backend: **phoenix** (Node, `/opt/pkgs/tv.vidaa.app.phoenix//bin/phoenix`, uid 314) — its own HTTP (9009) and WSS (9888) on localhost.
- The `vowOS` bridge is injected into pages by the binary itself (not via a `<script>` tag).

## Phoenix API (localhost:9009, POST JSON)
- `/service/basic/hiutils` — `fileRead`, `fileWrite` (argument is `writedata`!), `installApplication`, `setDns`, `securityEncrypt/Decrypt`, `deviceCode`, `setDebugPort` (requires security level 2–6 → returns "invalid" in production)
- `/service/basic/tvinfo` — read "biz" keys + `setbiz {key, value}`: `brightness`, `contrast`, `memcStatus`, `pictureMode`, `lowLatencyMode`, `storeMode` (RO), `isHotelMode` (RO), `adsID` (RO), `dns`, `kidsMode`, `devtoolSwitch`
- `/service/basic/fetcher` — server-side fetch (`fetchResponse`, `fetchHead`, `fetchFile`)
- `/service/system/pkgmgr` — `getInstalledPkgs`
- Services are unreachable from the LAN (firewall) — only from inside the TV.

## Path traversal (hiutils fileRead/fileWrite)
`path_list[mode] + path`, with `..` resolved by the FS:
0 `/tmp/`, 1 `/APPS/varlocal/applications/UI/`, 2 `/APPS/channelA/`, 3 `/APPS/varlocal/`, 4 `/data/`, 5 `/vddt/`, 6 `/APPS/`, 7 `/OAD/`
→ `websdk/../../etc/passwd` = full FS. RW: `/APPS` (mmcblk0p41), `/data`, `/cache`, `/var/local`, `/OAD`, `/var/tvservice`, `/tmp`. RO: `/`, `/application`, `/opt`, `/usr/local`.
Caution: `fileWrite` opens the file with mode `w` **before** validating arguments — a malformed call = truncated file.

## App list
45 preset entries + user apps. The `getInstalledApps` merge always prefers preset — a shadow entry in `/APPS/websdk/Appinfo.json` with the same `Id` + `isShowOnLauncher:false` is **ignored**. Manual removal via the launcher (long-press OK → Delete) for `remove:1` apps is persistent across reboot.

## MQTT (36669, TLS, client certificate)
Topics `/remoteapp/tv/ui_service/{client}/actions/`: `applist`, `launchapp`, `sendkey`, `gettvstate`, `sourcelist`, `capability`… No `deleteapp`/`uninstallapp` exists (probed: no response).

## Ports (listening, after reboot)
53 dnsmasq (LAN DHCP+DNS), 1883/36669 MQTT(+TLS), 3366/3367 DIAL, 7000 AirPlay, 9080 NRDP (Netflix), 9009/9888 phoenix, 11669/11679, 16668/16669, 38400 (HTTP 404), 2121-2123, 3822/3823/3825, 10001, 12321.

## Processes
hisenseUI (launcher, uid 311), phoenix (1603+), mosquitto, dialserver, reggieserver, **hi_logreport_service** (telemetry), app_upgrade, ota_upgrade, iot_service, airplay_bridge.

## Dead ends / what does NOT work
- `--remote_debugging_port=9666` — port dead in the production build
- `setDebugPort` — "invalid" (security level)
- shadow Appinfo.json — merge prefers preset
- MQTT removal actions — do not exist
- launcher Chromium profile — EACCES from the phoenix namespace
- `/proc/<pid>/fd` — hangs the renderer (do not use!)
