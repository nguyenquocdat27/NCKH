# Lưu file này ở: d:\NCKH\MAIN\research_archive\test_thucte.py
import os
import torch
import torchvision.transforms as transforms
import torchvision.models as models
import pandas as pd
from PIL import Image

IMAGE_DIR = "test_thucte" # Bỏ ảnh lá thật vừa chụp vào thư mục này
MODEL_PATH = "AI/multilabel_model_gpu.pth"
NUTRIENTS = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]
N_CLASSES = 7; THRESHOLD = 0.5

def main():
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)
        print(f"Đã tạo thư mục {IMAGE_DIR}. Hãy copy ảnh vào đây rồi chạy lại.")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(model.fc.in_features, N_CLASSES)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.to(device).eval()

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    results = []
    print(f"{'Tên ảnh':<20} | {'Dự đoán của AI':<30}")
    print("-" * 55)

    for img_name in os.listdir(IMAGE_DIR):
        if not img_name.lower().endswith(('.png', '.jpg', '.jpeg')): continue
        image = Image.open(os.path.join(IMAGE_DIR, img_name)).convert("RGB")
        tensor = transform(image).unsqueeze(0).to(device)

        with torch.no_grad():
            probs = torch.sigmoid(model(tensor)).cpu().numpy()[0]
        
        preds = [NUTRIENTS[i] for i in range(N_CLASSES) if probs[i] >= THRESHOLD]
        pred_str = ", ".join(preds) if preds else "Healthy"
        
        results.append({"Lần chụp": img_name, "Lớp thực tế": "Bạn tự điền", "AI Dự đoán": pred_str})
        print(f"{img_name:<20} | {pred_str:<30}")

    pd.DataFrame(results).to_csv("ket_qua_thuc_te_cho_bao_cao.csv", index=False)
    print("\n✅ Đã lưu kết quả ra file CSV, mở bằng Excel rồi copy vào báo cáo!")

if __name__ == "__main__":
    main()