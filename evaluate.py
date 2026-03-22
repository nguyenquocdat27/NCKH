

import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.metrics import (
    f1_score, precision_score, recall_score,
    hamming_loss, classification_report
)

# ====================================================
# CONFIG — giữ nguyên như train
# ====================================================
DATA_DIR   = "multilabel_dataset"
MODEL_PATH = "multilabel_model_gpu.pth"
NUTRIENTS  = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]
N_CLASSES  = 7
THRESHOLD  = 0.5
BATCH_SIZE = 16

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ====================================================
# DATASET + TRANSFORM (giống val trong train)
# ====================================================
class PlantDataset(Dataset):
    def __init__(self, csv_file, img_dir, transform=None):
        self.data      = pd.read_csv(csv_file)
        self.img_dir   = img_dir
        self.transform = transform

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        img_path = os.path.join(self.img_dir, self.data.iloc[idx, 0])
        image    = Image.open(img_path).convert("RGB")
        labels   = torch.tensor(
            self.data.iloc[idx, 1:].values.astype("float32")
        )
        if self.transform:
            image = self.transform(image)
        return image, labels

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std =[0.229, 0.224, 0.225]
    ),
])

val_dataset = PlantDataset(
    os.path.join(DATA_DIR, "val.csv"),
    os.path.join(DATA_DIR, "images"),
    val_transform
)
val_loader = DataLoader(
    val_dataset, batch_size=BATCH_SIZE,
    shuffle=False, num_workers=0
)

# ====================================================
# TẢI MODEL
# ====================================================
model    = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, N_CLASSES)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model    = model.to(DEVICE)
model.eval()
print(f"✅ Đã load model: {MODEL_PATH}\n")

# ====================================================
# INFERENCE TRÊN TẬP VAL
# ====================================================
all_labels = []
all_preds  = []

with torch.no_grad():
    for images, labels in val_loader:
        images  = images.to(DEVICE)
        outputs = model(images)
        probs   = torch.sigmoid(outputs).cpu().numpy()
        preds   = (probs >= THRESHOLD).astype(int)

        all_labels.append(labels.numpy())
        all_preds.append(preds)

all_labels = np.vstack(all_labels)   # shape: (N, 7)
all_preds  = np.vstack(all_preds)    # shape: (N, 7)

# ====================================================
# TÍNH CHỈ SỐ
# ====================================================
print("=" * 60)
print("  KẾT QUẢ ĐÁNH GIÁ MODEL")
print("=" * 60)

results = []
for i, nutrient in enumerate(NUTRIENTS):
    f1        = f1_score      (all_labels[:, i], all_preds[:, i], zero_division=0)
    precision = precision_score(all_labels[:, i], all_preds[:, i], zero_division=0)
    recall    = recall_score  (all_labels[:, i], all_preds[:, i], zero_division=0)
    support   = int(all_labels[:, i].sum())   # số ảnh thật có chất này

    results.append({
        'Chất':      nutrient,
        'F1-Score':  round(f1, 4),
        'Precision': round(precision, 4),
        'Recall':    round(recall, 4),
        'Support':   support,
    })

    status = "✅" if f1 >= 0.7 else ("⚠️ " if f1 >= 0.5 else "❌")
    print(f"{status} {nutrient:4s} | F1: {f1:.4f} | "
          f"Precision: {precision:.4f} | Recall: {recall:.4f} | "
          f"Support: {support}")

# Chỉ số tổng hợp
f1_macro  = f1_score(all_labels, all_preds, average='macro',  zero_division=0)
f1_micro  = f1_score(all_labels, all_preds, average='micro',  zero_division=0)
f1_sample = f1_score(all_labels, all_preds, average='samples',zero_division=0)
h_loss    = hamming_loss(all_labels, all_preds)

print("\n" + "-" * 60)
print(f"  F1 Macro   : {f1_macro:.4f}  (trung bình các chất, không cân bằng)")
print(f"  F1 Micro   : {f1_micro:.4f}  (tính theo từng nhãn)")
print(f"  F1 Samples : {f1_sample:.4f}  (trung bình theo ảnh)")
print(f"  Hamming Loss: {h_loss:.4f}  (càng gần 0 càng tốt)")
print("-" * 60)

# ====================================================
# LƯU KẾT QUẢ
# ====================================================
df_results = pd.DataFrame(results)
df_results.to_csv("evaluate_results.csv", index=False)
print(f"\n💾 Kết quả lưu tại: evaluate_results.csv")

# ====================================================
# VẼ BIỂU ĐỒ
# ====================================================
try:
    import matplotlib
    matplotlib.use('Agg')          # không cần GUI
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Kết quả đánh giá Model AI Nông Nghiệp", fontsize=14, fontweight='bold')

    # --- Biểu đồ 1: F1 / Precision / Recall theo từng chất ---
    x     = np.arange(len(NUTRIENTS))
    width = 0.25
    ax1   = axes[0]

    ax1.bar(x - width, df_results['F1-Score'],  width, label='F1-Score',  color='#3b82f6')
    ax1.bar(x,         df_results['Precision'], width, label='Precision', color='#10b981')
    ax1.bar(x + width, df_results['Recall'],    width, label='Recall',    color='#f59e0b')

    ax1.axhline(y=0.7, color='red', linestyle='--', alpha=0.5, label='Ngưỡng tốt (0.7)')
    ax1.set_xlabel('Chất dinh dưỡng')
    ax1.set_ylabel('Điểm số')
    ax1.set_title('F1 / Precision / Recall theo từng chất')
    ax1.set_xticks(x)
    ax1.set_xticklabels(NUTRIENTS)
    ax1.set_ylim(0, 1.1)
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

   
    ax2 = axes[1]
    if os.path.exists("train_history.csv"):
        history = pd.read_csv("train_history.csv")
        ax2.plot(history['epoch'], history['train_loss'],
                 label='Train Loss', color='#3b82f6', linewidth=2)
        ax2.plot(history['epoch'], history['val_loss'],
                 label='Val Loss',   color='#ef4444', linewidth=2)
        ax2.set_xlabel('Epoch')
        ax2.set_ylabel('Loss')
        ax2.set_title('Lịch sử Train / Validation Loss')
        ax2.legend()
        ax2.grid(alpha=0.3)
        best_epoch = history.loc[history['val_loss'].idxmin(), 'epoch']
        best_loss  = history['val_loss'].min()
        ax2.axvline(x=best_epoch, color='green', linestyle='--', alpha=0.6,
                    label=f'Best epoch {best_epoch}')
        ax2.annotate(f'Best: {best_loss:.4f}',
                     xy=(best_epoch, best_loss),
                     xytext=(best_epoch + 1, best_loss + 0.02),
                     fontsize=9, color='green')
    else:
        ax2.text(0.5, 0.5, 'Chưa có train_history.csv\nChạy train trước',
                 ha='center', va='center', transform=ax2.transAxes,
                 fontsize=12, color='gray')
        ax2.set_title('Lịch sử Train Loss')

    plt.tight_layout()
    plt.savefig("evaluate_chart.png", dpi=150, bbox_inches='tight')
    print("📊 Biểu đồ lưu tại: evaluate_chart.png")
    plt.close()

except ImportError:
    print("⚠️  Cài matplotlib để vẽ biểu đồ: pip install matplotlib")

# ====================================================
# TÓM TẮT
# ====================================================
print("\n" + "=" * 60)
print("  TÓM TẮT")
print("=" * 60)

good    = [r for r in results if r['F1-Score'] >= 0.7]
warning = [r for r in results if 0.5 <= r['F1-Score'] < 0.7]
bad     = [r for r in results if r['F1-Score'] < 0.5]

if good:
    print(f"✅ Tốt (F1≥0.7)     : {[r['Chất'] for r in good]}")
if warning:
    print(f"⚠️  Trung bình       : {[r['Chất'] for r in warning]}")
if bad:
    print(f"❌ Cần cải thiện    : {[r['Chất'] for r in bad]}")

print(f"\n→ F1 Macro tổng thể : {f1_macro:.4f}")
if f1_macro >= 0.8:
    print("🏆 Model tốt — sẵn sàng cho báo cáo nghiên cứu!")
elif f1_macro >= 0.65:
    print("📈 Model khá — có thể dùng, nên train thêm data.")
else:
    print("🔧 Model cần cải thiện — thêm data hoặc train lại.")
