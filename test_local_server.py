import requests
import base64

blank_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

payload = {"image": blank_image_base64}
headers = {'Content-Type': 'application/json'}

try:
    print("Testing local Flask /api/predict...")
    response = requests.post("http://localhost:5000/api/predict", json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print("Response text:", response.text)
except Exception as e:
    print("Error connecting to localhost:5000:", e)
