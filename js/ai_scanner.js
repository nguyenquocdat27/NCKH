// ============================================================
// AI SCANNER (js/ai_scanner.js)
// ============================================================

async function processAndRenderAI(imageData, loadingEl, contentEl, resultText) {
  loadingEl.classList.remove('hidden');
  contentEl.classList.add('hidden');

  try {
    let base64Data = imageData;
    if (!base64Data.startsWith('data:')) {
      const blob = await fetch(base64Data).then(r => r.blob());
      base64Data = await new Promise(res => {
        const reader = new FileReader();
        reader.onloadend = () => res(reader.result);
        reader.readAsDataURL(blob);
      });
    }

    const response = await fetch(`${AI_URL}/api/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image: base64Data })
    });

    if (!response.ok) throw new Error(`Server lỗi: ${response.status}`);
    const result = await response.json();

    loadingEl.classList.add('hidden');
    contentEl.classList.remove('hidden');

    const barsHtml = Object.entries(result.scores)
      .sort((a, b) => b[1] - a[1])
      .map(([nutrient, prob]) => {
        const pct    = (prob * 100).toFixed(1);
        const pctNum = parseFloat(pct);
        const color  = NUTRIENT_COLORS[nutrient] || '#94a3b8';
        let barColor, icon, labelClass, badge;
        if (pctNum >= 80) {
          barColor = color; icon = '⚠️'; labelClass = 'font-bold';
          badge = `<span class="ml-1 text-[10px] px-1 rounded" style="background:${color}22;color:${color}">Nặng</span>`;
        } else if (pctNum >= 65) {
          barColor = color; icon = '⚠️'; labelClass = 'font-bold';
          badge = `<span class="ml-1 text-[10px] px-1 rounded" style="background:${color}22;color:${color}">T.Bình</span>`;
        } else if (pctNum >= 50) {
          barColor = color; icon = '⚠️'; labelClass = 'font-bold';
          badge = `<span class="ml-1 text-[10px] px-1 rounded" style="background:${color}22;color:${color}">Nhẹ</span>`;
        } else if (pctNum >= 20) {
          barColor = '#f59e0b'; icon = '🔶'; labelClass = 'font-semibold text-amber-600';
          badge = `<span class="ml-1 text-[10px] px-1 rounded bg-amber-50 text-amber-600">Cảnh báo</span>`;
        } else {
          barColor = '#cbd5e1'; icon = '✓'; labelClass = 'text-slate-400'; badge = '';
        }
        return `
          <div class="flex items-center gap-2 text-xs py-0.5">
            <span class="w-6 text-center">${icon}</span>
            <span class="w-7 ${labelClass}">${nutrient}</span>
            <div class="flex-1 bg-slate-100 rounded-full h-2.5">
              <div class="h-2.5 rounded-full transition-all" style="width:${Math.min(pctNum,100)}%;background:${barColor}"></div>
            </div>
            <span class="w-12 text-right font-mono ${pctNum>=50?'font-bold':'text-slate-500'}" style="${pctNum>=50?`color:${color}`:''}">
              ${pct}%
            </span>
            ${badge}
          </div>`;
      }).join('');

    const heatmapHtml = (result.deficient_detail || [])
      .filter(d => d.heatmap)
      .map(d => `
        <div class="rounded-xl overflow-hidden border-2 mb-3" style="border-color:${d.severity_color}">
          <div class="flex items-center justify-between px-3 py-2" style="background:${d.severity_color}18">
            <span class="font-bold text-sm" style="color:${d.severity_color}">
              ${d.severity_icon} ${d.name}
            </span>
            <span class="text-xs font-semibold px-2 py-0.5 rounded-full text-white" style="background:${d.severity_color}">
              ${d.severity} · ${(d.probability*100).toFixed(1)}%
            </span>
          </div>
          <div class="relative">
            <img src="${d.heatmap}" class="w-full rounded-b-xl" alt="Heatmap ${d.nutrient}"/>
            <div class="absolute bottom-2 left-2 right-2 bg-black/60 rounded-lg px-2 py-1.5">
              <p class="text-white text-xs leading-relaxed">${d.recommendation}</p>
            </div>
          </div>
        </div>`)
      .join('');

    const headerHtml = result.healthy
      ? `<div class="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-xl mb-3">
           <span class="text-2xl">🌿</span>
           <div><p class="font-bold text-green-700">Cây khỏe mạnh</p>
           <p class="text-xs text-green-600">Không phát hiện thiếu chất</p></div>
         </div>`
      : `<div class="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-xl mb-3">
           <span class="text-2xl">🔍</span>
           <div>
             <p class="font-bold text-red-700">Phát hiện thiếu ${result.deficient_nutrients.length} chất</p>
             <p class="text-xs text-red-600">${result.deficient_names.join(' · ')}</p>
           </div>
         </div>`;

    const demoNote = result.demo_mode
      ? `<div class="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded-lg text-xs text-yellow-700">
           ⚠️ DEMO mode — đặt file <code class="font-mono bg-white px-1 rounded">multilabel_model_gpu.pth</code> vào thư mục rồi restart.
         </div>`
      : '';

    const legendHtml = !result.healthy && heatmapHtml ? `
      <div class="flex items-center gap-3 text-xs text-slate-500 mb-3 px-1">
        <span class="font-medium">Heatmap:</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-green-500 inline-block"></span>Bình thường</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-yellow-500 inline-block"></span>Chú ý</span>
        <span class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-red-500 inline-block"></span>Bất thường</span>
      </div>` : '';

    resultText.innerHTML = `
      ${headerHtml}
      ${legendHtml}
      ${heatmapHtml}
      <div class="mb-3">
        <p class="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">Mức độ từng chất (ngưỡng ${Math.round(result.threshold*100)}%)</p>
        <div class="space-y-1.5">${barsHtml}</div>
      </div>
      ${demoNote}
    `;

    if (window.lucide) window.lucide.createIcons();
    const msg = result.healthy ? '✅ Cây khỏe mạnh!' : `⚠️ Thiếu: ${result.deficient_nutrients.join(', ')}`;
    if (window.showToast) window.showToast(msg);

  } catch (err) {
    loadingEl.classList.add('hidden');
    contentEl.classList.remove('hidden');
    resultText.innerHTML = `
      <div class="p-3 bg-orange-50 border border-orange-200 rounded-xl text-sm text-orange-800">
        <strong>⚠️ Không kết nối được server</strong><br>
        ${err.message}<br><br>
        <strong>Cách khắc phục:</strong><br>
        1. Mở terminal, chạy: <code class="bg-white px-1 rounded font-mono">python server.py</code><br>
        2. Server phải chạy tại <code class="bg-white px-1 rounded font-mono">localhost:5000</code><br>
        3. Thử quét lại
      </div>
    `;
    if (window.showToast) window.showToast('Không kết nối được server AI');
  }
}

async function scanAI() {
  const preview = document.getElementById('preview-image');
  if (!preview || !preview.src || preview.src.includes('placeholder')) {
    if (window.showToast) window.showToast('Vui lòng chọn hoặc chụp ảnh trước!');
    return;
  }

  const resultBox = document.getElementById('ai-result-box');
  const loadingEl = document.getElementById('ai-loading');
  const contentEl = document.getElementById('ai-result-content');
  const resultText = document.getElementById('ai-result-text');

  if (!resultBox) return;
  resultBox.classList.remove('hidden');
  
  await processAndRenderAI(preview.src, loadingEl, contentEl, resultText);
}

async function scanImage() {
  if (!currentImage) { 
    if (window.showToast) window.showToast('Vui lòng chọn ảnh trước'); 
    return; 
  }
  if (window.showToast) window.showToast('Đang quét ảnh bằng AI...');
  
  const resultBox = document.getElementById('analysis-results');
  const loadingEl = document.getElementById('pro-ai-loading');
  const contentEl = document.getElementById('pro-ai-result-content');
  const resultText = document.getElementById('pro-ai-result-text');

  if (!resultBox) return;
  resultBox.classList.remove('hidden');
  
  await processAndRenderAI(currentImage, loadingEl, contentEl, resultText);
}
