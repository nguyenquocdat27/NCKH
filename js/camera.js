// ============================================================
// CAMERA HANDLING (js/camera.js)
// ============================================================

function connectCamera() {
  const url = document.getElementById('camera-url').value;
  if (!url) { showToast('Vui lòng nhập URL camera'); return; }
  document.getElementById('camera-stream').src = url;
  showToast('Đang kết nối camera ESP32...');
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
