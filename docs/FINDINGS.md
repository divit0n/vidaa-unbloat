# Ustalenia techniczne — VIDAA 9 (Hisense 70A5FE, MTK9602)

## Architektura
- Launcher i wszystkie aplikacje: jedna binarka `./bin/hisenseUI` (Chromium-based) z argumentami `--remote_debugging_port=9666 --webdriver_port=4445 --url=file:///hisenseUI/index.html`. DevTools **nie działa** (port martwy w produkcyjnym buildzie).
- Backend JS: **phoenix** (Node, `/opt/pkgs/tv.vidaa.app.phoenix//bin/phoenix`, uid 314) — własne HTTP (9009) i WSS (9888) na localhost.
- Mostek `vowOS` wstrzykiwany do stron przez binarkę (nie przez `<script>`).

## API phoenix (localhost:9009, POST JSON)
- `/service/basic/hiutils` — `fileRead`, `fileWrite` (arg. `writedata`!), `installApplication`, `setDns`, `securityEncrypt/Decrypt`, `deviceCode`, `setDebugPort` (wymaga security level 2–6 → „invalid" w produkcji)
- `/service/basic/tvinfo` — odczyt kluczy „biz" + `setbiz {key, value}`: `brightness`, `contrast`, `memcStatus`, `pictureMode`, `lowLatencyMode`, `storeMode` (RO), `isHotelMode` (RO), `adsID` (RO), `dns`, `kidsMode`, `devtoolSwitch`
- `/service/basic/fetcher` — serwerowy fetch (`fetchResponse`, `fetchHead`, `fetchFile`)
- `/service/system/pkgmgr` — `getInstalledPkgs`
- Usługi niedostępne z LAN (firewall), tylko z poziomu TV.

## Path traversal (hiutils fileRead/fileWrite)
`path_list[mode] + path`, rozwiązywanie `..` przez FS:
0 `/tmp/`, 1 `/APPS/varlocal/applications/UI/`, 2 `/APPS/channelA/`, 3 `/APPS/varlocal/`, 4 `/data/`, 5 `/vddt/`, 6 `/APPS/`, 7 `/OAD/`
→ `websdk/../../etc/passwd` = pełny FS. RW: `/APPS` (mmcblk0p41), `/data`, `/cache`, `/var/local`, `/OAD`, `/var/tvservice`, `/tmp`. RO: `/`, `/application`, `/opt`, `/usr/local`.
Uwaga: `fileWrite` otwiera plik trybem `w` **przed** walidacją argumentów — błędne wywołanie = pusty plik.

## Lista aplikacji
45 pozycji preset + user. Merge `getInstalledApps` zawsze preferuje preset — shadow wpis w `/APPS/websdk/Appinfo.json` z tym samym `Id` + `isShowOnLauncher:false` **jest ignorowany**. Ręczne usunięcie przez launcher (długie OK → Usuń) dla `remove:1` jest trwałe.

## MQTT (36669, TLS, client-cert)
Topiki `/remoteapp/tv/ui_service/{client}/actions/`: `applist`, `launchapp`, `sendkey`, `gettvstate`, `sourcelist`, `capability`… Brak `deleteapp`/`uninstallapp` (sondowane: brak odpowiedzi).

## Porty (nasłuch, po restarcie)
53 dnsmasq(DHCP+DNS LAN), 1883/36669 MQTT(+TLS), 3366/3367 DIAL, 7000 AirPlay, 9080 NRDP (Netflix), 9009/9888 phoenix, 11669/11679, 16668/16669, 38400 (HTTP 404), 2121-2123, 3822/3823/3825, 10001, 12321.

## Procesy
hisenseUI (launcher, uid 311), phoenix (1603+), mosquitto, dialserver, reggieserver, **hi_logreport_service** (telemetria), app_upgrade, ota_upgrade, iot_service, airplay_bridge.

## Co NIE działa / ślepe uliczki
- `--remote_debugging_port=9666` — port martwy w buildzie produkcyjnym
- `setDebugPort` — „invalid" (security level)
- shadow Appinfo.json — merge preferuje preset
- akcje MQTT usuwania — nie istnieją
- profile Chromium launchera — EACCES z namespace phoenixa
- `/proc/<pid>/fd` — zawiesza renderer (nie używać!)
