import os
import pandas as pd
import torch
import torch.nn as nn
import torchvision.transforms as transforms
from torchvision import models
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from tqdm import tqdm

# ====================================================
# CONFIG
# ====================================================
DATA_DIR    = "multilabel_dataset"
BATCH_SIZE  = 16
EPOCHS      = 50          # tăng từ 10 → 50
LR          = 0.0001
N_CLASSES   = 7
NUTRIENTS   = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]

# Early stopping: dừng nếu val_loss không cải thiện sau N epoch
EARLY_STOP_PATIENCE = 8

SAVE_PATH   = "multilabel_model_gpu.pth"

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if torch.cuda.is_available():
    print("🔥 GPU:", torch.cuda.get_device_name(0))
    torch.backends.cudnn.benchmark = True
else:
    print("⚠  CPU mode")

# ====================================================
# DATASET
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

# ====================================================
# TRANSFORM
# Thêm so với bản cũ:
#   - Normalize (ImageNet mean/std) → cải thiện độ chính xác đáng kể
#   - Data augmentation cho tập train → model tổng quát hơn
# ====================================================
NORMALIZE = transforms.Normalize(
    mean=[0.485, 0.456, 0.406],
    std =[0.229, 0.224, 0.225]
)

train_transform = transforms.Compose([
    transforms.Resize((256, 256)),
    transforms.RandomCrop(224),                          # random crop thay resize thẳng
    transforms.RandomHorizontalFlip(p=0.5),              # lật ngang
    transforms.RandomVerticalFlip(p=0.2),                # lật dọc
    transforms.RandomRotation(degrees=20),               # xoay ±20°
    transforms.ColorJitter(
        brightness=0.3, contrast=0.3,
        saturation=0.3, hue=0.1
    ),                                                   # thay đổi màu sắc
    transforms.ToTensor(),
    NORMALIZE,
])

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    NORMALIZE,
])

# ====================================================
# DATALOADER
# ====================================================
train_dataset = PlantDataset(
    os.path.join(DATA_DIR, "train.csv"),
    os.path.join(DATA_DIR, "images"),
    train_transform
)
val_dataset = PlantDataset(
    os.path.join(DATA_DIR, "val.csv"),
    os.path.join(DATA_DIR, "images"),
    val_transform
)

train_loader = DataLoader(
    train_dataset, batch_size=BATCH_SIZE,
    shuffle=True, num_workers=0, pin_memory=True
)
val_loader = DataLoader(
    val_dataset, batch_size=BATCH_SIZE,
    shuffle=False, num_workers=0, pin_memory=True
)

print(f"📦 Train: {len(train_dataset)} ảnh | Val: {len(val_dataset)} ảnh")

# ====================================================
# MODEL
# ====================================================
model    = models.resnet18(weights="IMAGENET1K_V1")
model.fc = nn.Linear(model.fc.in_features, N_CLASSES)
model    = model.to(DEVICE)

criterion = nn.BCEWithLogitsLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)

# Learning rate giảm dần khi val_loss không cải thiện
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, mode='min', factor=0.5, patience=4
)

# ====================================================
# TRAIN LOOP
# ====================================================
best_val_loss    = float('inf')
patience_counter = 0
history          = []   # lưu log để vẽ biểu đồ sau

print("\n🚀 Bắt đầu train...\n")

for epoch in range(EPOCHS):

    # ---------- TRAIN ----------
    model.train()
    train_loss = 0.0
    loop = tqdm(train_loader, desc=f"Epoch {epoch+1:02d}/{EPOCHS} [Train]", leave=False)

    for images, labels in loop:
        images = images.to(DEVICE, non_blocking=True)
        labels = labels.to(DEVICE, non_blocking=True)

        optimizer.zero_grad()
        outputs = model(images)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        loop.set_postfix(loss=f"{loss.item():.4f}")

    train_loss /= len(train_loader)

    # ---------- VALIDATION ----------
    model.eval()
    val_loss = 0.0

    with torch.no_grad():
        for images, labels in val_loader:
            images  = images.to(DEVICE, non_blocking=True)
            labels  = labels.to(DEVICE, non_blocking=True)
            outputs = model(images)
            loss    = criterion(outputs, labels)
            val_loss += loss.item()

    val_loss /= len(val_loader)
    scheduler.step(val_loss)

    # ---------- LOG ----------
    history.append({
        'epoch': epoch + 1,
        'train_loss': round(train_loss, 4),
        'val_loss':   round(val_loss, 4),
        'lr':         optimizer.param_groups[0]['lr']
    })

    print(f"Epoch {epoch+1:02d}/{EPOCHS} | "
          f"Train Loss: {train_loss:.4f} | "
          f"Val Loss: {val_loss:.4f} | "
          f"LR: {optimizer.param_groups[0]['lr']:.6f}")

    # ---------- SAVE BEST ----------
    if val_loss < best_val_loss:
        best_val_loss    = val_loss
        patience_counter = 0
        torch.save(model.state_dict(), SAVE_PATH)
        print(f"  ✅ Val loss tốt hơn → Lưu model (val_loss={val_loss:.4f})")
    else:
        patience_counter += 1
        print(f"  ⏳ Không cải thiện ({patience_counter}/{EARLY_STOP_PATIENCE})")

    # ---------- EARLY STOPPING ----------
    if patience_counter >= EARLY_STOP_PATIENCE:
        print(f"\n🛑 Early stopping tại epoch {epoch+1}")
        break

# ====================================================
# LƯU LỊCH SỬ TRAIN
# ====================================================
log_df = pd.DataFrame(history)
log_df.to_csv("train_history.csv", index=False)

print(f"\n✅ Train xong!")
print(f"   Best val loss : {best_val_loss:.4f}")
print(f"   Model đã lưu  : {SAVE_PATH}")
print(f"   Lịch sử train : train_history.csv")
