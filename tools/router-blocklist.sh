#!/bin/sh
# router-blocklist.sh — zainstaluj blacklistę telemetrii na OpenWrt/GL.iNet (dnsmasq)
# Użycie:  sh router-blocklist.sh            (instaluje)
#          sh router-blocklist.sh remove     (usuwa wszystkie wpisy)
# Wykonaj na routerze przez SSH. Po instalacji każde urządzenie w LAN przestanie
# rozwiązywać te domeny (0.0.0.0). Usuń wcześniejsze duplikaty ręcznie jeśli były.

set -e

DOMAINS="ter-jrnl-eu.vidaahub.com ter-jrnl-na.vidaahub.com telemetry.vidaahub.com metrics.vidaahub.com rpt-mntz-azure.vidaahub.com rsc-mntz.vidaahub.com acr.unruly.co logs.netflix.com nrdp.push.prod.netflix.com doubleclick.net pixel.ssai.media"

cmd="${1:-install}"

if [ "$cmd" = "remove" ]; then
  echo "Usuwam blacklistę..."
  uci -q delete dhcp.@dnsmasq[0].address || true
  uci commit dhcp
  /etc/init.d/dnsmasq restart
  echo "Gotowe."
  exit 0
fi

echo "Instaluję blacklistę telemetrii (dnsmasq address=)..."
for d in $DOMAINS; do
  uci add_list dhcp.@dnsmasq[0].address="/$d/0.0.0.0"
done
uci commit dhcp
/etc/init.d/dnsmasq restart
sleep 2
echo
echo "Weryfikacja:"
for d in ter-jrnl-eu.vidaahub.com acr.unruly.co logs.netflix.com; do
  r=$(nslookup "$d" 127.0.0.1 2>/dev/null | grep -m1 'Address 1' | awk '{print $3}')
  echo "  $d -> ${r:-BRAK ODPOWIEDZI}"
done
echo
echo "Oczekiwane: 0.0.0.0 dla każdej z powyższych."
echo "Netflix/apki działają normalnie — zamknięty jest tylko kanał raportowania."
