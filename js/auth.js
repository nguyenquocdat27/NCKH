// ============================================================
// AUTH & USER TYPE MANAGEMENT (js/auth.js)
// ============================================================

document.addEventListener('DOMContentLoaded', async () => {
  lucide.createIcons();

  document.getElementById('logout-btn').addEventListener('click', () => {
    currentUser = null; farms = []; selectedFarmId = null; deviceType = null;
    localStorage.removeItem('userSession');
    localStorage.removeItem('deviceType');
    showScreen('user-type-screen');
    showToast('Đã đăng xuất');
  });

  // Luôn bắt đầu bằng màn hình chọn chế độ
  showScreen('user-type-screen');
});

async function selectUserType(type) {
  if (type === 'personal') {
    showScreen('personal-screen');
  } else if (type === 'pro') {
    const savedSession = localStorage.getItem('userSession');
    if (savedSession) {
      currentUser = JSON.parse(savedSession);
      await loginSuccess(); // Bỏ qua đăng nhập, tới Chọn thiết bị
    } else {
      showScreen('auth-screen');
    }
  }
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById('login-tab');
  const signupTab = document.getElementById('signup-tab');
  const loginForm = document.getElementById('login-form');
  const signupForm = document.getElementById('signup-form');

  if (tab === 'login') {
    loginTab.classList.add('text-red-600', 'bg-red-50');
    loginTab.classList.remove('text-slate-600');
    signupTab.classList.remove('text-red-600', 'bg-red-50');
    signupTab.classList.add('text-slate-600');
    loginForm.classList.remove('hidden');
    signupForm.classList.add('hidden');
  } else {
    signupTab.classList.add('text-red-600', 'bg-red-50');
    signupTab.classList.remove('text-slate-600');
    loginTab.classList.remove('text-red-600', 'bg-red-50');
    loginTab.classList.add('text-slate-600');
    signupForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
  }
}

async function handleLogin(event) {
  event.preventDefault();
  const email    = event.target.querySelector('input[type="text"]').value;
  const password = event.target.querySelector('input[type="password"]').value;

  try {
    const res = await fetch(`${BACKEND_URL}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (data.error) {
      showToast(`❌ ${data.error}`);
      return;
    }

    currentUser = { name: data.user.ho_ten, email: data.user.email, db_id: data.user.id };
    localStorage.setItem('userSession', JSON.stringify(currentUser));
    showToast(`✅ Chào mừng ${data.user.ho_ten}!`);
    await loginSuccess();
  } catch (err) {
    showToast('❌ Không kết nối được server!');
  }
}

async function handleSignup(event) {
  event.preventDefault();
  const inputs   = event.target.querySelectorAll('input');
  const ho_ten   = inputs[0].value;
  const email    = inputs[1].value;
  const password = inputs[3].value;

  if (password.length < 6) {
    showToast('❌ Mật khẩu ít nhất 6 ký tự!');
    return;
  }

  try {
    const res = await dbCreateUser({ ho_ten, email, password });
    if (res.error) {
      showToast(`❌ ${res.error}`);
      return;
    }

    currentUser = { name: ho_ten, email, db_id: res.user.id };
    localStorage.setItem('userSession', JSON.stringify(currentUser));
    showToast(`✅ Đăng ký thành công! Chào ${ho_ten}`);
    await loginSuccess();
  } catch (err) {
    showToast('❌ Không kết nối được server!');
  }
}

async function loginSuccess() {
  showScreen('device-screen');
  farms = [];
  const el = document.getElementById('user-name');
  if (el) el.textContent = currentUser.name;

  if (currentUser.db_id) {
    try {
      const vuons = await window.dbGetVuons(currentUser.db_id);
      farms = vuons.map(v => ({
        id:       v.id,
        name:     v.ten_vuon,
        loai_cay: v.loai_cay,
        dia_chi:  v.dia_chi,
        ghi_chu:  v.ghi_chu,
        ngay_tao: v.ngay_tao,
      }));
      window.updateFarmsList();
      window.updateDashboard();
    } catch (err) {
      console.log('Không load được vườn:', err);
    }
  }
}

function backToLogin() {
  currentUser = null; deviceType = null;
  localStorage.removeItem('userSession');
  localStorage.removeItem('deviceType');
  showScreen('auth-screen');
}

function backToUserType() {
  currentUser = null; deviceType = null;
  localStorage.removeItem('userSession');
  localStorage.removeItem('deviceType');
  showScreen('user-type-screen');
}

function selectDevice(type, skipToast = false) {
  deviceType = type;
  localStorage.setItem('deviceType', type);
  const names = { mobile: 'Điện thoại', desktop: 'Máy tính' };
  showScreen('main-app');
  window.updateDashboard();
  if (!skipToast) showToast(`Đã chọn chế độ ${names[type]}`);
}
