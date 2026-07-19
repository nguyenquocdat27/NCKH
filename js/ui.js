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

let isAnimatingPage = false;

function switchPage(page) {
  if (isAnimatingPage) return;
  const targetPage = document.getElementById(page + '-page');
  if (!targetPage) return;

  // Update tabs
  document.querySelectorAll('.nav-tab').forEach(tab => {
    tab.classList.remove('tab-active', 'font-bold', 'bg-[#2D6A4F]', 'text-white', 'shadow-md');
    tab.classList.add('tab-inactive', 'font-semibold', 'text-slate-600', 'hover:text-[#2D6A4F]', 'hover:bg-white/60');
  });
  if (event && event.target) {
    const targetTab = event.target.closest ? event.target.closest('.nav-tab') : event.target;
    if (targetTab && targetTab.classList) {
      targetTab.classList.remove('tab-inactive', 'font-semibold', 'text-slate-600', 'hover:text-[#2D6A4F]', 'hover:bg-white/60');
      targetTab.classList.add('tab-active', 'font-bold', 'bg-[#2D6A4F]', 'text-white', 'shadow-md');
    }
  }

  // Find currently visible page
  let currentPage = null;
  document.querySelectorAll('[id$="-page"]').forEach(el => {
    if (!el.classList.contains('hidden')) currentPage = el;
  });

  if (currentPage && currentPage !== targetPage) {
    isAnimatingPage = true;
    currentPage.classList.add('page-exit');
    setTimeout(() => {
      currentPage.classList.add('hidden');
      currentPage.classList.remove('page-exit');
      
      targetPage.classList.remove('hidden');
      targetPage.classList.add('page-enter');
      
      setTimeout(() => {
        targetPage.classList.remove('page-enter');
        isAnimatingPage = false;
        if (page === 'camera' && window.initCameraPage) window.initCameraPage();
        lucide.createIcons();
      }, 500); 
    }, 400); 
  } else if (!currentPage) {
    targetPage.classList.remove('hidden');
    targetPage.classList.add('page-enter');
    isAnimatingPage = true;
    setTimeout(() => {
      targetPage.classList.remove('page-enter');
      isAnimatingPage = false;
      if (page === 'camera' && window.initCameraPage) window.initCameraPage();
      lucide.createIcons();
    }, 500);
  }
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
