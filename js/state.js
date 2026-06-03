// ============================================================
// STATE (js/state.js)
// ============================================================
const defaultConfig = { system_name: 'AI trong Nông Nghiệp' };
let currentUser = null;
let farms = [];
let selectedFarmId = null;
let deviceType = null;
let currentImage = null;
let currentChart = null;
let sensorData = {
  temperature: [28.5, 28.2, 28.1, 27.9, 28.3, 28.6, 28.4, 28.5, 28.7, 28.2],
  humidity: [65, 64, 66, 67, 65, 64, 63, 65, 66, 64],
  light: [850, 840, 880, 860, 870, 880, 890, 870, 860, 850]
};
let sensorLabels = ['14:05','14:15','14:25','14:35','14:45','14:55','15:05','15:15','15:25','15:35'];

// Màu cho từng chất
const NUTRIENT_COLORS = {
  Ca: '#f97316', K: '#ef4444', Mn: '#8b5cf6',
  N:  '#3b82f6', P: '#10b981', S: '#f59e0b', Zn: '#06b6d4'
};

// URL phục vụ Đăng nhập & Tạo Vườn
const BACKEND_URL = ''; // Để rỗng nếu backend cùng host với frontend

// URL phục vụ AI
const AI_URL = ''; // Để rỗng nếu backend cùng host

// Hàm helper dùng chung để định dạng chuỗi thời gian ISO UTC sang giờ địa phương của trình duyệt
window.formatDateTime = function(isoString) {
  if (!isoString) return '';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    
    return `${hours}:${minutes}:${seconds} ${day}/${month}/${year}`;
  } catch (e) {
    console.error("Lỗi format thời gian:", e);
    return isoString;
  }
};

