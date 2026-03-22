// ============================================================
// UI & SCREEN MANAGEMENT (js/ui.js)
// ============================================================
function showScreen(screenId) {
  const screens = ['user-type-screen', 'personal-screen', 'device-screen', 'auth-screen', 'main-app'];
  screens.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
  const target = document.getElementById(screenId);
  if (target) {
    target.classList.remove('hidden');
    lucide.createIcons();
  }
}

function switchPage(page) {
  document.querySelectorAll('[id$="-page"]').forEach(el => el.classList.add('hidden'));
  const pageEl = document.getElementById(page + '-page');
  if (pageEl) pageEl.classList.remove('hidden');

  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.classList.remove('tab-active', 'border-red-500', 'text-red-600');
    tab.classList.add('tab-inactive', 'border-transparent', 'text-slate-600');
  });
  if (event && event.target && event.target.classList) {
    event.target.classList.remove('tab-inactive', 'border-transparent', 'text-slate-600');
    event.target.classList.add('tab-active', 'border-red-500', 'text-red-600');
  }
  lucide.createIcons();
}

function switchPageMobile(page) {
  switchPage(page);
  closeMobileMenu();
}

function toggleMobileMenu() {
  const overlay = document.getElementById('mobile-menu-overlay');
  const panel = document.getElementById('mobile-menu-panel');
  const isOpen = panel.classList.contains('open');
  if (isOpen) {
    panel.classList.remove('open');
    overlay.classList.add('hidden');
  } else {
    panel.classList.add('open');
    overlay.classList.remove('hidden');
  }
}

function closeMobileMenu() {
  document.getElementById('mobile-menu-panel').classList.remove('open');
  document.getElementById('mobile-menu-overlay').classList.add('hidden');
}

function showToast(message) {
  const toast = document.getElementById('toast');
  const toastMessage = document.getElementById('toast-message');
  toastMessage.textContent = message;
  toast.style.transform = 'translateY(0)';
  toast.style.opacity = '1';
  setTimeout(() => {
    toast.style.transform = 'translateY(20px)';
    toast.style.opacity = '0';
  }, 3000);
}

function goBack() {
  // Stop camera if running
  const video = document.getElementById('camera');
  if (video && video.srcObject) {
    video.srcObject.getTracks().forEach(t => t.stop());
    video.srcObject = null;
    video.classList.add('hidden');
  }
  // Reset camera button
  const btn = document.getElementById('camera-btn');
  if (btn) { btn.textContent = 'Chụp ảnh'; btn.onclick = window.startCamera; }

  showScreen('user-type-screen');
}
