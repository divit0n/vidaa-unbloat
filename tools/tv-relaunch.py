# Otwiera/powtarza strone mostka w przegladarce TV przez MQTT.
# Wymaga: pip install hisense-tv (biblioteka hisense_tv), sparowany certyfikat kliencki (vidaa_client.pem/key).
# TV_IP i MAC dostosuj do swojej sieci.
import sys, time
sys.path.insert(0, r"C:\sciezka\do\site-packages")  # <- venv z hisense_tv
from hisense_tv import HisenseTV

TV_IP = "192.168.8.170"            # <- IP telewizora
MAC = "AA:BB:CC:DD:EE:FF"         # <- MAC TV (WiFi lub LAN, ten sam co przy parowaniu)

tv = HisenseTV(host=TV_IP, mac_address=MAC, use_dynamic_auth=True,
               certfile=r"C:\Users\user\Downloads\vidaa_client.pem",
               keyfile=r"C:\Users\user\Downloads\vidaa_client.key")
if not tv.connect(timeout=12):
    print("MQTT FAIL"); sys.exit(1)
tv.launch_app({"appId": "16", "name": "TV Browser", "url": "https://vidaahub.com/"})
print("launched")
time.sleep(4)
tv.disconnect()
