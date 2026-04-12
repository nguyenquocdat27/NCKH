// ============================================================
// FARM MANAGEMENT (js/farms.js)
// ============================================================

function openAddFarmModal() {
  document.getElementById('add-farm-modal').classList.add('active');
}

function closeAddFarmModal() {
  document.getElementById('add-farm-modal').classList.remove('active');
  document.getElementById('farm-name').value    = '';
  document.getElementById('farm-loaicay').value = 'Cây ớt';
  document.getElementById('farm-diachi').value  = '';
  document.getElementById('farm-ghichu').value  = '';
}

async function handleAddFarm(event) {
  event.preventDefault();
  const ten_vuon = document.getElementById('farm-name').value;
  const loai_cay = document.getElementById('farm-loaicay').value;
  const dia_chi  = document.getElementById('farm-diachi').value;
  const ghi_chu  = document.getElementById('farm-ghichu').value;
  const userId   = currentUser?.db_id;

  if (!userId) {
    showToast('❌ Vui lòng đăng nhập lại!');
    return;
  }

  try {
    const res = await window.dbCreateVuon({ user_id: userId, ten_vuon, loai_cay, dia_chi, ghi_chu });
    if (res.error) throw new Error(res.error);

    farms.push({
      id:       res.vuon.id,
      name:     res.vuon.ten_vuon,
      loai_cay: res.vuon.loai_cay,
      dia_chi:  res.vuon.dia_chi,
      ghi_chu:  res.vuon.ghi_chu,
    });

    closeAddFarmModal();
    showToast(`✅ Đã tạo vườn "${ten_vuon}"`);
    updateFarmsList();
    updateDashboard();

  } catch (err) {
    console.error('Lỗi thêm vườn:', err);
    showToast(`❌ Lỗi: ${err.message}`);
  }
}

function updateFarmsList() {
  const farmsList = document.getElementById('farms-list');
  const noFarms   = document.getElementById('no-farms');
  if (farms.length === 0) {
    farmsList.innerHTML = '';
    noFarms.classList.remove('hidden');
    populateFarmSelector();
    return;
  }
  noFarms.classList.add('hidden');
  farmsList.innerHTML = farms.map(farm => `
    <div class="card-hover bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
      <div class="flex items-start justify-between mb-4">
        <div class="w-12 h-12 rounded-lg bg-gradient-to-br from-red-400 to-orange-500 flex items-center justify-center">
          <i data-lucide="flame" class="w-6 h-6 text-white"></i>
        </div>
        <span class="w-3 h-3 rounded-full bg-teal-400 inline-block mt-1"></span>
      </div>
      <h3 class="text-lg font-semibold text-slate-800 mb-2">${farm.name} <span class="text-sm font-normal text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full ml-1">ID: ${farm.id}</span></h3>
      <div class="space-y-1 mb-4 text-sm text-slate-600">
        <p>🌱 ${farm.loai_cay || 'Cây ớt'}</p>
        ${farm.dia_chi ? `<p>📍 ${farm.dia_chi}</p>` : ''}
        ${farm.ghi_chu ? `<p>📝 ${farm.ghi_chu}</p>` : ''}
      </div>
      <button onclick="editFarm('${farm.id}')" class="w-full px-3 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2">
        <i data-lucide="edit" class="w-4 h-4"></i> Quản lý
      </button>
    </div>
  `).join('');
  lucide.createIcons();
  populateFarmSelector();
}

function editFarm(farmId) {
  selectedFarmId = farmId;
  const farm = farms.find(f => f.id === farmId);
  if (farm) {
    showToast(`Đã mở ${farm.name}`);
    
    const selector = document.getElementById('active-farm-selector');
    if (selector) selector.value = farmId;

    document.querySelectorAll('[id$="-page"]').forEach(el => el.classList.add('hidden'));
    document.getElementById('esp32-page').classList.remove('hidden');
    
    document.querySelectorAll('.nav-tab').forEach(tab => {
      tab.classList.remove('tab-active', 'border-red-500', 'text-red-600');
      tab.classList.add('tab-inactive', 'border-transparent', 'text-slate-600');
      if (tab.getAttribute('onclick') && tab.getAttribute('onclick').includes("switchPage('esp32')")) {
        tab.classList.remove('tab-inactive', 'border-transparent', 'text-slate-600');
        tab.classList.add('tab-active', 'border-red-500', 'text-red-600');
      }
    });

    lucide.createIcons();
    if (window.fetchAndUpdateSensors) window.fetchAndUpdateSensors();
  }
}

function updateDashboard() {
  const fc = document.getElementById('farms-count');
  const sc = document.getElementById('scan-count');
  const ac = document.getElementById('alert-count');
  const hp = document.getElementById('health-percent');
  if (fc) fc.textContent = farms.length;
  if (sc) sc.textContent = '0';
  if (ac) ac.textContent = '0';
  if (hp) hp.textContent = '95%';
}

function populateFarmSelector() {
  const selector = document.getElementById('active-farm-selector');
  if (!selector) return;
  
  selector.innerHTML = '<option value="">-- Chọn vườn --</option>';
  farms.forEach(farm => {
    const option = document.createElement('option');
    option.value = farm.id;
    option.textContent = `${farm.name} (ID: ${farm.id})`;
    selector.appendChild(option);
  });
  
  if (selectedFarmId) {
    selector.value = selectedFarmId;
  }
}

function changeActiveFarm(farmId) {
  selectedFarmId = farmId;
  const farm = farms.find(f => f.id === farmId);
  if (farm) {
    showToast(`Đã đổi sang: ${farm.name}`);
    if (window.fetchAndUpdateSensors) {
      window.fetchAndUpdateSensors();
    }
  }
}

