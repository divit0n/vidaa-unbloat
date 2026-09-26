# vidaa-unbloat

Odchudzanie, przyspieszanie i odinwigilacja telewizora **Hisense 70A5FE z systemem VIDAA 9** (firmware V0000.09.09A.P0930, chipset MTK9602) — wykonane w całości zdalnie, przez sieć lokalną, bez otwierania TV i bez roota z perspektywy użytkownika.

Repo zawiera: opis techniki (DNS-spoof + mostek JS wbudowany w przeglądarkę TV), działające narzędzia oraz dokumentację **brudnych praktyk Hisense/VIDAA** wykrytych podczas eksploracji.

---

## 🕵️ Co Hisense robi Twoim telewizorem (udokumentowane praktyki)

Wszystko poniżej zaobserwowane na żywym urządzeniu w trakcie tego projektu (logi DNS z routera + bezpośredni odczyt systemu plików i procesów TV):

### 1. ACR — rozpoznawanie oglądanej treści
Telewizor regularnie łączy się z **`acr.unruly.co`** (14 zapytań w krótkim oknie obserwacji). ACR = Automatic Content Recognition: TV analizuje obraz/dźwięk tego, co oglądasz, i wysyła sygnatury do zewnętrznej firmy. Domyślnie włączone, bez sensownej informacji na ekranie.

### 2. Telemetria co ~20 sekund
- **`ter-jrnl-eu.vidaahub.com`** — 154 zapytania DNS w ciągu kilku godzin (dziennik zdarzeń VIDAA EU). Telewizor buduje się z uśpienia, żeby raportować.
- **`rpt-mntz-azure.vidaahub.com`**, **`rsc-mntz.vidaahub.com`** — raportowanie/monitoring z chmury Azure.
- **Netflix na telewizorze Hisense** wysyła logi do **`logs.netflix.com`** i **`nrdp.push.prod.netflix.com`** co ok. 20 s, niezależnie od tego, czy ktokolwiek ogląda.

### 3. Stały identyfikator reklamowy
System trzyma `adsID` — trwały identyfikator użytkownika do targetowania reklam (`kilby.sl2.str.system.adtarget.id`), odczytywany przez natywne API. W menu siedzi przy tym niewinna apk „Ads Privacy".

### 4. Bloatware, którego nie wolno usunąć
- ~45 aplikacji fabrycznych (preset). Część ma flagę `remove:0` — **nie da się ich usunąć nawet w trybie serwisowym**, bo lista preset jest zaszyta w natywnym kodzie launchera (hisenseUI). Wpisy-cienie w `Appinfo.json` są ignorowane — merge zawsze preferuje preset.
- Aplikacje z flagą `remove:1` da się usunąć ręcznie (długie OK → Usuń) i usunięcie **jest trwałe** (przetrwało reboot) — ale Hisense po instalacji ich nie oznacza i użytkownik nie wie, które można skasować.
- System potrafi też pozostawić aplikację w stanie **„półusuniętym"**: flaga `isunInstalled: true` jest ustawiona, a ikona dalej wisi na ekranie głównym i launcher jej nie ukrywa.

### 5. Półka sponsorska nie do ruszenia
Ekran główny ma wiersz aplikacji sponsorowanych (Rakuten, Boosteroid, Blacknut, Game Center…), których obecności nie kontroluje żadna flaga użytkownika. Lista pochodzi z binarki launchera — nie z konfiguracji, nie z chmury, którą można podmienić.

### 6. Telemetria systemowa
Proces **`hi_logreport_service`** działa stale w tle (zgłaszanie logów). Firmware przy pierwszym uruchomieniu wymusza zgody (EULA + osobna zgoda reklamowa).

---

## 🛠️ Technika (jak to zrobiliśmy)

1. **DNS-spoof**: własny serwer DNS odpowiada `vidaahub.com` adresem PC, resztę forwarduje do routera. TV ustawiony ręcznie na ten DNS.
2. **HTTPS**: własny certyfikat dla `vidaahub.com` (TV pyta o akceptację — jeden klik).
3. **Mostek JS**: strona otwarta w przeglądarce TV dostaje dostęp do mostka `vowOS`/phoenix wbudowanego w binarkę hisenseUI — enumeracja funkcji, wysyłanie poleceń JS (hotfolder `cnd/NNN.js` → wynik w `results.jsonl`).
4. **Path traversal w hiutils**: API `fileRead`/`fileWrite` skleja ścieżki z listy bazowych katalogów — `websdk/../../etc/passwd` daje **pełny odczyt i zapis plików na całym FS** (partycje RW: `/APPS`, `/data`, `/var/local`, `/OAD`, `/tmp`).
5. **API phoenix na localhost:9009**: usługi `hiutils`, `tvinfo` (natywne klucze „biz": jasność, kontrast, MEMC, tryb obrazu, MAC, identyfikatory), `fetcher` (serwerowy fetch), `ipchandler`. Wywoływane POST-em z poziomu strony w TV.
6. **MQTT (port 36669, TLS z certem klienckim)**: `applist`, `launchapp`, `sendkey` — biblioteka `hisense_tv`.

**Efekty**: usunięcie bloatu, jasność 100% + kontrast max + MEMC max ustawione przez natywne API, blacklista telemetrii, pełna mapa systemu (procesy, porty, mounty, partycje).

---

## 📁 Zawartość repo

- [`blocklist/domains.txt`](blocklist/domains.txt) — domeny do blokady (dnsmasq/OpenWrt/AGH/Pi-hole)
- [`tools/vidaa-cnc.py`](tools/vidaa-cnc.py) — serwer DNS+HTTPS+C&C z hotfolderem poleceń JS
- [`tools/tv-relaunch.py`](tools/tv-relaunch.py) — reopen strony mostka przez MQTT
- [`docs/FINDINGS.md`](docs/FINDINGS.md) — pełne ustalenia techniczne (procesy, porty, partycje, API, ścieżki)

## 🚀 Szybki start

```bash
pip install dnslib
# 1. wygeneruj self-signed cert dla vidaahub.com, włóż obok skryptu
# 2. ustaw PC_IP / UPSTREAM w vidaa-cnc.py
python tools/vidaa-cnc.py
# 3. w TV: ustaw DNS ręcznie na IP PC, otwórz https://vidaahub.com/ w przeglądarce
# 4. wrzucaj komendy JS do cnd/001.js, 002.js... — wyniki w results.jsonl
```

## ⚖️ Uwaga
Wszystko robione na własnym urządzeniu, na własnym rachunku. Telewizor to komputer, który stoi w Twoim salonie — masz prawo wiedzieć, co wysyła i decydować o tym.

Licencja: MIT.
