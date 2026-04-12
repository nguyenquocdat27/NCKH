import requests
import json

url = "https://nckh-ai.onrender.com/api/predict"

# Base64 1x1 PNG image
img_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="

payload = {
    "image": img_b64
}

try:
    res = requests.post(url, json=payload)
    print("STATUS:", res.status_code)
    print("RESPONSE:", res.text)
except Exception as e:
    print("ERROR:", e)
