import time
import requests
import os
import threading

def ping_self():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        return
    while True:
        try:
            requests.get(url)
            print("Ping successful")
        except:
            print("Ping failed")
        time.sleep(600) # Раз в 10 минут

if __name__ == "__main__":
    threading.Thread(target=ping_self, daemon=True).start()
