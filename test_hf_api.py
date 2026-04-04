import requests
import json
import base64

# Use a 1x1 pixel base64 image for testing
blank_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

payload = {"data": [blank_image_base64]}
headers = {'Content-Type': 'application/json'}

urls = [
    "https://dat2709-nghiencuu.hf.space/call/predict",
    "https://dat2709-nghiencuu.hf.space/gradio_api/call/predict",
    "https://dat2709-nghiencuu.hf.space/run/predict",
]

for HF_API_URL in urls:
    print(f"\nSending to {HF_API_URL}...")
    try:
        response = requests.post(HF_API_URL, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print("Response text:", response.text[:200])
    except Exception as e:
        print("Error:", e)
