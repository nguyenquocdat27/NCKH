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
        labels = history.map(d => d.timestamp.split(' ')[0]); // Lấy giờ HH:mm:ss
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
      <td class="px-4 py-3 text-slate-600 font-medium">${d.timestamp.split(' ')[0]}</td>
      <td class="text-center font-bold text-red-600">${d.temperature}°C</td>
      <td class="text-center font-bold text-cyan-600">${d.humidity}%</td>
      <td class="text-center font-bold text-amber-600">${lightDisplay}</td>
    </tr>`;
  }).join('');
}

function closeSensorChart() {
  document.getElementById('sensor-chart-modal').classList.remove('active');
}
