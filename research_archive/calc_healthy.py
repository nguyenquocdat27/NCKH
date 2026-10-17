import os
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import pandas as pd
import numpy as np
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

DATA_DIR   = 'multilabel_dataset'
MODEL_PATH = 'AI/multilabel_model_gpu.pth'
N_CLASSES  = 7
THRESHOLD  = 0.5
BATCH_SIZE = 16
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class PlantDataset(Dataset):
    def __init__(self, csv_file, img_dir, transform=None):
        self.data      = pd.read_csv(csv_file)
        self.img_dir   = img_dir
        self.transform = transform
    def __len__(self): return len(self.data)
    def __getitem__(self, idx):
        img_path = os.path.join(self.img_dir, self.data.iloc[idx, 0])
        image    = Image.open(img_path).convert('RGB')
        labels   = torch.tensor(self.data.iloc[idx, 1:].values.astype('float32'))
        if self.transform: image = self.transform(image)
        return image, labels

val_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std =[0.229, 0.224, 0.225]),
])

val_dataset = PlantDataset(os.path.join(DATA_DIR, 'val.csv'), os.path.join(DATA_DIR, 'images'), val_transform)
val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

model    = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, N_CLASSES)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model    = model.to(DEVICE)
model.eval()

all_labels = []
all_preds  = []
with torch.no_grad():
    for images, labels in val_loader:
        outputs = model(images.to(DEVICE))
        probs   = torch.sigmoid(outputs).cpu().numpy()
        all_labels.append(labels.numpy())
        all_preds.append((probs >= THRESHOLD).astype(int))

all_labels = np.vstack(all_labels)
all_preds  = np.vstack(all_preds)

healthy_true = (all_labels.sum(axis=1) == 0).astype(int)
healthy_pred = (all_preds.sum(axis=1) == 0).astype(int)

print(f'Overall Subset Accuracy (Exact Match): {accuracy_score(all_labels, all_preds):.4f}')
print(f'Healthy - Precision: {precision_score(healthy_true, healthy_pred):.4f}')
print(f'Healthy - Recall: {recall_score(healthy_true, healthy_pred):.4f}')
print(f'Healthy - F1: {f1_score(healthy_true, healthy_pred):.4f}')
print(f'Healthy - Support: {healthy_true.sum()}')
