#!/bin/sh
# verify-tv.sh — sprawdź, czy Twoja Hisense VIDAA dzwoni do domu (read-only, bez roota na TV)
# Użycie:  sh verify-tv.sh [interfejs] [czas_w_sekundach]
#    np.:  sh verify-tv.sh br-lan 3600
# Wymaga: tcpdump na routerze (OpenWrt/GL.iNet: opkg install tcpdump)
#
# Skrypt NASŁUCHUJE wyłącznie ruchu DNS w Twojej sieci. Nic nie modyfikuje.

IFACE="${1:-br-lan}"
DURATION="${2:-1800}"
OUT="vidaa-verify-$(date +%Y%m%d-%H%M%S).txt"

DOMAINS='vidaahub|unruly|netflix|doubleclick|ssai|hisense|hicloud|netify|crashlytics|app-measurement'

echo "=== vidaa-unbloat :: verify-tv ==="
echo "Interfejs: $IFACE   Czas: ${DURATION}s   Wynik: $OUT"
echo "Zostaw TV na ekranie głównym (idle). Nie oglądaj niczego podczas testu."
echo "Nasłuchuję DNS... (Ctrl+C aby przerwać)"
echo

timeout "$DURATION" tcpdump -i "$IFACE" -n -l port 53 2>/dev/null | tee "$OUT" | \
while IFS= read -r line; do
  echo "$line" | grep -oiE "$DOMAINS" >/dev/null && echo "  >> $line"
done

echo
echo "=== PODSUMOWANIE ==="
echo "Przejęte linie DNS z domenami śledzącymi:"
grep -oiE "$DOMAINS" "$OUT" | sort | uniq -c | sort -rn
echo
TV_IP=$(grep -oE 'A\? [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' "$OUT" | head -1)
echo "Pierwsze tropy zapisane w: $OUT"
echo
echo "WERYDYKACJA — szukaj tych domen w logu:"
for d in ter-jrnl-eu.vidaahub.com acr.unruly.co logs.netflix.com rpt-mntz-azure.vidaahub.com; do
  n=$(grep -c "$d" "$OUT")
  if [ "$n" -gt 0 ]; then
    echo "  [ZNALEZIONO x$n] $d"
  else
    echo "  [brak]        $d"
  fi
done
echo
echo "Interpretacja: znalezienie ter-jrnl-eu/acr.unruly/logs.netflix w trybie idle"
echo "oznacza, że TV raportuje bez Twojego udziału. Zobacz README -> Level 2 jak to wyłączyć."
