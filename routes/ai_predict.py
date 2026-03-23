import io
import os
import base64
from flask import Blueprint, request, jsonify
from PIL import Image
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import numpy as np

ai_bp = Blueprint('ai', __name__)

MODEL_PATH = 'multilabel_model_gpu.pth'

NUTRIENTS = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]
N_CLASSES  = 7
THRESHOLD  = 0.5

NUTRIENT_NAMES = {
    "Ca": "Canxi (Ca)",        "K":  "Kali (K)",
    "Mn": "Mangan (Mn)",       "N":  "Đạm / Nitrogen (N)",
    "P":  "Lân / Phosphorus (P)", "S": "Lưu huỳnh (S)",
    "Zn": "Kẽm (Zn)",
}

SEVERITY_LEVELS = {
    (0.50, 0.65): ("Nhẹ",        "#f59e0b", "🟡"),
    (0.65, 0.80): ("Trung bình", "#f97316", "🟠"),
    (0.80, 1.01): ("Nặng",       "#ef4444", "🔴"),
}

RECOMMENDATIONS = {
    "Ca": "Bổ sung Ca",
    "K":  "Bổ sung K",
    "Mn": "Bổ sung Mn",
    "N":  "Bổ sung N",
    "P":  "Bổ sung P",
    "S":  "Bổ sung S",
    "Zn": "Bổ sung Zn",
}

DEVICE  = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model   = None
gradcam = None


class GradCAM:
    def __init__(self, net):
        self.net = net
        self.gradients = self.activations = None
        net.layer4.register_forward_hook(self._save_activation)
        net.layer4.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, m, i, o): self.activations = o.detach()
    def _save_gradient(self, m, gi, go): self.gradients   = go[0].detach()

    def generate(self, tensor, class_idx):
        self.net.zero_grad()
        self.net(tensor)[0, class_idx].backward()
        weights = self.gradients.mean(dim=[2, 3], keepdim=True)
        cam = torch.relu((weights * self.activations).sum(dim=1).squeeze())
        cam = cam.cpu().numpy()
        if cam.max() > 0:
            cam = cam / cam.max()
        return cam


def cam_to_heatmap_b64(cam, orig_img):
    w, h = orig_img.size
    cam_r = np.array(
        Image.fromarray((cam * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
    ) / 255.0
    r = np.clip(cam_r * 2, 0, 1)
    g = np.clip(2 - cam_r * 2, 0, 1)
    b = np.zeros_like(cam_r)
    heatmap = Image.fromarray((np.stack([r, g, b], 2) * 255).astype(np.uint8)).convert("RGBA")
    heatmap.putalpha(Image.fromarray((cam_r * 180).astype(np.uint8)))
    blended = Image.alpha_composite(orig_img.convert("RGBA"), heatmap).convert("RGB")
    buf = io.BytesIO()
    blended.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def load_model():
    global model, gradcam
    try:
        if not os.path.exists(MODEL_PATH):
            print(f"⚠️  Không tìm thấy {MODEL_PATH} — Chạy chế độ DEMO")
            return

        net    = models.resnet18(weights=None)
        net.fc = nn.Linear(net.fc.in_features, N_CLASSES)
        net.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
        net.to(DEVICE).eval()
        model   = net
        gradcam = GradCAM(net)
        print(f"✅ Model: {MODEL_PATH} | Device: {DEVICE} | GradCAM: bật")
    except Exception as e:
        print(f"❌ Lỗi model: {e} — Tự động chuyển qua chế độ DEMO")
        model = None


transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

def b64_to_pil(b64):
    if ',' in b64: b64 = b64.split(',')[1]
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert('RGB')

def get_severity(prob):
    for (lo, hi), val in SEVERITY_LEVELS.items():
        if lo <= prob < hi: return val
    return "Bình thường", "#10b981", "🟢"


@ai_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'Thiếu trường "image"'}), 400

        if model is None:
            import random
            deficient = random.sample(NUTRIENTS, k=random.randint(1, 3))
            scores = {n: round(random.uniform(0.7, 0.95) if n in deficient
                               else random.uniform(0.05, 0.4), 3) for n in NUTRIENTS}
            return _build_response(scores, {}, demo=True)

        orig_img = b64_to_pil(data['image'])
        tensor   = transform(orig_img).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            probs = torch.sigmoid(model(tensor)[0]).cpu().tolist()

        scores    = {NUTRIENTS[i]: round(probs[i], 4) for i in range(N_CLASSES)}
        deficient = [n for n, p in scores.items() if p >= THRESHOLD]

        heatmaps = {}
        for nutrient in deficient:
            idx = NUTRIENTS.index(nutrient)
            t   = transform(orig_img).unsqueeze(0).to(DEVICE)
            heatmaps[nutrient] = cam_to_heatmap_b64(gradcam.generate(t, idx), orig_img)

        return _build_response(scores, heatmaps, demo=False)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _build_response(scores, heatmaps, demo):
    deficient = [n for n, p in scores.items() if p >= THRESHOLD]
    healthy   = len(deficient) == 0
    detail    = []
    for n in deficient:
        sl, sc, si = get_severity(scores[n])
        detail.append({
            'nutrient': n, 'name': NUTRIENT_NAMES[n],
            'probability': scores[n],
            'severity': sl, 'severity_color': sc, 'severity_icon': si,
            'recommendation': RECOMMENDATIONS[n],
            'heatmap': heatmaps.get(n),
        })
    detail.sort(key=lambda x: x['probability'], reverse=True)
    recs = (["✅ Cây khỏe mạnh! Tiếp tục chăm sóc bình thường."] if healthy
            else [f"{d['severity_icon']} Thiếu {d['name']} ({d['severity']}): {d['recommendation']}"
                  for d in detail])
    return jsonify({
        'healthy': healthy, 'deficient_detail': detail,
        'deficient_nutrients': deficient,
        'deficient_names': [NUTRIENT_NAMES[n] for n in deficient],
        'scores': scores, 'recommendations': recs,
        'threshold': THRESHOLD, 'demo_mode': demo,
    })


@ai_bp.route('/status')
def status():
    return jsonify({
        'server': 'running', 'model_loaded': model is not None,
        'gradcam': gradcam is not None, 'device': str(DEVICE),
    })
