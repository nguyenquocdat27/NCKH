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

    // Cập nhật Bảng lịch sử cảm biến
    renderSensorHistoryTable(history);
    
    // Lấy lịch sử hoạt động thiết bị (Quạt/Bơm) từ backend
    fetchDeviceHistory();
  } catch (e) {
    console.error("Lỗi lấy dữ liệu sensors:", e);
  }
}

async function fetchDeviceHistory() {
  if (!selectedFarmId) return;
  try {
    const res = await fetch(`/api/device_history/${selectedFarmId}`);
    const data = await res.json();
    if (!data.error) {
      updateDeviceHistoryUI(data);
    }
  } catch(e) {
    console.error("Lỗi lấy lịch sử thiết bị:", e);
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

window.deviceStateHistory = [];

window.updateControlUI = function(state) {
  // Không cần làm gì nữa vì đã dùng fetchDeviceHistory để cập nhật UI
}

function updateDeviceHistoryUI(data) {
  const historyList = document.getElementById('device-history-list');
  if (!historyList) return;
  
  historyList.innerHTML = '';
  
  // Trạng thái ESP32
  const statusLi = document.createElement('li');
  const isOnline = !data.is_offline;
  statusLi.className = `p-3 rounded-xl border ${isOnline ? 'bg-emerald-50 border-emerald-100' : 'bg-slate-50 border-slate-200'} flex items-center justify-between transition-all`;
  
  // Format last seen
  let lastSeenStr = 'Chưa có dữ liệu';
  if (data.last_seen) {
     const d = new Date(data.last_seen);
     lastSeenStr = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
  }

  statusLi.innerHTML = `
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-sm">
        <i data-lucide="wifi" class="w-4 h-4 ${isOnline ? 'text-emerald-500' : 'text-slate-500'}"></i>
      </div>
      <div>
        <p class="text-sm font-semibold text-slate-700">Trạng thái ESP32</p>
        <p class="text-xs font-bold ${isOnline ? 'text-emerald-500' : 'text-slate-500'}">${isOnline ? '✓ Đang hoạt động' : '✗ Ngoại tuyến'}</p>
      </div>
    </div>
    <div class="text-right">
      <p class="text-xs font-bold text-slate-600">${isOnline ? 'Hiện tại' : lastSeenStr}</p>
      <p class="text-[10px] text-slate-400">Lần cuối</p>
    </div>
  `;
  historyList.appendChild(statusLi);

  // Quạt gió
  let fanTimeStr = 'Chưa từng chạy';
  let fanDateStr = '';
  if (data.last_fan_on) {
     const d = new Date(data.last_fan_on);
     fanTimeStr = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
     fanDateStr = d.toLocaleDateString();
  }
  const fanLi = document.createElement('li');
  fanLi.className = `p-3 rounded-xl border bg-cyan-50 border-cyan-100 flex items-center justify-between transition-all mt-3`;
  fanLi.innerHTML = `
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-sm">
        <i data-lucide="fan" class="w-4 h-4 text-cyan-500"></i>
      </div>
      <div>
        <p class="text-sm font-semibold text-slate-700">Quạt gió (Giảm nhiệt)</p>
        <p class="text-xs font-bold text-cyan-500">Lần cuối > 30°C</p>
      </div>
    </div>
    <div class="text-right">
      <p class="text-xs font-bold text-slate-600">${fanTimeStr}</p>
      <p class="text-[10px] text-slate-400">${fanDateStr}</p>
    </div>
  `;
  historyList.appendChild(fanLi);

  // Máy bơm
  let pumpTimeStr = 'Chưa từng chạy';
  let pumpDateStr = '';
  if (data.last_pump_on) {
     const d = new Date(data.last_pump_on);
     pumpTimeStr = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
     pumpDateStr = d.toLocaleDateString();
  }
  const pumpLi = document.createElement('li');
  pumpLi.className = `p-3 rounded-xl border bg-blue-50 border-blue-100 flex items-center justify-between transition-all mt-3`;
  pumpLi.innerHTML = `
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-full bg-white flex items-center justify-center shadow-sm">
        <i data-lucide="droplets" class="w-4 h-4 text-blue-500"></i>
      </div>
      <div>
        <p class="text-sm font-semibold text-slate-700">Máy bơm (Tưới ẩm)</p>
        <p class="text-xs font-bold text-blue-500">Lần cuối < 50%</p>
      </div>
    </div>
    <div class="text-right">
      <p class="text-xs font-bold text-slate-600">${pumpTimeStr}</p>
      <p class="text-[10px] text-slate-400">${pumpDateStr}</p>
    </div>
  `;
  historyList.appendChild(pumpLi);
  
  if (window.lucide) {
    lucide.createIcons();
  }
  
  // Cập nhật nhãn Online/Offline
  const badges = ['badge-temp', 'badge-hum', 'badge-light'];
  badges.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
       if (isOnline) {
          el.className = "text-sm font-semibold text-teal-600 bg-teal-50 px-2 py-1 rounded-full";
          el.textContent = "✓ Online";
       } else {
          el.className = "text-sm font-semibold text-rose-600 bg-rose-50 px-2 py-1 rounded-full";
          el.textContent = "✗ Ngoại tuyến";
       }
    }
  });
}
