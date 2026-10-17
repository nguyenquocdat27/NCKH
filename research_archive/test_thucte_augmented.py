"""
Script: test_thucte_augmented.py
Mục đích:
  1. Đọc 150 ảnh gốc từ thucdiatest/
  2. Augment mỗi ảnh bằng 7 kỹ thuật (giống lúc huấn luyện):
     - Lật ngang (Horizontal Flip)
     - Lật dọc (Vertical Flip)
     - Xoay 20° (Rotation)
     - Tăng sáng (Brightness Up)
     - Giảm sáng (Brightness Down)
     - Đổi bão hoà + hue (Color Jitter)
     - Random Crop + Resize
  3. Chạy model AI predict trên tất cả ảnh (gốc + augmented)
  4. Tạo biểu đồ tổng hợp: số lượng thiếu chất, thời gian tính toán, tỉ lệ nhất quán
"""

import os
import sys
import time
import json
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
import pandas as pd
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
from collections import Counter, defaultdict

# ====================================================
# CONFIG
# ====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)  # d:\NCKH\MAIN

IMAGE_DIR = os.path.join(PROJECT_DIR, "thucdiatest")
AUGMENTED_DIR = os.path.join(PROJECT_DIR, "thucdiatest_augmented")
MODEL_PATH = os.path.join(BASE_DIR, "AI", "multilabel_model_gpu.pth")
OUTPUT_DIR = os.path.join(BASE_DIR, "ket_qua_augmented")

NUTRIENTS = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]
N_CLASSES = 7
THRESHOLD = 0.5

# ====================================================
# TẠO THƯ MỤC OUTPUT
# ====================================================
os.makedirs(AUGMENTED_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ====================================================
# 1. AUGMENTATION - Giống kỹ thuật trong train_multilabel.py
# ====================================================
def augment_images(image_dir, output_dir):
    """
    Áp dụng 7 kỹ thuật augmentation cho mỗi ảnh gốc.
    Giống transforms trong train_multilabel.py:
      - RandomHorizontalFlip(p=0.5)
      - RandomVerticalFlip(p=0.2)
      - RandomRotation(degrees=20)
      - ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1)
      - RandomCrop(224) từ 256
    """
    print("=" * 60)
    print("  BƯỚC 1: AUGMENT ẢNH")
    print("=" * 60)

    image_files = sorted([
        f for f in os.listdir(image_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])

    print(f"📷 Tìm thấy {len(image_files)} ảnh gốc trong {image_dir}")

    augment_count = 0
    augment_map = {}  # gốc -> list augmented

    for idx, img_name in enumerate(image_files):
        img_path = os.path.join(image_dir, img_name)
        try:
            img = Image.open(img_path).convert("RGB")
        except Exception as e:
            print(f"  ⚠️ Không đọc được {img_name}: {e}")
            continue

        base_name = os.path.splitext(img_name)[0]
        ext = os.path.splitext(img_name)[1]
        augmented_names = []

        # --- Kỹ thuật 1: Lật ngang (Horizontal Flip) ---
        aug_name = f"{base_name}_hflip{ext}"
        img.transpose(Image.FLIP_LEFT_RIGHT).save(
            os.path.join(output_dir, aug_name), quality=95
        )
        augmented_names.append(aug_name)

        # --- Kỹ thuật 2: Lật dọc (Vertical Flip) ---
        aug_name = f"{base_name}_vflip{ext}"
        img.transpose(Image.FLIP_TOP_BOTTOM).save(
            os.path.join(output_dir, aug_name), quality=95
        )
        augmented_names.append(aug_name)

        # --- Kỹ thuật 3: Xoay 20° ---
        aug_name = f"{base_name}_rot20{ext}"
        img.rotate(20, resample=Image.BICUBIC, expand=False, fillcolor=(0, 0, 0)).save(
            os.path.join(output_dir, aug_name), quality=95
        )
        augmented_names.append(aug_name)

        # --- Kỹ thuật 4: Tăng sáng (brightness=1.3) ---
        aug_name = f"{base_name}_bright_up{ext}"
        enhancer = ImageEnhance.Brightness(img)
        enhancer.enhance(1.3).save(
            os.path.join(output_dir, aug_name), quality=95
        )
        augmented_names.append(aug_name)

        # --- Kỹ thuật 5: Giảm sáng (brightness=0.7) ---
        aug_name = f"{base_name}_bright_down{ext}"
        enhancer = ImageEnhance.Brightness(img)
        enhancer.enhance(0.7).save(
            os.path.join(output_dir, aug_name), quality=95
        )
        augmented_names.append(aug_name)

        # --- Kỹ thuật 6: Thay đổi bão hòa + hue (ColorJitter) ---
        aug_name = f"{base_name}_color_jitter{ext}"
        img_jitter = img.copy()
        # Saturation
        img_jitter = ImageEnhance.Color(img_jitter).enhance(1.3)
        # Contrast
        img_jitter = ImageEnhance.Contrast(img_jitter).enhance(1.3)
        # Slight hue shift bằng cách chuyển HSV
        img_hsv = img_jitter.convert("HSV")
        h, s, v = img_hsv.split()
        h_np = np.array(h, dtype=np.int16)
        h_np = ((h_np + 13) % 256).astype(np.uint8)  # shift hue ~10%
        h = Image.fromarray(h_np, mode='L')
        img_jitter = Image.merge("HSV", (h, s, v)).convert("RGB")
        img_jitter.save(os.path.join(output_dir, aug_name), quality=95)
        augmented_names.append(aug_name)

        # --- Kỹ thuật 7: Random Crop + Resize ---
        aug_name = f"{base_name}_crop_resize{ext}"
        w, h_size = img.size
        # Resize to 256 first, then crop 224
        img_resized = img.resize((256, 256), Image.BICUBIC)
        # Center-offset crop (simulate random crop)
        left = 16  # (256-224)/2
        top = 16
        img_cropped = img_resized.crop((left, top, left + 224, top + 224))
        img_cropped = img_cropped.resize((w, h_size), Image.BICUBIC)
        img_cropped.save(os.path.join(output_dir, aug_name), quality=95)
        augmented_names.append(aug_name)

        augment_map[img_name] = augmented_names
        augment_count += len(augmented_names)

        if (idx + 1) % 30 == 0:
            print(f"  ✅ Đã augment {idx + 1}/{len(image_files)} ảnh...")

    print(f"\n📊 Tổng kết augmentation:")
    print(f"   Ảnh gốc: {len(image_files)}")
    print(f"   Ảnh augmented: {augment_count}")
    print(f"   Tổng cộng sẽ test: {len(image_files)} (gốc) + {augment_count} (augmented) = {len(image_files) + augment_count} ảnh")
    print(f"   Lưu tại: {output_dir}")

    return image_files, augment_map


# ====================================================
# 2. LOAD MODEL & PREDICT
# ====================================================
def load_model(model_path, device):
    """Load ResNet18 model giống cấu trúc trong train_multilabel.py"""
    model = models.resnet18(weights=None)
    model.fc = nn.Linear(model.fc.in_features, N_CLASSES)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device).eval()
    return model


def predict_single(model, image_path, transform, device):
    """Dự đoán 1 ảnh, trả về danh sách chất thiếu và thời gian tính toán"""
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(device)

    start_time = time.time()
    with torch.no_grad():
        probs = torch.sigmoid(model(tensor)).cpu().numpy()[0]
    elapsed = time.time() - start_time

    preds = [NUTRIENTS[i] for i in range(N_CLASSES) if probs[i] >= THRESHOLD]
    pred_str = ", ".join(preds) if preds else "Healthy"

    return pred_str, preds, probs, elapsed


def run_predictions(model, image_files, augment_map, image_dir, augmented_dir, transform, device):
    """Chạy prediction trên toàn bộ ảnh gốc + augmented"""
    print("\n" + "=" * 60)
    print("  BƯỚC 2: CHẠY AI PREDICT")
    print("=" * 60)

    all_results = []
    original_results = {}  # lưu kết quả gốc để so sánh tỉ lệ nhất quán
    total_time = 0
    total_images = 0

    # --- Predict ảnh gốc ---
    print(f"\n🔍 Predicting {len(image_files)} ảnh gốc...")
    for img_name in image_files:
        img_path = os.path.join(image_dir, img_name)
        if not os.path.exists(img_path):
            continue

        pred_str, preds, probs, elapsed = predict_single(
            model, img_path, transform, device
        )
        total_time += elapsed
        total_images += 1

        original_results[img_name] = set(preds)

        prob_detail = {NUTRIENTS[i]: round(float(probs[i]), 4) for i in range(N_CLASSES)}
        all_results.append({
            "Ảnh gốc": img_name,
            "Loại": "Gốc",
            "Augmentation": "Original",
            "AI Dự đoán": pred_str,
            "Thời gian (ms)": round(elapsed * 1000, 2),
            "Xác suất chi tiết": json.dumps(prob_detail, ensure_ascii=False),
        })

    # --- Predict ảnh augmented ---
    aug_total = sum(len(v) for v in augment_map.values())
    print(f"🔍 Predicting {aug_total} ảnh augmented...")

    consistency_data = defaultdict(list)  # gốc -> [set(preds) for each augmented]
    processed = 0

    for orig_name, aug_names in augment_map.items():
        for aug_name in aug_names:
            aug_path = os.path.join(augmented_dir, aug_name)
            if not os.path.exists(aug_path):
                continue

            pred_str, preds, probs, elapsed = predict_single(
                model, aug_path, transform, device
            )
            total_time += elapsed
            total_images += 1

            # Xác định loại augmentation
            aug_type = "Unknown"
            if "_hflip" in aug_name:
                aug_type = "Lật ngang"
            elif "_vflip" in aug_name:
                aug_type = "Lật dọc"
            elif "_rot20" in aug_name:
                aug_type = "Xoay 20°"
            elif "_bright_up" in aug_name:
                aug_type = "Tăng sáng"
            elif "_bright_down" in aug_name:
                aug_type = "Giảm sáng"
            elif "_color_jitter" in aug_name:
                aug_type = "Đổi màu sắc"
            elif "_crop_resize" in aug_name:
                aug_type = "Crop & Resize"

            consistency_data[orig_name].append(set(preds))

            prob_detail = {NUTRIENTS[i]: round(float(probs[i]), 4) for i in range(N_CLASSES)}
            all_results.append({
                "Ảnh gốc": orig_name,
                "Loại": "Augmented",
                "Augmentation": aug_type,
                "AI Dự đoán": pred_str,
                "Thời gian (ms)": round(elapsed * 1000, 2),
                "Xác suất chi tiết": json.dumps(prob_detail, ensure_ascii=False),
            })

            processed += 1
            if processed % 100 == 0:
                print(f"  ✅ Đã predict {processed}/{aug_total} ảnh augmented...")

    avg_time = (total_time / total_images * 1000) if total_images > 0 else 0

    print(f"\n📊 Tổng kết prediction:")
    print(f"   Tổng ảnh đã predict: {total_images}")
    print(f"   Tổng thời gian: {total_time:.2f}s")
    print(f"   Thời gian trung bình: {avg_time:.2f}ms/ảnh")

    return all_results, original_results, consistency_data, avg_time, total_time, total_images


# ====================================================
# 3. PHÂN TÍCH & TẠO BIỂU ĐỒ
# ====================================================
def analyze_and_chart(all_results, original_results, consistency_data,
                      avg_time, total_time, total_images, output_dir):
    """Phân tích kết quả và tạo biểu đồ tổng hợp"""
    print("\n" + "=" * 60)
    print("  BƯỚC 3: PHÂN TÍCH & TẠO BIỂU ĐỒ")
    print("=" * 60)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import rcParams

    # Font hỗ trợ Unicode
    rcParams['font.family'] = 'DejaVu Sans'

    # --- Lưu CSV kết quả chi tiết ---
    df = pd.DataFrame(all_results)
    csv_path = os.path.join(output_dir, "ket_qua_augmented_full.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"💾 CSV chi tiết: {csv_path}")

    # =============================================
    # PHÂN TÍCH 1: Số lượng thiếu từng chất
    # =============================================
    nutrient_count_original = Counter()
    nutrient_count_all = Counter()
    healthy_original = 0
    healthy_all = 0

    for r in all_results:
        pred = r["AI Dự đoán"]
        if pred == "Healthy":
            healthy_all += 1
            if r["Loại"] == "Gốc":
                healthy_original += 1
        else:
            chats = [c.strip() for c in pred.split(",")]
            for c in chats:
                nutrient_count_all[c] += 1
                if r["Loại"] == "Gốc":
                    nutrient_count_original[c] += 1

    # =============================================
    # PHÂN TÍCH 2: Tỉ lệ nhất quán (consistency)
    # Ảnh augmented cho kết quả giống ảnh gốc → model ổn định
    # =============================================
    consistency_scores = []
    per_aug_consistency = defaultdict(list)

    aug_type_map = {
        "_hflip": "Lat ngang",
        "_vflip": "Lat doc",
        "_rot20": "Xoay 20°",
        "_bright_up": "Tang sang",
        "_bright_down": "Giam sang",
        "_color_jitter": "Doi mau",
        "_crop_resize": "Crop"
    }

    for orig_name, aug_pred_sets in consistency_data.items():
        orig_preds = original_results.get(orig_name, set())
        for i, aug_preds in enumerate(aug_pred_sets):
            # Jaccard similarity
            if len(orig_preds) == 0 and len(aug_preds) == 0:
                score = 1.0  # both healthy
            elif len(orig_preds | aug_preds) == 0:
                score = 1.0
            else:
                intersection = len(orig_preds & aug_preds)
                union = len(orig_preds | aug_preds)
                score = intersection / union if union > 0 else 1.0

            consistency_scores.append(score)

            # Xác định aug type theo thứ tự
            aug_types_order = ["_hflip", "_vflip", "_rot20", "_bright_up",
                               "_bright_down", "_color_jitter", "_crop_resize"]
            if i < len(aug_types_order):
                aug_key = aug_types_order[i]
                per_aug_consistency[aug_type_map[aug_key]].append(score)

    overall_consistency = np.mean(consistency_scores) if consistency_scores else 0
    exact_match_count = sum(1 for s in consistency_scores if s == 1.0)
    exact_match_rate = exact_match_count / len(consistency_scores) * 100 if consistency_scores else 0

    print(f"\n📊 Phân tích nhất quán (Consistency):")
    print(f"   Tỉ lệ nhất quán trung bình (Jaccard): {overall_consistency:.4f} ({overall_consistency*100:.1f}%)")
    print(f"   Exact match rate: {exact_match_rate:.1f}%")
    print(f"   (Ảnh augmented cho kết quả giống hệt gốc: {exact_match_count}/{len(consistency_scores)})")

    # =============================================
    # VẼ BIỂU ĐỒ TỔNG HỢP
    # =============================================
    fig = plt.figure(figsize=(20, 14))
    fig.suptitle("DANH GIA MODEL AI TREN ANH THUC TE + AUGMENTATION",
                 fontsize=16, fontweight='bold', y=0.98)

    # --- Biểu đồ 1: Số lượng thiếu từng chất (Gốc vs Augmented) ---
    ax1 = fig.add_subplot(2, 3, 1)
    x = np.arange(len(NUTRIENTS))
    width = 0.35
    counts_orig = [nutrient_count_original.get(n, 0) for n in NUTRIENTS]
    counts_all = [nutrient_count_all.get(n, 0) for n in NUTRIENTS]

    bars1 = ax1.bar(x - width/2, counts_orig, width, label='Goc (150 anh)',
                     color='#3b82f6', edgecolor='white')
    bars2 = ax1.bar(x + width/2, counts_all, width, label='Tat ca (1200 anh)',
                     color='#f59e0b', edgecolor='white', alpha=0.8)

    ax1.set_xlabel('Chat dinh duong', fontsize=10)
    ax1.set_ylabel('So luong anh thieu chat', fontsize=10)
    ax1.set_title('So luong thieu tung chat dinh duong', fontsize=12, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(NUTRIENTS, fontsize=11)
    ax1.legend(fontsize=9)
    ax1.grid(axis='y', alpha=0.3)

    # Ghi số lên cột
    for bar in bars1:
        h = bar.get_height()
        if h > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., h + 0.5,
                     str(int(h)), ha='center', va='bottom', fontsize=8, fontweight='bold')
    for bar in bars2:
        h = bar.get_height()
        if h > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., h + 0.5,
                     str(int(h)), ha='center', va='bottom', fontsize=8, fontweight='bold')

    # --- Biểu đồ 2: Phân bố kết quả dự đoán (Pie chart) ---
    ax2 = fig.add_subplot(2, 3, 2)
    pred_categories = Counter()
    for r in all_results:
        if r["Loại"] == "Gốc":
            pred = r["AI Dự đoán"]
            if pred == "Healthy":
                pred_categories["Healthy"] += 1
            else:
                num_deficient = len(pred.split(","))
                if num_deficient == 1:
                    pred_categories["Thieu 1 chat"] += 1
                elif num_deficient == 2:
                    pred_categories["Thieu 2 chat"] += 1
                else:
                    pred_categories["Thieu 3+ chat"] += 1

    if pred_categories:
        labels_pie = list(pred_categories.keys())
        sizes = list(pred_categories.values())
        colors_pie = ['#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][:len(labels_pie)]
        explode = [0.05] * len(labels_pie)

        wedges, texts, autotexts = ax2.pie(
            sizes, explode=explode, labels=labels_pie, colors=colors_pie,
            autopct='%1.1f%%', shadow=True, startangle=90,
            textprops={'fontsize': 9}
        )
        for autotext in autotexts:
            autotext.set_fontweight('bold')
    ax2.set_title('Phan bo du doan (Anh goc)', fontsize=12, fontweight='bold')

    # --- Biểu đồ 3: Thời gian tính toán ---
    ax3 = fig.add_subplot(2, 3, 3)
    times = [r["Thời gian (ms)"] for r in all_results]
    ax3.hist(times, bins=30, color='#6366f1', edgecolor='white', alpha=0.8)
    ax3.axvline(avg_time, color='red', linestyle='--', linewidth=2,
                label=f'TB: {avg_time:.2f}ms')
    ax3.set_xlabel('Thoi gian (ms)', fontsize=10)
    ax3.set_ylabel('So luong anh', fontsize=10)
    ax3.set_title('Phan bo thoi gian tinh toan', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=10)
    ax3.grid(axis='y', alpha=0.3)

    # Thêm text box thống kê
    stats_text = (f"Tong: {total_images} anh\n"
                  f"TB: {avg_time:.2f}ms\n"
                  f"Min: {min(times):.2f}ms\n"
                  f"Max: {max(times):.2f}ms\n"
                  f"Tong TG: {total_time:.1f}s")
    ax3.text(0.95, 0.95, stats_text, transform=ax3.transAxes,
             fontsize=8, verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    # --- Biểu đồ 4: Tỉ lệ nhất quán theo loại augmentation ---
    ax4 = fig.add_subplot(2, 3, 4)
    if per_aug_consistency:
        aug_names = list(per_aug_consistency.keys())
        aug_means = [np.mean(v) * 100 for v in per_aug_consistency.values()]
        colors_bar = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444',
                      '#8b5cf6', '#ec4899', '#06b6d4'][:len(aug_names)]

        bars = ax4.bar(range(len(aug_names)), aug_means, color=colors_bar,
                        edgecolor='white')
        ax4.set_xticks(range(len(aug_names)))
        ax4.set_xticklabels(aug_names, fontsize=8, rotation=30, ha='right')
        ax4.set_ylabel('Ti le nhat quan (%)', fontsize=10)
        ax4.set_title('Do on dinh theo loai augmentation', fontsize=12, fontweight='bold')
        ax4.set_ylim(0, 110)
        ax4.axhline(y=overall_consistency*100, color='red', linestyle='--',
                     alpha=0.6, label=f'TB: {overall_consistency*100:.1f}%')
        ax4.legend(fontsize=9)
        ax4.grid(axis='y', alpha=0.3)

        for bar, val in zip(bars, aug_means):
            ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 1,
                     f'{val:.1f}%', ha='center', va='bottom', fontsize=8, fontweight='bold')

    # --- Biểu đồ 5: So sánh số lượng Healthy vs Thieu chat ---
    ax5 = fig.add_subplot(2, 3, 5)

    # Tính riêng cho gốc
    orig_healthy = sum(1 for r in all_results if r["Loại"] == "Gốc" and r["AI Dự đoán"] == "Healthy")
    orig_deficient = sum(1 for r in all_results if r["Loại"] == "Gốc" and r["AI Dự đoán"] != "Healthy")
    aug_healthy = sum(1 for r in all_results if r["Loại"] == "Augmented" and r["AI Dự đoán"] == "Healthy")
    aug_deficient = sum(1 for r in all_results if r["Loại"] == "Augmented" and r["AI Dự đoán"] != "Healthy")

    categories = ['Goc - Healthy', 'Goc - Thieu', 'Aug - Healthy', 'Aug - Thieu']
    values = [orig_healthy, orig_deficient, aug_healthy, aug_deficient]
    colors_comp = ['#10b981', '#ef4444', '#6ee7b7', '#fca5a5']

    bars_comp = ax5.bar(categories, values, color=colors_comp, edgecolor='white')
    ax5.set_ylabel('So luong anh', fontsize=10)
    ax5.set_title('Healthy vs Thieu chat (Goc & Aug)', fontsize=12, fontweight='bold')
    ax5.grid(axis='y', alpha=0.3)
    plt.setp(ax5.xaxis.get_majorticklabels(), fontsize=8, rotation=20, ha='right')

    for bar, val in zip(bars_comp, values):
        ax5.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                 str(val), ha='center', va='bottom', fontsize=9, fontweight='bold')

    # --- Biểu đồ 6: Bảng tóm tắt ---
    ax6 = fig.add_subplot(2, 3, 6)
    ax6.axis('off')

    summary_data = [
        ["Chi tieu", "Gia tri"],
        ["Anh goc", f"{len(original_results)}"],
        ["Anh augmented", f"{total_images - len(original_results)}"],
        ["Tong anh da test", f"{total_images}"],
        ["", ""],
        ["TG trung binh/anh", f"{avg_time:.2f} ms"],
        ["Tong thoi gian", f"{total_time:.2f} s"],
        ["", ""],
        ["Ti le nhat quan (Jaccard)", f"{overall_consistency*100:.1f}%"],
        ["Exact Match Rate", f"{exact_match_rate:.1f}%"],
        ["", ""],
        ["Healthy (goc)", f"{orig_healthy}/{len(original_results)} ({orig_healthy/max(len(original_results),1)*100:.0f}%)"],
        ["Thieu chat (goc)", f"{orig_deficient}/{len(original_results)} ({orig_deficient/max(len(original_results),1)*100:.0f}%)"],
    ]

    table = ax6.table(
        cellText=summary_data,
        cellLoc='center',
        loc='center',
        colWidths=[0.55, 0.45]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    # Header styling
    for j in range(2):
        table[0, j].set_facecolor('#3b82f6')
        table[0, j].set_text_props(color='white', fontweight='bold')

    # Alternate row colors
    for i in range(1, len(summary_data)):
        for j in range(2):
            if summary_data[i][0] == "":
                table[i, j].set_facecolor('#f8fafc')
                table[i, j].set_edgecolor('#f8fafc')
            elif i % 2 == 0:
                table[i, j].set_facecolor('#f0f9ff')

    ax6.set_title('BANG TOM TAT', fontsize=12, fontweight='bold', pad=20)

    plt.tight_layout(rect=[0, 0, 1, 0.95])

    chart_path = os.path.join(output_dir, "bieu_do_tong_hop_augmented.png")
    plt.savefig(chart_path, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print(f"\n📊 Biểu đồ tổng hợp: {chart_path}")

    # =============================================
    # BẢNG TỔNG HỢP CONSOLE
    # =============================================
    print("\n" + "=" * 60)
    print("  BẢNG TÓM TẮT KẾT QUẢ")
    print("=" * 60)
    print(f"  📷 Ảnh gốc             : {len(original_results)}")
    print(f"  🔄 Ảnh augmented       : {total_images - len(original_results)}")
    print(f"  📦 Tổng ảnh đã test    : {total_images}")
    print(f"  ⏱️  TG trung bình/ảnh  : {avg_time:.2f} ms")
    print(f"  ⏱️  Tổng thời gian     : {total_time:.2f} s")
    print(f"  🎯 Tỉ lệ nhất quán    : {overall_consistency*100:.1f}%")
    print(f"  ✅ Exact Match         : {exact_match_rate:.1f}%")
    print(f"  🌿 Healthy (gốc)      : {orig_healthy}/{len(original_results)}")
    print(f"  ⚠️  Thiếu chất (gốc)  : {orig_deficient}/{len(original_results)}")
    print("-" * 60)
    print(f"\n  Số lượng thiếu từng chất (ảnh gốc):")
    for n in NUTRIENTS:
        c = nutrient_count_original.get(n, 0)
        bar_visual = "█" * max(c // 2, 0) + "▌" * (c % 2)
        print(f"    {n:4s}: {c:4d} ảnh  {bar_visual}")
    print("-" * 60)

    if per_aug_consistency:
        print(f"\n  Độ nhất quán theo loại augmentation:")
        for aug_name, scores in per_aug_consistency.items():
            mean_s = np.mean(scores) * 100
            print(f"    {aug_name:15s}: {mean_s:.1f}%")
    print("=" * 60)

    return chart_path, csv_path


# ====================================================
# MAIN
# ====================================================
def main():
    print("🚀 BẮT ĐẦU TEST ẢNH THỰC TẾ VỚI AUGMENTATION")
    print("=" * 60)

    # Kiểm tra model
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Không tìm thấy model: {MODEL_PATH}")
        return

    # Kiểm tra thư mục ảnh
    if not os.path.exists(IMAGE_DIR):
        print(f"❌ Không tìm thấy thư mục ảnh: {IMAGE_DIR}")
        return

    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🖥️ Device: {device}")
    if torch.cuda.is_available():
        print(f"   GPU: {torch.cuda.get_device_name(0)}")

    # Transform giống val_transform trong train
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Bước 1: Augment
    image_files, augment_map = augment_images(IMAGE_DIR, AUGMENTED_DIR)

    # Bước 2: Load model & predict
    print(f"\n⏳ Đang load model: {MODEL_PATH}")
    model = load_model(MODEL_PATH, device)
    print("✅ Model loaded!")

    all_results, original_results, consistency_data, avg_time, total_time, total_images = \
        run_predictions(model, image_files, augment_map, IMAGE_DIR, AUGMENTED_DIR,
                        transform, device)

    # Bước 3: Phân tích & biểu đồ
    chart_path, csv_path = analyze_and_chart(
        all_results, original_results, consistency_data,
        avg_time, total_time, total_images, OUTPUT_DIR
    )

    print(f"\n🎉 HOÀN TẤT!")
    print(f"   📊 Biểu đồ: {chart_path}")
    print(f"   📄 CSV chi tiết: {csv_path}")
    print(f"   🖼️ Ảnh augmented: {AUGMENTED_DIR}")


if __name__ == "__main__":
    main()
