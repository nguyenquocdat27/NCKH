// ============================================================
// SENSORS & ESP32 (js/sensors.js)
// ============================================================

let sensorPollingInterval = null;

function connectESP32() {
  const url = document.getElementById('esp32-url').value;
  if (!url) { showToast('Vui lòng nhập URL ESP32'); return; }
  showToast('Đang kết nối ESP32 và tải dữ liệu...');
  startSensorPolling();
}

window.fetchAndUpdateSensors = async function() {
  if (!selectedFarmId) return;

  // Đồng bộ trạng thái thiết bị điều khiển (Quạt/Bơm) từ server
  window.fetchDeviceControlState(selectedFarmId);

  try {
    const history = await dbGetSensorHistory(selectedFarmId, 10);
    if (!history || history.length === 0) return;

    // Backend trả về oldest -> newest. Nên lấy bản ghi cuối cùng làm giá trị hiện tại (mới nhất)
    const latest = history[history.length - 1];

    const tEl = document.getElementById('esp32-temp');
    if (tEl) tEl.textContent = `${latest.temperature.toFixed(2)}°C`;

    const hEl = document.getElementById('esp32-humidity');
    if (hEl) hEl.textContent = latest.humidity !== null ? `${latest.humidity.toFixed(0)}%` : '--';

    const lEl = document.getElementById('esp32-light');
    if (lEl) {
      lEl.textContent = (latest.light !== null && latest.light >= 0) ? `${latest.light.toFixed(0)} lux` : '--';
    }

    renderSensorHistoryTable(history);
  } catch (e) {
    console.error("Lỗi lấy dữ liệu sensors:", e);
  }
}

function startSensorPolling() {
  if (sensorPollingInterval) clearInterval(sensorPollingInterval);
  window.fetchAndUpdateSensors();
  sensorPollingInterval = setInterval(window.fetchAndUpdateSensors, 5000);
}

// Tự động khởi chạy ngay khi mở trang web (Không cần nhấn Nút kết nối ESP32)
document.addEventListener('DOMContentLoaded', () => {
    startSensorPolling();
});

async function showSensorChart(type) {
  const chartModal = document.getElementById('sensor-chart-modal');
  const chartTitle = document.getElementById('chart-title');
  const ctx = document.getElementById('sensorChart').getContext('2d');

  let data = [];
  let labels = [];
  let label = '';
  let color = '';
  let unit = '';

  // 1. Lọc thông tin theo loại cảm biến
  switch(type) {
    case 'temperature': label = 'Nhiệt độ (°C)'; color = 'rgb(239,68,68)'; unit = '°C'; chartTitle.textContent = 'Biểu đồ Nhiệt độ'; break;
    case 'humidity':    label = 'Độ ẩm (%)';    color = 'rgb(34,197,94)'; unit = '%';  chartTitle.textContent = 'Biểu đồ Độ ẩm';   break;
    case 'light':       label = 'Ánh sáng (lux)'; color = 'rgb(217,119,6)'; unit = ' lux'; chartTitle.textContent = 'Biểu đồ Ánh sáng'; break;
  }

  // 2. Lấy dữ liệu (Từ API nếu có selectedFarmId, ngược lại dùng dummy)
  if (selectedFarmId) {
    try {
      const history = await dbGetSensorHistory(selectedFarmId);
      if (history && history.length > 0) {
        labels = history.map(d => {
          const dateObj = new Date(d.timestamp);
          const hrs = String(dateObj.getHours()).padStart(2, '0');
          const mins = String(dateObj.getMinutes()).padStart(2, '0');
          return `${hrs}:${mins}`;
        });
        data   = history.map(d => d[type]);
      }
    } catch (err) {
      console.warn('Lỗi lấy dữ liệu sensor, dùng debug data:', err);
    }
  }

  // Fallback nếu không có dữ liệu API
  if (data.length === 0) {
    data   = sensorData[type];
    labels = sensorLabels;
  }

  // 3. Vẽ biểu đồ
  if (currentChart) currentChart.destroy();
  currentChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{ label, data, borderColor: color, backgroundColor: color.replace('rgb', 'rgba').replace(')', ',0.1)'), borderWidth: 2, fill: true, tension: 0.4, pointBackgroundColor: color, pointRadius: 5 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' } }, x: { grid: { color: 'rgba(0,0,0,0.05)' } } }
    }
  });

  // 4. Cập nhật thống kê
  const avg = (data.reduce((a,b) => a+b, 0) / data.length).toFixed(1);
  const max = Math.max(...data).toFixed(1);
  const min = Math.min(...data).toFixed(1);
  document.getElementById('avg-value').textContent = avg + unit;
  document.getElementById('max-value').textContent = max + unit;
  document.getElementById('min-value').textContent = min + unit;

  // 5. Cập nhật Bảng lịch sử (Nếu có dữ liệu thật)
  if (selectedFarmId) {
    const history = await dbGetSensorHistory(selectedFarmId, 10);
    renderSensorHistoryTable(history);
  }

  chartModal.classList.add('active');
}

/** Hiển thị dữ liệu vào bảng lịch sử trên trang ESP32 */
function renderSensorHistoryTable(history) {
  const tbody = document.querySelector('#esp32-page tbody');
  if (!tbody || !history) return;

  if (history.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-8 text-center text-slate-400 italic">Chưa có dữ liệu cảm biến</td></tr>';
    return;
  }

  // Backend trả về oldest -> newest. Revert array để hiển thị newest lên đầu
  const sortedHistory = [...history].reverse();

  tbody.innerHTML = sortedHistory.map(d => {
    const lightDisplay = (d.light === null || d.light < 0)
      ? '<span class="text-slate-400 italic">--</span>'
      : `${d.light} lux`;
    return `
    <tr class="hover:bg-slate-50 transition-colors">
      <td class="px-4 py-3 text-slate-600 font-medium">${window.formatDateTime(d.timestamp)}</td>
      <td class="text-center font-bold text-red-600">${d.temperature}°C</td>
      <td class="text-center font-bold text-cyan-600">${d.humidity}%</td>
      <td class="text-center font-bold text-amber-600">${lightDisplay}</td>
    </tr>`;
  }).join('');
}

function closeSensorChart() {
  document.getElementById('sensor-chart-modal').classList.remove('active');
}

// ============================================================
// LOGIC ĐIỀU KHIỂN THIẾT BỊ DUAL RELAY (QUẠT & BƠM)
// ============================================================

window.currentDeviceState = { manual: false, fan_state: false, pump_state: false };

window.fetchDeviceControlState = async function(vuonId) {
  if (!vuonId) return;
  try {
    const res = await fetch(`/api/control?vuon_id=${vuonId}`);
    const state = await res.json();
    window.updateControlUI(state);
  } catch (err) {
    console.error("Lỗi lấy trạng thái điều khiển thiết bị:", err);
  }
}

window.updateControlUI = function(state) {
  const toggle = document.getElementById('mode-toggle');
  const modeText = document.getElementById('mode-status-text');
  const labelAuto = document.getElementById('label-auto');
  const labelManual = document.getElementById('label-manual');

  // Nút Quạt
  const fanBtn = document.getElementById('fan-btn');
  const fanBtnText = document.getElementById('fan-btn-text');
  const fanBadge = document.getElementById('fan-status-badge');
  const fanIcon = document.getElementById('fan-icon');
  const fanNote = document.getElementById('fan-auto-note');

  // Nút Bơm
  const pumpBtn = document.getElementById('pump-btn');
  const pumpBtnText = document.getElementById('pump-btn-text');
  const pumpBadge = document.getElementById('pump-status-badge');
  const pumpIcon = document.getElementById('pump-icon');
  const pumpNote = document.getElementById('pump-auto-note');

  if (!toggle) return; // Bảo vệ nếu HTML chưa load xong

  // 1. Chế độ điều khiển
  toggle.checked = state.manual;
  window.currentDeviceState = state;

  if (state.manual) {
    modeText.textContent = "Chế độ: THỦ CÔNG";
    labelManual.classList.add('text-red-500');
    labelManual.classList.remove('text-slate-400');
    labelAuto.classList.remove('text-red-500');
    labelAuto.classList.add('text-slate-400');
    
    // Mở khóa các nút điều khiển
    fanBtn.disabled = false;
    pumpBtn.disabled = false;

    fanNote.classList.add('hidden');
    pumpNote.classList.add('hidden');
  } else {
    modeText.textContent = "Chế độ: TỰ ĐỘNG (Auto)";
    labelAuto.classList.add('text-red-500');
    labelAuto.classList.remove('text-slate-400');
    labelManual.classList.remove('text-red-500');
    labelManual.classList.add('text-slate-400');

    // Khóa các nút điều khiển
    fanBtn.disabled = true;
    pumpBtn.disabled = true;

    fanNote.classList.remove('hidden');
    pumpNote.classList.remove('hidden');
  }

  // 2. Cập nhật giao diện Quạt (Relay 1)
  if (state.fan_state) {
    fanBadge.textContent = "BẬT";
    fanBadge.className = "text-xs px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-600";
    fanBtnText.textContent = state.manual ? "TẮT QUẠT GIÓ" : "TỰ ĐỘNG: BẬT";
    
    // Gradient màu xanh active
    fanBtn.className = "w-full py-3 rounded-xl font-bold text-white transition-all duration-300 shadow-md flex items-center justify-center gap-3 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 shadow-emerald-100";
    fanIcon.className = "w-5 h-5 animate-spin-fast";
  } else {
    fanBadge.textContent = "TẮT";
    fanBadge.className = "text-xs px-2 py-0.5 rounded-full font-bold bg-rose-100 text-rose-600";
    fanBtnText.textContent = state.manual ? "BẬT QUẠT GIÓ" : "TỰ ĐỘNG: TẮT";
    
    // Gradient màu đỏ inactive
    fanBtn.className = "w-full py-3 rounded-xl font-bold text-white transition-all duration-300 shadow-md flex items-center justify-center gap-3 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed bg-gradient-to-r from-rose-500 to-red-500 hover:from-rose-600 hover:to-red-600 shadow-rose-100";
    fanIcon.className = "w-5 h-5";
  }

  // 3. Cập nhật giao diện Bơm (Relay 2)
  if (state.pump_state) {
    pumpBadge.textContent = "BẬT";
    pumpBadge.className = "text-xs px-2 py-0.5 rounded-full font-bold bg-blue-100 text-blue-600";
    pumpBtnText.textContent = state.manual ? "TẮT BƠM NƯỚC" : "TỰ ĐỘNG: BẬT";
    
    // Gradient màu xanh dương active
    pumpBtn.className = "w-full py-3 rounded-xl font-bold text-white transition-all duration-300 shadow-md flex items-center justify-center gap-3 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600 shadow-blue-100";
    pumpIcon.className = "w-5 h-5 animate-pulse-blue";
  } else {
    pumpBadge.textContent = "TẮT";
    pumpBadge.className = "text-xs px-2 py-0.5 rounded-full font-bold bg-rose-100 text-rose-600";
    pumpBtnText.textContent = state.manual ? "BẬT BƠM NƯỚC" : "TỰ ĐỘNG: TẮT";
    
    // Gradient màu đỏ inactive
    pumpBtn.className = "w-full py-3 rounded-xl font-bold text-white transition-all duration-300 shadow-md flex items-center justify-center gap-3 active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed bg-gradient-to-r from-rose-500 to-red-500 hover:from-rose-600 hover:to-red-600 shadow-rose-100";
    pumpIcon.className = "w-5 h-5";
  }
}

window.toggleControlMode = async function(isManual) {
  if (!selectedFarmId) {
    showToast("❌ Vui lòng chọn vườn trước khi đổi chế độ!");
    document.getElementById('mode-toggle').checked = !isManual;
    return;
  }

  try {
    const res = await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vuon_id: selectedFarmId,
        manual: isManual
      })
    });
    const result = await res.json();
    if (result.success) {
      showToast(`⚡ Đã chuyển sang chế độ: ${isManual ? 'THỦ CÔNG' : 'TỰ ĐỘNG'}`);
      await window.fetchDeviceControlState(selectedFarmId);
    } else {
      throw new Error(result.error);
    }
  } catch (err) {
    console.error("Lỗi khi chuyển đổi chế độ:", err);
    showToast("❌ Lỗi cấu hình chế độ điều khiển");
    document.getElementById('mode-toggle').checked = !isManual;
  }
}

window.toggleDeviceState = async function(deviceType) {
  if (!selectedFarmId) {
    showToast("❌ Vui lòng chọn một vườn!");
    return;
  }

  if (!window.currentDeviceState || !window.currentDeviceState.manual) {
    showToast("⚠️ Vui lòng chuyển chế độ sang THỦ CÔNG để điều khiển!");
    return;
  }

  try {
    const payload = { vuon_id: selectedFarmId };
    if (deviceType === 'fan') {
      payload.fan_state = !window.currentDeviceState.fan_state;
    } else if (deviceType === 'pump') {
      payload.pump_state = !window.currentDeviceState.pump_state;
    }

    const res = await fetch('/api/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const result = await res.json();
    
    if (result.success) {
      const stateLabel = payload.fan_state !== undefined 
        ? (payload.fan_state ? 'Bật Quạt' : 'Tắt Quạt') 
        : (payload.pump_state ? 'Bật Bơm' : 'Tắt Bơm');
      showToast(`✅ Đã gửi lệnh: ${stateLabel}`);
      await window.fetchDeviceControlState(selectedFarmId);
    } else {
      throw new Error(result.error);
    }
  } catch (err) {
    console.error("Lỗi khi chuyển trạng thái thiết bị:", err);
    showToast("❌ Lỗi điều khiển thiết bị!");
  }
}
