// ============================================================
// CAMERA HANDLING (js/camera.js)
// ============================================================

// ============================================================
// NEW USB CAMERA HANDLING & AI GALLERY (js/camera.js)
// ============================================================

let cameraSettingsInterval = null;
let cameraHistoryData = [];
let latestAnalysisRecord = null;
let isPollingCapture = false;

// Khởi tạo trang Camera
window.initCameraPage = function() {
  populateCameraFarms();
  
  const selector = document.getElementById('camera-farm-selector');
  if (selector) {
    if (selectedFarmId) {
      selector.value = selectedFarmId;
      changeCameraFarm(selectedFarmId);
    } else {
      selector.value = "";
      changeCameraFarm("");
    }
  }
};

// Đổ danh sách vườn vào dropdown trang camera
function populateCameraFarms() {
  const selector = document.getElementById('camera-farm-selector');
  if (!selector) return;
  
  selector.innerHTML = '<option value="">-- Chọn vườn --</option>';
  farms.forEach(farm => {
    const option = document.createElement('option');
    option.value = farm.id;
    option.textContent = `${farm.name} (ID: ${farm.id})`;
    selector.appendChild(option);
  });
}

// Thay đổi vườn giám sát trên trang camera
window.changeCameraFarm = function(farmId) {
  selectedFarmId = farmId ? parseInt(farmId) : null;
  
  const warningEl = document.getElementById('camera-no-farm-warning');
  const mainContentEl = document.getElementById('camera-main-content');
  
  if (cameraSettingsInterval) {
    clearInterval(cameraSettingsInterval);
    cameraSettingsInterval = null;
  }
  
  if (!selectedFarmId) {
    if (warningEl) warningEl.classList.remove('hidden');
    if (mainContentEl) mainContentEl.classList.add('hidden');
    return;
  }
  
  if (warningEl) warningEl.classList.add('hidden');
  if (mainContentEl) mainContentEl.classList.remove('hidden');
  
  // Đồng bộ selector ở đầu trang
  const selector = document.getElementById('camera-farm-selector');
  if (selector) selector.value = selectedFarmId;
  
  // Tải cài đặt và lịch sử
  loadCameraSettings(selectedFarmId);
  loadCameraHistory(selectedFarmId);
  
  // Khởi động vòng lặp kiểm tra trạng thái thiết bị và cập nhật ảnh mới mỗi 5 giây
  cameraSettingsInterval = setInterval(() => {
    if (!isPollingCapture) {
      loadCameraSettings(selectedFarmId);
      loadCameraHistory(selectedFarmId);
    }
  }, 5000);
};

// Tải cấu hình camera & trạng thái online của Client
async function loadCameraSettings(farmId) {
  if (!farmId) return;
  try {
    const settings = await dbGetCameraSettings(farmId);
    if (settings.error) return;
    
    // Cập nhật chu kỳ chụp lên giao diện
    const intervalSelect = document.getElementById('camera-schedule-interval');
    if (intervalSelect && !document.activeElement.isSameNode(intervalSelect)) {
      intervalSelect.value = settings.camera_interval;
    }
    
    // Cập nhật trạng thái kết nối của client
    const indicator = document.getElementById('camera-ping-indicator');
    const statusText = document.getElementById('camera-ping-status');
    const lastSeenText = document.getElementById('camera-last-seen-text');
    
    if (settings.is_online) {
      if (indicator) {
        indicator.innerHTML = `
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
        `;
      }
      if (statusText) {
        statusText.textContent = "Trực tuyến (Sẵn sàng)";
        statusText.className = "text-sm font-bold text-emerald-500";
      }
    } else {
      if (indicator) {
        indicator.innerHTML = `
          <span class="relative inline-flex rounded-full h-3 w-3 bg-slate-400"></span>
        `;
      }
      if (statusText) {
        statusText.textContent = "Ngoại tuyến";
        statusText.className = "text-sm font-bold text-slate-500";
      }
    }
    
    if (lastSeenText) {
      lastSeenText.textContent = `🕒 Lần cuối hoạt động: ${settings.last_seen}`;
    }

    // Nếu đang trong quá trình chờ lệnh chụp từ xa, kiểm tra xem lệnh đã chuyển về 'idle' chưa
    if (isPollingCapture && settings.camera_command === 'idle') {
      isPollingCapture = false;
      showToast("📸 Đã nhận được ảnh chụp mới từ Camera rời!");
      const remoteBtn = document.getElementById('remote-capture-btn');
      if (remoteBtn) {
        remoteBtn.disabled = false;
        remoteBtn.innerHTML = '<i data-lucide="send" class="w-4 h-4"></i> Yêu cầu chụp từ Server';
        lucide.createIcons();
      }
      loadCameraHistory(selectedFarmId);
    }
    
  } catch (err) {
    console.error("Lỗi tải cấu hình camera:", err);
  }
}

// Lưu chu kỳ chụp tự động
window.saveCameraSchedule = async function() {
  if (!selectedFarmId) return;
  const intervalVal = document.getElementById('camera-schedule-interval').value;
  
  try {
    showToast("⌛ Đang lưu chu kỳ chụp...");
    const res = await dbUpdateCameraSettings(selectedFarmId, { camera_interval: parseInt(intervalVal) });
    if (res.error) throw new Error(res.error);
    
    showToast("✅ Lưu cấu hình chu kỳ chụp thành công!");
    loadCameraSettings(selectedFarmId);
  } catch (err) {
    showToast(`❌ Không thể lưu cấu hình: ${err.message}`);
  }
};

// Gửi lệnh chụp ảnh từ xa xuống Client
window.triggerRemoteCapture = async function() {
  if (!selectedFarmId) return;
  
  const remoteBtn = document.getElementById('remote-capture-btn');
  try {
    showToast("📡 Đang gửi lệnh yêu cầu chụp ảnh từ xa...");
    
    if (remoteBtn) {
      remoteBtn.disabled = true;
      remoteBtn.innerHTML = '<i class="w-4 h-4 animate-spin inline-block rounded-full border-2 border-white border-t-transparent mr-1"></i> Đang chờ Client chụp...';
    }
    
    const res = await dbUpdateCameraSettings(selectedFarmId, { camera_command: 'capture' });
    if (res.error) throw new Error(res.error);
    
    // Bật cờ polling đặc biệt để quét ảnh chụp mới nhanh hơn
    isPollingCapture = true;
    
    // Chờ tối đa 20 giây, cứ 2 giây kiểm tra 1 lần xem đã chụp xong chưa
    let attempts = 0;
    const checkInterval = setInterval(async () => {
      attempts++;
      await loadCameraSettings(selectedFarmId);
      
      if (!isPollingCapture || attempts >= 10) {
        clearInterval(checkInterval);
        if (isPollingCapture) {
          isPollingCapture = false;
          showToast("⚠️ Hết thời gian chờ! Client không phản hồi lệnh chụp.");
          if (remoteBtn) {
            remoteBtn.disabled = false;
            remoteBtn.innerHTML = '<i data-lucide="send" class="w-4 h-4"></i> Yêu cầu chụp từ Server';
            lucide.createIcons();
          }
        }
      }
    }, 2000);
    
  } catch (err) {
    showToast(`❌ Gửi lệnh thất bại: ${err.message}`);
    if (remoteBtn) {
      remoteBtn.disabled = false;
      remoteBtn.innerHTML = '<i data-lucide="send" class="w-4 h-4"></i> Yêu cầu chụp từ Server';
      lucide.createIcons();
    }
  }
};

// Yêu cầu chụp cục bộ trên Server (Local capture)
window.triggerLocalCapture = async function() {
  if (!selectedFarmId) return;
  
  const localBtn = document.getElementById('local-capture-btn');
  const cameraIndex = document.getElementById('local-camera-index').value;
  
  try {
    showToast("📸 Đang khởi chạy Camera máy chủ để chụp ảnh...");
    if (localBtn) {
      localBtn.disabled = true;
      localBtn.innerHTML = '<i class="w-3.5 h-3.5 animate-spin inline-block rounded-full border-2 border-white border-t-transparent mr-1"></i> Đang chụp...';
    }
    
    const res = await dbTriggerLocalCapture(selectedFarmId, parseInt(cameraIndex));
    if (res.error) throw new Error(res.error);
    
    showToast("✅ Chụp cục bộ & phân tích AI thành công!");
    loadCameraHistory(selectedFarmId);
    loadCameraSettings(selectedFarmId);
  } catch (err) {
    showToast(`❌ Không thể mở camera: ${err.message}`);
  } finally {
    if (localBtn) {
      localBtn.disabled = false;
      localBtn.innerHTML = '<i data-lucide="video" class="w-3.5 h-3.5"></i> Chụp trực tiếp bằng Server';
      lucide.createIcons();
    }
  }
};

// ============================================================
// BROWSER CAMERA — Chụp ảnh từ Camera trình duyệt (mọi thiết bị)
// ============================================================

let browserCameraStream = null;

window.openBrowserCamera = async function() {
  if (!selectedFarmId) {
    showToast("⚠️ Vui lòng chọn vườn trước khi chụp ảnh!");
    return;
  }

  const modal = document.getElementById('browser-camera-modal');
  const video = document.getElementById('browser-camera-video');
  const captured = document.getElementById('browser-camera-captured');
  const loading = document.getElementById('browser-camera-loading');
  const guide = document.getElementById('browser-camera-guide');
  const captureBtn = document.getElementById('browser-capture-btn');

  if (!modal || !video) return;

  // Reset UI
  video.classList.remove('hidden');
  if (captured) captured.classList.add('hidden');
  if (loading) loading.classList.add('hidden');
  if (guide) guide.classList.remove('hidden');
  if (captureBtn) {
    captureBtn.disabled = false;
    captureBtn.classList.remove('hidden');
    captureBtn.onclick = captureBrowserPhoto;
  }

  // Get camera preference
  const facingSelect = document.getElementById('browser-camera-facing');
  const facingMode = facingSelect ? facingSelect.value : 'environment';

  try {
    // Stop existing stream if any
    if (browserCameraStream) {
      browserCameraStream.getTracks().forEach(t => t.stop());
    }

    browserCameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: facingMode,
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    });

    video.srcObject = browserCameraStream;

    // Show modal with animation
    modal.classList.remove('opacity-0', 'pointer-events-none');

    lucide.createIcons();

  } catch (err) {
    console.error("Browser camera error:", err);
    if (err.name === 'NotAllowedError') {
      showToast("❌ Bạn cần cấp quyền truy cập Camera trong trình duyệt!");
    } else if (err.name === 'NotFoundError') {
      showToast("❌ Không tìm thấy Camera trên thiết bị này!");
    } else {
      showToast(`❌ Không thể truy cập Camera: ${err.message}`);
    }
    closeBrowserCamera();
  }
};

window.switchBrowserCamera = function() {
  // Re-open camera with the newly selected facing mode
  openBrowserCamera();
};

window.captureBrowserPhoto = async function() {
  if (!browserCameraStream || !selectedFarmId) return;

  const video = document.getElementById('browser-camera-video');
  const captured = document.getElementById('browser-camera-captured');
  const loading = document.getElementById('browser-camera-loading');
  const guide = document.getElementById('browser-camera-guide');
  const captureBtn = document.getElementById('browser-capture-btn');

  // Capture frame from video to canvas
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);

  const base64Image = canvas.toDataURL('image/jpeg', 0.85);

  // Stop camera stream to save battery/resources
  browserCameraStream.getTracks().forEach(t => t.stop());
  browserCameraStream = null;

  // Show captured preview + loading
  video.classList.add('hidden');
  if (captured) { captured.src = base64Image; captured.classList.remove('hidden'); }
  if (guide) guide.classList.add('hidden');
  if (captureBtn) captureBtn.classList.add('hidden');
  if (loading) loading.classList.remove('hidden');

  // Upload to server for AI analysis
  try {
    const res = await dbUploadCameraImage(selectedFarmId, base64Image);

    if (res.error) throw new Error(res.error);

    showToast("✅ Phân tích AI thành công! Kết quả đã lưu vào lịch sử.");

    // Refresh the camera page data
    loadCameraHistory(selectedFarmId);
    loadCameraSettings(selectedFarmId);

    // Close modal after brief delay so user sees the success
    setTimeout(() => closeBrowserCamera(), 600);

  } catch (err) {
    showToast(`❌ Lỗi phân tích: ${err.message}`);
    if (loading) loading.classList.add('hidden');

    // Show capture button as "Chụp lại" (retake) button
    if (captureBtn) {
      captureBtn.classList.remove('hidden');
      captureBtn.onclick = () => openBrowserCamera();
    }
  }
};

window.closeBrowserCamera = function() {
  // Release camera hardware
  if (browserCameraStream) {
    browserCameraStream.getTracks().forEach(t => t.stop());
    browserCameraStream = null;
  }

  const modal = document.getElementById('browser-camera-modal');
  const video = document.getElementById('browser-camera-video');

  if (video) video.srcObject = null;
  if (modal) modal.classList.add('opacity-0', 'pointer-events-none');
};


// Tải lịch sử chụp ảnh & AI phân tích
async function loadCameraHistory(farmId) {
  if (!farmId) return;
  try {
    const history = await dbGetCameraHistory(farmId);
    if (history.error) return;
    
    cameraHistoryData = history;
    
    // Cập nhật ảnh chụp mới nhất
    if (history.length > 0) {
      latestAnalysisRecord = history[0];
      
      const latestImg = document.getElementById('camera-latest-image');
      const latestTime = document.getElementById('camera-latest-time');
      
      if (latestImg) latestImg.src = latestAnalysisRecord.image_data;
      if (latestTime) latestTime.textContent = `Chụp lúc: ${window.formatDateTime(latestAnalysisRecord.timestamp)}`;
      
      renderLatestAIResult(latestAnalysisRecord);
    } else {
      latestAnalysisRecord = null;
      resetLatestUI();
    }
    
    // Render Thư viện lịch sử
    renderCameraHistory(history);
    
  } catch (err) {
    console.error("Lỗi tải lịch sử camera:", err);
  }
}

// Hiển thị kết quả AI của ảnh chụp mới nhất lên giao diện
function renderLatestAIResult(record) {
  const statusBox = document.getElementById('camera-latest-ai-status');
  const detailsBox = document.getElementById('camera-latest-ai-details');
  const barsBox = document.getElementById('camera-latest-ai-bars');
  const recsBtn = document.getElementById('camera-view-recs-btn');
  
  if (!statusBox) return;
  
  if (record.healthy) {
    statusBox.innerHTML = `
      <span class="text-3xl">🌿</span>
      <div>
        <p class="font-bold text-green-700">Cây khỏe mạnh</p>
        <p class="text-xs text-green-600">Lá cây ớt phát triển bình thường</p>
      </div>
    `;
    statusBox.className = "p-4 bg-green-50 border border-green-200 rounded-xl flex items-center gap-3 shadow-sm";
    
    if (detailsBox) detailsBox.classList.add('hidden');
    if (recsBtn) recsBtn.classList.remove('hidden');
  } else {
    const count = record.deficient_names.length;
    statusBox.innerHTML = `
      <span class="text-3xl">🔍</span>
      <div>
        <p class="font-bold text-red-700">Thiếu hụt ${count} chất</p>
        <p class="text-xs text-red-600 font-semibold">${record.deficient_names.join(', ')}</p>
      </div>
    `;
    statusBox.className = "p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 shadow-sm";
    
    if (detailsBox) detailsBox.classList.remove('hidden');
    if (recsBtn) recsBtn.classList.remove('hidden');
    
    // Vẽ các thanh phần trăm mức độ
    if (barsBox) {
      barsBox.innerHTML = Object.entries(record.scores)
        .sort((a, b) => b[1] - a[1])
        .map(([nutrient, prob]) => {
          const pct = (prob * 100).toFixed(0);
          const color = NUTRIENT_COLORS[nutrient] || '#94a3b8';
          let levelText = '';
          let barBg = '#cbd5e1';
          
          if (prob >= 0.8) { levelText = 'Nặng'; barBg = color; }
          else if (prob >= 0.65) { levelText = 'T.Bình'; barBg = color; }
          else if (prob >= 0.5) { levelText = 'Nhẹ'; barBg = color; }
          else if (prob >= 0.2) { levelText = 'Cảnh báo'; barBg = '#f59e0b'; }
          else { levelText = '✓ Khỏe'; barBg = '#cbd5e1'; }
          
          return `
            <div class="flex items-center gap-2 text-[11px] py-0.5">
              <span class="w-6 font-bold text-slate-700">${nutrient}</span>
              <div class="flex-1 bg-slate-100 rounded-full h-2">
                <div class="h-2 rounded-full transition-all" style="width:${pct}%;background:${barBg}"></div>
              </div>
              <span class="w-8 text-right font-mono font-bold" style="color:${prob >= 0.5 ? color : '#64748b'}">${pct}%</span>
              <span class="text-[9px] px-1 rounded bg-slate-50 font-medium text-slate-500">${levelText}</span>
            </div>
          `;
        }).join('');
    }
  }
}

// Reset UI khi chưa có ảnh
function resetLatestUI() {
  const latestImg = document.getElementById('camera-latest-image');
  const latestTime = document.getElementById('camera-latest-time');
  const statusBox = document.getElementById('camera-latest-ai-status');
  const detailsBox = document.getElementById('camera-latest-ai-details');
  const recsBtn = document.getElementById('camera-view-recs-btn');
  
  if (latestImg) latestImg.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='640' height='480'%3E%3Crect fill='%231e293b' width='640' height='480'/%3E%3Ctext x='320' y='240' text-anchor='middle' dy='.3em' fill='%2364748b' font-size='16' font-family='sans-serif'%3EChưa có dữ liệu ảnh chụp từ USB Camera%3C/text%3E%3C/svg%3E";
  if (latestTime) latestTime.textContent = "Chưa có ảnh chụp";
  
  if (statusBox) {
    statusBox.innerHTML = `
      <span class="text-3xl">🌿</span>
      <div>
        <p class="font-bold text-slate-700">Chưa có kết quả</p>
        <p class="text-xs text-slate-400">Hãy thực hiện chụp ảnh trước</p>
      </div>
    `;
    statusBox.className = "p-4 bg-slate-50 border border-slate-100 rounded-xl flex items-center gap-3";
  }
  
  if (detailsBox) detailsBox.classList.add('hidden');
  if (recsBtn) recsBtn.classList.add('hidden');
}

// Hiển thị lịch sử ảnh trong Thư viện
function renderCameraHistory(history) {
  const gallery = document.getElementById('camera-history-gallery');
  const emptyEl = document.getElementById('camera-history-empty');
  
  if (!gallery) return;
  
  if (history.length === 0) {
    gallery.innerHTML = "";
    if (emptyEl) emptyEl.classList.remove('hidden');
    return;
  }
  
  if (emptyEl) emptyEl.classList.add('hidden');
  
  gallery.innerHTML = history.map(item => {
    let badgeHtml = '';
    if (item.healthy) {
      badgeHtml = '<span class="text-[10px] bg-green-500 text-white font-bold px-2 py-0.5 rounded-full flex items-center gap-0.5"><i data-lucide="check-circle" class="w-3 h-3"></i> Khỏe mạnh</span>';
    } else {
      badgeHtml = `<span class="text-[10px] bg-red-500 text-white font-bold px-2 py-0.5 rounded-full flex items-center gap-0.5" title="${item.deficient_names.join(', ')}"><i data-lucide="alert-circle" class="w-3 h-3"></i> Thiếu ${item.deficient_names.length} chất</span>`;
    }
    
    return `
      <div onclick="viewHistoryRecord(${item.id})" class="group cursor-pointer bg-slate-50 rounded-xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition-all relative">
        <!-- Thumbnail -->
        <div class="aspect-[4/3] w-full overflow-hidden bg-slate-900 flex items-center justify-center">
          <img class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300" src="${item.image_data}" alt="Chilli leaf capture">
        </div>
        
        <!-- Quick stats overlay -->
        <div class="absolute top-2 left-2 right-2 flex justify-between pointer-events-none">
          ${badgeHtml}
        </div>
        
        <!-- Info text -->
        <div class="p-3 bg-white">
          <p class="text-[11px] font-bold text-slate-800 flex items-center gap-1">
            <i data-lucide="clock" class="w-3 h-3 text-slate-400"></i> ${window.formatDateTime(item.timestamp).split(' ')[0] || ''}
          </p>
          <p class="text-[10px] text-slate-400 font-semibold mt-0.5">${window.formatDateTime(item.timestamp).split(' ')[1] || ''}</p>
        </div>
      </div>
    `;
  }).join('');
  
  lucide.createIcons();
}

// Xem chi tiết lịch sử phân tích
window.viewHistoryRecord = function(recordId) {
  const record = cameraHistoryData.find(item => item.id === recordId);
  if (!record) return;
  
  openCameraDetailsModalWithData(record);
};

// Mở modal chẩn đoán chi tiết cho ảnh mới chụp
window.openCameraDetailsModal = function() {
  if (latestAnalysisRecord) {
    openCameraDetailsModalWithData(latestAnalysisRecord);
  }
};

// Đổ dữ liệu và mở Modal chẩn đoán chi tiết
function openCameraDetailsModalWithData(record) {
  const modal = document.getElementById('camera-details-modal');
  const modalImage = document.getElementById('modal-analysis-image');
  const modalTime = document.getElementById('modal-analysis-time');
  const modalStatus = document.getElementById('modal-ai-status');
  const modalBars = document.getElementById('modal-ai-bars');
  const modalRecs = document.getElementById('modal-ai-recs');
  const deleteBtn = document.getElementById('modal-delete-btn');
  
  if (!modal) return;
  
  if (deleteBtn) {
    deleteBtn.onclick = () => deleteHistoryRecord(record.id);
  }

  
  // Điền dữ liệu cơ bản
  if (modalImage) modalImage.src = record.image_data;
  if (modalTime) modalTime.textContent = `Chụp lúc: ${window.formatDateTime(record.timestamp)}`;
  
  // Trạng thái AI
  if (modalStatus) {
    if (record.healthy) {
      modalStatus.innerHTML = `
        <span class="text-3xl">🌿</span>
        <div>
          <h4 class="font-bold text-green-700 text-base">Cây khỏe mạnh phát triển tốt</h4>
          <p class="text-xs text-green-600">Mẫu lá ớt không có biểu hiện thiếu hụt dinh dưỡng vi lượng.</p>
        </div>
      `;
      modalStatus.className = "p-4 bg-green-50 border border-green-200 rounded-2xl flex items-center gap-3 shadow-sm";
    } else {
      modalStatus.innerHTML = `
        <span class="text-3xl">⚠️</span>
        <div>
          <h4 class="font-bold text-red-700 text-base">Phát hiện thiếu hụt dinh dưỡng</h4>
          <p class="text-xs text-red-600">Lá ớt đang bị thiếu chất: <strong class="underline">${record.deficient_names.join(', ')}</strong></p>
        </div>
      `;
      modalStatus.className = "p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-3 shadow-sm";
    }
  }
  
  // Vẽ các thanh biểu diễn
  if (modalBars) {
    modalBars.innerHTML = Object.entries(record.scores)
      .sort((a, b) => b[1] - a[1])
      .map(([nutrient, prob]) => {
        const pct = (prob * 100).toFixed(0);
        const color = NUTRIENT_COLORS[nutrient] || '#94a3b8';
        let barColor = '#cbd5e1';
        let badgeStyle = 'background:#f1f5f9;color:#64748b';
        let levelText = 'Bình thường';
        
        if (prob >= 0.8) { levelText = 'Nặng'; barColor = color; badgeStyle = `background:${color}22;color:${color}`; }
        else if (prob >= 0.65) { levelText = 'Trung bình'; barColor = color; badgeStyle = `background:${color}22;color:${color}`; }
        else if (prob >= 0.5) { levelText = 'Nhẹ'; barColor = color; badgeStyle = `background:${color}22;color:${color}`; }
        else if (prob >= 0.2) { levelText = 'Chú ý'; barColor = '#f59e0b'; badgeStyle = 'background:#fef3c7;color:#d97706'; }
        else { levelText = 'Khỏe mạnh'; }
        
        return `
          <div class="flex items-center gap-3 text-xs py-1">
            <span class="w-8 font-bold text-slate-700">${nutrient}</span>
            <div class="flex-grow bg-slate-200/60 rounded-full h-3">
              <div class="h-3 rounded-full transition-all" style="width:${pct}%;background:${barColor}"></div>
            </div>
            <span class="w-12 text-right font-mono font-bold ${prob >= 0.5 ? 'text-lg' : ''}" style="color:${prob >= 0.5 ? color : '#475569'}">${pct}%</span>
            <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" style="${badgeStyle}">${levelText}</span>
          </div>
        `;
      }).join('');
  }
  
  // Đổ khuyến nghị điều trị
  if (modalRecs) {
    if (record.healthy) {
      modalRecs.innerHTML = `
        <div class="p-4 bg-slate-50 border border-slate-100 rounded-2xl flex gap-3 text-sm text-slate-600">
          <i data-lucide="check-circle" class="w-5 h-5 text-green-500 shrink-0 mt-0.5"></i>
          <div>
            <p class="font-bold text-slate-700">Duy trì quy trình chăm sóc hiện tại</p>
            <p class="text-xs mt-1">Cây đang hấp thụ dinh dưỡng rất cân bằng. Hãy tiếp tục tưới nước, giữ độ ẩm đất ổn định và theo dõi biểu đồ cảm biến ESP32.</p>
          </div>
        </div>
      `;
    } else {
      modalRecs.innerHTML = record.recommendations.map(rec => {
        return `
          <div class="p-3.5 bg-slate-50 border border-slate-150 rounded-2xl flex gap-3 text-sm text-slate-700 hover:bg-slate-100/50 transition-colors">
            <i data-lucide="arrow-right-circle" class="w-5 h-5 text-indigo-500 shrink-0 mt-0.5"></i>
            <span class="leading-relaxed font-medium">${rec.replace(/^\*\*.*?\*\*:\s*/, '')}</span>
          </div>
        `;
      }).join('');
    }
  }
  
  // Hiển thị modal
  modal.classList.remove('pointer-events-none', 'opacity-0');
  modal.querySelector('.modal-container').classList.remove('scale-95');
  lucide.createIcons();
}

// Đóng modal
window.closeCameraDetailsModal = function() {
  const modal = document.getElementById('camera-details-modal');
  if (modal) {
    modal.classList.add('pointer-events-none', 'opacity-0');
    modal.querySelector('.modal-container').classList.add('scale-95');
  }
};

// Xóa 1 ảnh trong lịch sử
window.deleteHistoryRecord = async function(recordId) {
  if (!confirm("Bạn có chắc chắn muốn xóa ảnh phân tích này?")) return;
  
  try {
    showToast("⌛ Đang xóa ảnh...");
    const res = await dbDeleteCameraHistory(selectedFarmId, recordId);
    if (res.error) throw new Error(res.error);
    
    showToast("✅ Đã xóa ảnh thành công!");
    closeCameraDetailsModal();
    loadCameraHistory(selectedFarmId);
  } catch (err) {
    showToast(`❌ Không thể xóa: ${err.message}`);
  }
};

// Xóa tất cả ảnh trong lịch sử
window.cleanupCameraHistory = async function() {
  if (!selectedFarmId) return;
  if (!confirm("⚠️ NGUY HIỂM: Bạn có chắc chắn muốn xóa TẤT CẢ ảnh lịch sử của vườn này không? Hành động này không thể hoàn tác!")) return;
  
  try {
    showToast("⌛ Đang dọn dẹp thư viện...");
    const res = await dbCleanupCameraHistory(selectedFarmId);
    if (res.error) throw new Error(res.error);
    
    showToast(`✅ ${res.message}`);
    loadCameraHistory(selectedFarmId);
  } catch (err) {
    showToast(`❌ Không thể dọn dẹp: ${err.message}`);
  }
};

// Xem ảnh full-size
window.viewLatestFullImage = function() {
  if (latestAnalysisRecord) {
    // Mở popup ảnh full-size hoặc dùng chính modal chi tiết để xem
    openCameraDetailsModal();
  }
};

// Thay đổi vườn giám sát khi đổi ở dropdown đầu trang
window.changeCameraFarm = function(farmId) {
  selectedFarmId = farmId ? parseInt(farmId) : null;
  
  const warningEl = document.getElementById('camera-no-farm-warning');
  const mainContentEl = document.getElementById('camera-main-content');
  
  if (cameraSettingsInterval) {
    clearInterval(cameraSettingsInterval);
    cameraSettingsInterval = null;
  }
  
  if (!selectedFarmId) {
    if (warningEl) warningEl.classList.remove('hidden');
    if (mainContentEl) mainContentEl.classList.add('hidden');
    return;
  }
  
  if (warningEl) warningEl.classList.add('hidden');
  if (mainContentEl) mainContentEl.classList.remove('hidden');
  
  // Đồng bộ selector ở đầu trang
  const selector = document.getElementById('camera-farm-selector');
  if (selector) selector.value = selectedFarmId;
  
  // Tải cài đặt và lịch sử
  loadCameraSettings(selectedFarmId);
  loadCameraHistory(selectedFarmId);
  
  // Khởi động vòng lặp kiểm tra trạng thái thiết bị và cập nhật ảnh mới mỗi 5 giây
  cameraSettingsInterval = setInterval(() => {
    if (!isPollingCapture) {
      loadCameraSettings(selectedFarmId);
      loadCameraHistory(selectedFarmId);
    }
  }, 5000);
};

function connectCamera() {
  // Hàm này giữ lại để không bị lỗi gọi hàm cũ ở bất cứ đâu
}


function handleImageUpload(event) {
  const file = event.target.files[0];
  if (file) {
    const reader = new FileReader();
    reader.onload = (e) => {
      currentImage = e.target.result;
      document.getElementById('upload-image-preview').src = currentImage;
      document.getElementById('scan-image-preview').src = currentImage;
      document.getElementById('scan-btn').disabled = false;
      showToast('Ảnh cây ớt đã được tải lên - Sẵn sàng quét AI');
    };
    reader.readAsDataURL(file);
  }
}

// Personal Screen Camera Actions
const preview = document.getElementById('preview-image');
const imageInput = document.getElementById('imageInput');
const camera = document.getElementById('camera');
const canvas = document.getElementById('canvas');

function chooseImage() {
  if (imageInput) imageInput.click();
}

if (imageInput) {
  imageInput.addEventListener('change', function() {
    const file = this.files[0];
    if (file) {
      if (camera && camera.srcObject) {
        camera.srcObject.getTracks().forEach(t => t.stop());
        camera.srcObject = null;
        camera.classList.add('hidden');
      }
      if (preview) preview.src = URL.createObjectURL(file);
    }
  });
}

async function startCamera() {
  try {
    if (!camera) return;
    camera.classList.remove('hidden');
    // Yêu cầu độ phân giải cao, phù hợp cho WebCam USB gắn ngoài
    const stream = await navigator.mediaDevices.getUserMedia({ 
      video: { width: { ideal: 1920 }, height: { ideal: 1080 } } 
    });
    camera.srcObject = stream;
    showToast('Camera đang chạy - nhấn nút để chụp');
    const btn = document.getElementById('camera-btn');
    if (btn) { btn.textContent = '📸 Chụp'; btn.onclick = capturePhoto; }
  } catch (err) {
    showToast('Không thể mở camera: ' + err.message);
  }
}

function capturePhoto() {
  if (!camera || !camera.srcObject) return;
  const ctx = canvas.getContext('2d');
  canvas.width = camera.videoWidth;
  canvas.height = camera.videoHeight;
  ctx.drawImage(camera, 0, 0);
  
  const dataUrl = canvas.toDataURL('image/png');
  if (preview) preview.src = dataUrl;
  
  // Cập nhật currentImage cho luồng dùng chuyên nghiệp
  if (typeof currentImage !== 'undefined') {
    currentImage = dataUrl;
    const uploadPreview = document.getElementById('upload-image-preview');
    const scanPreview = document.getElementById('scan-image-preview');
    const scanBtn = document.getElementById('scan-btn');
    if (uploadPreview) uploadPreview.src = currentImage;
    if (scanPreview) scanPreview.src = currentImage;
    if (scanBtn) scanBtn.disabled = false;
  }

  camera.srcObject.getTracks().forEach(t => t.stop());
  camera.srcObject = null;
  camera.classList.add('hidden');
  showToast('Đã chụp ảnh - nhấn Quét AI để phân tích');
  const btn = document.getElementById('camera-btn');
  if (btn) { btn.textContent = 'Chụp ảnh'; btn.onclick = startCamera; }
}
