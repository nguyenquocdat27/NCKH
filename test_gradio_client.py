from gradio_client import Client, handle_file
import tempfile
import base64
import json

# Use a 1x1 pixel base64 image for testing
blank_image_base64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

HF_API_URL = "dat2709/nghiencuu"

try:
    print("Initiating gradio client to", HF_API_URL)
    client = Client(HF_API_URL)
    
    img_data = blank_image_base64.split(',')[1] if ',' in blank_image_base64 else blank_image_base64
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(base64.b64decode(img_data))
        tmp_file_path = tmp.name

    print("Sending prediction...")
    res_data = client.predict(
        image_input=handle_file(tmp_file_path),
        api_name="/predict"
    )
    
    print("Response:", res_data)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("Error:", e)
