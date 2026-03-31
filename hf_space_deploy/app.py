import os
import io
import base64
import torch
import torch.nn as nn
from torchvision import models
from torchvision.transforms import functional as TF
from PIL import Image
import gradio as gr

print(f"[STARTUP] torch={torch.__version__}")
try:
    import numpy as np
    print(f"[STARTUP] numpy={np.__version__} OK")
    HAS_NUMPY = True
except Exception as e:
    print(f"[STARTUP] numpy UNAVAILABLE: {e}")
    HAS_NUMPY = False

# ========================================================
# CONFIG
# ========================================================
MODEL_PATH = "multilabel_model_gpu.pth"
NUTRIENTS  = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]
N_CLASSES  = 7
DEVICE     = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ========================================================
# MODEL DEFINITION
# ========================================================
def get_model():
    net = models.resnet18(weights=None)
    net.fc = nn.Linear(net.fc.in_features, N_CLASSES)
    if os.path.exists(MODEL_PATH):
        try:
            checkpoint = torch.load(MODEL_PATH, map_location=DEVICE)
            net.load_state_dict(checkpoint)
            print(f"✅ Model loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"❌ Error loading weights: {e}")
    else:
        print(f"⚠️  {MODEL_PATH} not found. Using random weights.")
    net.to(DEVICE).eval()
    return net

model = get_model()

# ========================================================
# INFERENCE LOGIC
# ========================================================
# Normalize constants
_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
_STD  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)

def pil_to_tensor_normalized(img: Image.Image) -> torch.Tensor:
    """Convert PIL Image -> normalized float tensor WITHOUT requiring numpy."""
    img = img.resize((224, 224), Image.BILINEAR)
    # TF.pil_to_tensor returns uint8 [C,H,W]
    t = TF.pil_to_tensor(img).float() / 255.0
    return (t - _MEAN) / _STD

def predict_image(image_input):
    """
    Nhận PIL Image từ Gradio UI hoặc base64 string từ API call.
    Trả về dict scores theo format tương thích với main app.
    """
    if image_input is None:
        return {"error": "No image provided"}

    # Chuyển sang PIL nếu là base64 string
    if isinstance(image_input, str):
        if ',' in image_input:
            image_input = image_input.split(',')[1]
        img_bytes = base64.b64decode(image_input)
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    else:
        img = image_input.convert("RGB")

    # Transform & Run (numpy-free)
    input_tensor = pil_to_tensor_normalized(img).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        outputs = model(input_tensor)
        probs = torch.sigmoid(outputs[0]).cpu().tolist()
    print(f"[PREDICT] probs={[round(p,3) for p in probs]}")

    scores = {NUTRIENTS[i]: round(probs[i], 4) for i in range(N_CLASSES)}

    return {
        "scores": scores,
        "heatmaps": {}  # Grad-CAM placeholder
    }

# ========================================================
# GRADIO INTERFACE (Gradio 6.x compatible)
# ========================================================
iface = gr.Interface(
    fn=predict_image,
    inputs=gr.Image(type="pil", label="Ảnh lá cây"),
    outputs=gr.JSON(label="Kết quả phân tích"),
    title="NCKH AI - Phát hiện thiếu dinh dưỡng cây trồng",
    description="API Endpoint để phát hiện thiếu dinh dưỡng ở cây trồng từ ảnh lá.",
    api_name="predict"  # Đặt tên API endpoint là /predict
)

if __name__ == "__main__":
    iface.launch()
