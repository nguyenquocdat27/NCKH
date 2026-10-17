"""
Tạo biểu đồ phân tích số lượng thiếu từng chất dinh dưỡng chi tiết
Đọc từ CSV kết quả đã có sẵn
"""
import os
import sys
import pandas as pd
import numpy as np
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ====================================================
# ĐỌC DỮ LIỆU
# ====================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "ket_qua_augmented", "ket_qua_augmented_full.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "ket_qua_augmented")

df = pd.read_csv(CSV_PATH)
NUTRIENTS = ["Ca", "K", "Mn", "N", "P", "S", "Zn"]

# Tách dữ liệu gốc vs augmented
df_goc = df[df["Loại"] == "Gốc"]
df_aug = df[df["Loại"] == "Augmented"]

# Đếm từng chất
def count_nutrients(dataframe):
    counts = Counter()
    for pred in dataframe["AI Dự đoán"]:
        if pred == "Healthy":
            continue
        for c in str(pred).split(","):
            c = c.strip()
            if c in NUTRIENTS:
                counts[c] += 1
    return counts

counts_goc = count_nutrients(df_goc)
counts_aug = count_nutrients(df_aug)
counts_all = count_nutrients(df)

n_goc = len(df_goc)
n_aug = len(df_aug)
n_all = len(df)

healthy_goc = len(df_goc[df_goc["AI Dự đoán"] == "Healthy"])
healthy_aug = len(df_aug[df_aug["AI Dự đoán"] == "Healthy"])

# ====================================================
# VẼ BIỂU ĐỒ
# ====================================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle("PHAN TICH SO LUONG THIEU TUNG CHAT DINH DUONG",
             fontsize=16, fontweight='bold', y=0.98)

# --- 1. Bar chart so sánh Gốc vs Augmented vs Tổng ---
ax1 = axes[0, 0]
x = np.arange(len(NUTRIENTS))
width = 0.25

vals_goc = [counts_goc.get(n, 0) for n in NUTRIENTS]
vals_aug = [counts_aug.get(n, 0) for n in NUTRIENTS]
vals_all = [counts_all.get(n, 0) for n in NUTRIENTS]

bars1 = ax1.bar(x - width, vals_goc, width, label=f'Goc ({n_goc} anh)', color='#3b82f6')
bars2 = ax1.bar(x,         vals_aug, width, label=f'Augmented ({n_aug} anh)', color='#f59e0b')
bars3 = ax1.bar(x + width, vals_all, width, label=f'Tong ({n_all} anh)', color='#10b981')

for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., h + 2,
                     str(int(h)), ha='center', va='bottom', fontsize=8, fontweight='bold')

ax1.set_xlabel('Chat dinh duong', fontsize=11)
ax1.set_ylabel('So luong anh', fontsize=11)
ax1.set_title('So luong thieu tung chat: Goc vs Augmented vs Tong', fontsize=12, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels(NUTRIENTS, fontsize=12, fontweight='bold')
ax1.legend(fontsize=9)
ax1.grid(axis='y', alpha=0.3)

# --- 2. Tỉ lệ % thiếu từng chất (trên ảnh gốc) ---
ax2 = axes[0, 1]
pct_goc = [(counts_goc.get(n, 0) / n_goc * 100) for n in NUTRIENTS]
colors = ['#ef4444' if p > 50 else '#f59e0b' if p > 10 else '#10b981' for p in pct_goc]

bars_pct = ax2.barh(NUTRIENTS[::-1], pct_goc[::-1], color=colors[::-1], edgecolor='white', height=0.6)

for bar, pct in zip(bars_pct, pct_goc[::-1]):
    w = bar.get_width()
    label = f'{pct:.1f}% ({int(w * n_goc / 100)} anh)'
    ax2.text(w + 1, bar.get_y() + bar.get_height()/2., label,
             ha='left', va='center', fontsize=10, fontweight='bold')

ax2.set_xlabel('Ti le (%)', fontsize=11)
ax2.set_title(f'Ti le thieu tung chat (Anh goc - {n_goc} anh)', fontsize=12, fontweight='bold')
ax2.set_xlim(0, 110)
ax2.grid(axis='x', alpha=0.3)

# --- 3. Pie chart phân bố các chất thiếu (ảnh gốc) ---
ax3 = axes[1, 0]
# Gom lại: chất nào > 0 thì hiện, thêm Healthy
pie_data = {}
for n in NUTRIENTS:
    c = counts_goc.get(n, 0)
    if c > 0:
        pie_data[f"Thieu {n}"] = c
pie_data["Healthy"] = healthy_goc

labels_pie = list(pie_data.keys())
sizes_pie = list(pie_data.values())
colors_pie = ['#ef4444', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#10b981'][:len(labels_pie)]
# Healthy luôn màu xanh lá
colors_pie[-1] = '#10b981'

explode = [0.05] * len(labels_pie)
wedges, texts, autotexts = ax3.pie(
    sizes_pie, explode=explode, labels=labels_pie, colors=colors_pie,
    autopct=lambda p: f'{p:.1f}%\n({int(round(p * sum(sizes_pie) / 100))})',
    shadow=True, startangle=90, textprops={'fontsize': 10}
)
for at in autotexts:
    at.set_fontweight('bold')
    at.set_fontsize(9)
ax3.set_title('Phan bo ket qua du doan (Anh goc)', fontsize=12, fontweight='bold')

# --- 4. Bảng tóm tắt chi tiết ---
ax4 = axes[1, 1]
ax4.axis('off')

table_data = [
    ["Chat", "Goc", "Augmented", "Tong", "% (Goc)"]
]
for n in NUTRIENTS:
    g = counts_goc.get(n, 0)
    a = counts_aug.get(n, 0)
    t = counts_all.get(n, 0)
    pct = g / n_goc * 100
    table_data.append([n, str(g), str(a), str(t), f"{pct:.1f}%"])

# Thêm dòng Healthy
table_data.append(["Healthy", str(healthy_goc), str(healthy_aug),
                    str(healthy_goc + healthy_aug),
                    f"{healthy_goc/n_goc*100:.1f}%"])
# Thêm dòng tổng
table_data.append(["TONG", str(n_goc), str(n_aug), str(n_all), "100%"])

table = ax4.table(
    cellText=table_data,
    cellLoc='center',
    loc='center',
    colWidths=[0.18, 0.18, 0.22, 0.18, 0.18]
)
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 1.6)

# Header
for j in range(5):
    table[0, j].set_facecolor('#3b82f6')
    table[0, j].set_text_props(color='white', fontweight='bold')

# Highlight dòng có giá trị cao
for i in range(1, len(table_data)):
    for j in range(5):
        if table_data[i][0] == "TONG":
            table[i, j].set_facecolor('#e2e8f0')
            table[i, j].set_text_props(fontweight='bold')
        elif table_data[i][0] == "Healthy":
            table[i, j].set_facecolor('#d1fae5')
        elif int(table_data[i][1]) > 0:
            table[i, j].set_facecolor('#fef3c7')
        else:
            table[i, j].set_facecolor('#f8fafc')

ax4.set_title('BANG THONG KE CHI TIET', fontsize=12, fontweight='bold', pad=20)

plt.tight_layout(rect=[0, 0, 1, 0.95])

chart_path = os.path.join(OUTPUT_DIR, "phan_tich_thieu_chat.png")
plt.savefig(chart_path, dpi=150, bbox_inches='tight', facecolor='white')
plt.close()

print(f"Da luu bieu do: {chart_path}")
