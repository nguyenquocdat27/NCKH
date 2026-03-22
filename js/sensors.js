// ============================================================
// SENSORS & ESP32 (js/sensors.js)
// ============================================================

function connectESP32() {
  const url = document.getElementById('esp32-url').value;
  if (!url) { showToast('Vui lòng nhập URL ESP32'); return; }
  showToast('Đang kết nối ESP32 và cảm biến...');
}

function showSensorChart(type) {
  const chartModal = document.getElementById('sensor-chart-modal');
  const chartTitle = document.getElementById('chart-title');
  const ctx = document.getElementById('sensorChart').getContext('2d');

  let data, label, color, unit;
  switch(type) {
    case 'temperature': data = sensorData.temperature; label = 'Nhiệt độ (°C)'; color = 'rgb(239,68,68)'; unit = '°C'; chartTitle.textContent = 'Biểu đồ Nhiệt độ'; break;
    case 'humidity': data = sensorData.humidity; label = 'Độ ẩm (%)'; color = 'rgb(34,197,94)'; unit = '%'; chartTitle.textContent = 'Biểu đồ Độ ẩm'; break;
    case 'light': data = sensorData.light; label = 'Ánh sáng (lux)'; color = 'rgb(217,119,6)'; unit = ' lux'; chartTitle.textContent = 'Biểu đồ Ánh sáng'; break;
  }

  if (currentChart) currentChart.destroy();

  currentChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: sensorLabels,
      datasets: [{ label, data, borderColor: color, backgroundColor: color.replace('rgb', 'rgba').replace(')', ',0.1)'), borderWidth: 2, fill: true, tension: 0.4, pointBackgroundColor: color, pointRadius: 5 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: false, grid: { color: 'rgba(0,0,0,0.05)' } }, x: { grid: { color: 'rgba(0,0,0,0.05)' } } }
    }
  });

  const avg = (data.reduce((a,b) => a+b, 0) / data.length).toFixed(1);
  const max = Math.max(...data).toFixed(1);
  const min = Math.min(...data).toFixed(1);
  document.getElementById('avg-value').textContent = avg + unit;
  document.getElementById('max-value').textContent = max + unit;
  document.getElementById('min-value').textContent = min + unit;

  chartModal.classList.add('active');
}

function closeSensorChart() {
  document.getElementById('sensor-chart-modal').classList.remove('active');
}
