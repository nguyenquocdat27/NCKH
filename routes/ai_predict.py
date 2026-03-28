import io
import os
import base64
import requests
from flask import Blueprint, request, jsonify

ai_bp = Blueprint('ai', __name__)

# ========================================================
# CẤU HÌNH AI (Ưu tiên Hugging Face để tiết kiệm RAM)
# ========================================================
HF_API_URL = os.getenv('HUGGINGFACE_API_URL') # Ví dụ: "https://dat2709-nchk.hf.space/api/predict" (tùy API của Space)
HF_TOKEN   = os.getenv('HUGGINGFACE_TOKEN')

# Cấu hình local (Chỉ dùng nếu không có HF_API_URL và có RAM > 1GB)
try:
    import torch
    import torch.nn as nn
    import torchvision.transforms as transforms
    import torchvision.models as models
    import numpy as np
    from PIL import Image
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

MODEL_PATH = 'multilabel_model_gpu.pth'
NUTRIENTS = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]
N_CLASSES  = 7
THRESHOLD  = 0.5

NUTRIENT_NAMES = {
    "Ca": "Canxi (Ca)", "K": "Kali (K)", "Mn": "Mangan (Mn)",
    "N": "Đạm (N)",     "P": "Lân (P)", "S": "Lưu huỳnh (S)", "Zn": "Kẽm (Zn)"
}

SEVERITY_LEVELS = {
    (0.50, 0.65): ("Nhẹ",        "#f59e0b", "🟡"),
    (0.65, 0.80): ("Trung bình", "#f97316", "🟠"),
    (0.80, 1.01): ("Nặng",       "#ef4444", "🔴"),
}

RECOMMENDATIONS = {
    "N":  "Bổ sung phân Đạm (Urê), tỉa bớt lá già, tưới đủ nước để cây hấp thụ tốt hơn.",
    "P":  "Bổ sung phân Lân (Super lân), kiểm tra độ pH đất, nếu đất chua cần bón thêm vôi.",
    "K":  "Bổ sung Kali (K2SO4 hoặc KCl), giúp cây chịu hạn và tăng cường vận chuyển nước.",
    "Ca": "Bón thêm vôi bột hoặc Canxi Nitrate để cải thiện cấu trúc tế bào lá mới.",
    "Mn": "Phun phân bón lá chứa Mangan Sunfat, tránh để đất quá kiềm (pH cao).",
    "S":  "Bổ sung phân bón chứa Lưu huỳnh (như thạch cao bón đất hoặc phân SA).",
    "Zn": "Phun Kẽm Sunfat (ZnSO4) trực tiếp lên lá để cây phục hồi nhanh nhất.",
}

model = None
gradcam = None

# --- LOCAL TORCH LOGIC ---
if HAS_TORCH:
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    class GradCAM:
        def __init__(self, net):
            self.net = net
            self.gradients = self.activations = None
            net.layer4.register_forward_hook(lambda m, i, o: setattr(self, 'activations', o.detach()))
            net.layer4.register_full_backward_hook(lambda m, gi, go: setattr(self, 'gradients', go[0].detach()))
        def generate(self, tensor, class_idx):
            self.net.zero_grad()
            self.net(tensor)[0, class_idx].backward()
            weights = self.gradients.mean(dim=[2, 3], keepdim=True)
            cam = torch.relu((weights * self.activations).sum(dim=1).squeeze()).cpu().numpy()
            return cam / cam.max() if cam.max() > 0 else cam

def load_model():
    global model, gradcam
    if HF_API_URL:
        print(f"🚀 AI Mode: Hugging Face API ({HF_API_URL})")
        return
    if not HAS_TORCH:
        print("⚠️  Thiếu thư viện Torch — Chế độ DEMO")
        return
    try:
        if os.path.exists(MODEL_PATH):
            net = models.resnet18(weights=None)
            net.fc = nn.Linear(net.fc.in_features, N_CLASSES)
            net.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
            net.to(DEVICE).eval()
            model, gradcam = net, GradCAM(net)
            print(f"✅ Local Model Loaded: {DEVICE}")
    except Exception as e: print(f"❌ Error loading model: {e}")

@ai_bp.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({'error': 'Thiếu ảnh'}), 400

        # MODO 1: Hugging Face (Augmented)
        if HF_API_URL:
            headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
            response = requests.post(HF_API_URL, json=data, headers=headers, timeout=30)
            if response.status_code == 200:
                res_data = response.json()
                # Bổ sung/Ghi đè lời khuyên tiếng Việt từ Backend vào response của HF
                return _build_response(res_data.get('scores', {}), res_data.get('heatmaps', {}), demo=False)
            return jsonify({'error': f'HF API Error: {response.text}'}), 502

        # MODO 2: Local
        if model and HAS_TORCH:
            from PIL import Image
            import io
            img_data = base64.b64decode(data['image'].split(',')[1] if ',' in data['image'] else data['image'])
            orig_img = Image.open(io.BytesIO(img_data)).convert('RGB')
            
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            tensor = transform(orig_img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                probs = torch.sigmoid(model(tensor)[0]).cpu().tolist()
            
            scores = {NUTRIENTS[i]: round(probs[i], 4) for i in range(N_CLASSES)}
            return _build_response(scores, {}, demo=False)

        # MODO 3: Demo
        import random
        scores = {n: round(random.uniform(0.05, 0.95), 3) for n in NUTRIENTS}
        return _build_response(scores, {}, demo=True)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def _get_severity(prob):
    for (lo, hi), val in SEVERITY_LEVELS.items():
        if lo <= prob < hi: return val
    return "Bình thường", "#10b981", "🟢"

def _build_response(scores, heatmaps, demo):
    deficient = [n for n, p in scores.items() if p >= THRESHOLD]
    healthy   = len(deficient) == 0
    detail = []
    
    for n in deficient:
        sl, sc, si = _get_severity(scores[n])
        detail.append({
            'nutrient': n, 'name': NUTRIENT_NAMES.get(n, n),
            'probability': scores[n], 'severity': sl, 'severity_color': sc, 'severity_icon': si,
            'recommendation': RECOMMENDATIONS.get(n, "Cần theo dõi thêm."),
            'heatmap': heatmaps.get(n)
        })
    
    # Sắp xếp theo xác suất giảm dần
    detail.sort(key=lambda x: x['probability'], reverse=True)
    
    # Tạo danh sách lời khuyên tổng hợp
    recs = []
    if healthy:
        recs.append("✅ Cây có vẻ khỏe mạnh! Hãy duy trì chế độ phân bón và nước tưới hiện tại.")
    else:
        for d in detail:
            recs.append(f"{d['severity_icon']} **{d['name']} ({d['severity']})**: {d['recommendation']}")

    return jsonify({
        'healthy': healthy,
        'deficient_detail': detail,
        'deficient_names': [NUTRIENT_NAMES.get(n, n) for n in deficient],
        'scores': scores,
        'recommendations': recs,
        'demo_mode': demo,
        'threshold': THRESHOLD
    })

@ai_bp.route('/status')
def status():
    return jsonify({
        'server': 'running',
        'ai_mode': 'huggingface' if HF_API_URL else ('local' if model else 'demo'),
        'has_torch': HAS_TORCH
    })
