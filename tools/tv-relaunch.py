# Reopens the bridge page in the TV browser via MQTT.
# Requires: pip install hisense-tv (the hisense_tv library), a paired client cert (vidaa_client.pem/key).
# Adjust TV_IP and MAC to your setup.
import sys, time
sys.path.insert(0, r"C:\path\to\site-packages")  # <- venv with hisense_tv
from hisense_tv import HisenseTV

TV_IP = "192.168.8.170"            # <- your TV's IP
MAC = "AA:BB:CC:DD:EE:FF"         # <- TV MAC (WiFi or LAN, the one used at pairing)

tv = HisenseTV(host=TV_IP, mac_address=MAC, use_dynamic_auth=True,
               certfile=r"C:\Users\user\Downloads\vidaa_client.pem",
               keyfile=r"C:\Users\user\Downloads\vidaa_client.key")
if not tv.connect(timeout=12):
    print("MQTT FAIL"); sys.exit(1)
tv.launch_app({"appId": "16", "name": "TV Browser", "url": "https://vidaahub.com/"})
print("launched")
time.sleep(4)
tv.disconnect()
