/**
 * db.js — Gọi API database từ frontend
 * Quản lý: người dùng + nhà vườn
 * Import vào index.html: <script src="db.js"></script>
 */
const DB_API = '/api';
// ========================================================
// NGƯỜI DÙNG
// ========================================================

/** Tạo người dùng mới */
async function dbCreateUser({ ho_ten, email, password, so_dien_thoai = '' }) {
  const res = await fetch(`${DB_API}/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ho_ten, email, password, so_dien_thoai })
  });
  return res.json();
}

/** Lấy danh sách tất cả người dùng */
async function dbGetUsers() {
  const res = await fetch(`${DB_API}/users`);
  return res.json();
}

/** Lấy thông tin 1 người dùng theo id */
async function dbGetUser(userId) {
  const res = await fetch(`${DB_API}/users/${userId}`);
  return res.json();
}

/** Cập nhật thông tin người dùng */
async function dbUpdateUser(userId, data) {
  const res = await fetch(`${DB_API}/users/${userId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

/** Xóa người dùng */
async function dbDeleteUser(userId) {
  const res = await fetch(`${DB_API}/users/${userId}`, { method: 'DELETE' });
  return res.json();
}


// ========================================================
// NHÀ VƯỜN
// ========================================================

/** Thêm vườn mới */
async function dbCreateVuon({ user_id, ten_vuon, loai_cay = 'Cây ớt', dia_chi = '', ghi_chu = '' }) {
  const res = await fetch(`${DB_API}/vuons`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id, ten_vuon, loai_cay, dia_chi, ghi_chu })
  });
  return res.json();
}

/** Lấy tất cả vườn (truyền userId để lọc theo user) */
async function dbGetVuons(userId = null) {
  const url = userId ? `${DB_API}/vuons?user_id=${userId}` : `${DB_API}/vuons`;
  const res  = await fetch(url);
  return res.json();
}

/** Lấy thông tin 1 vườn */
async function dbGetVuon(vuonId) {
  const res = await fetch(`${DB_API}/vuons/${vuonId}`);
  return res.json();
}

/** Cập nhật thông tin vườn */
async function dbUpdateVuon(vuonId, data) {
  const res = await fetch(`${DB_API}/vuons/${vuonId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  });
  return res.json();
}

/** Xóa vườn */
async function dbDeleteVuon(vuonId) {
  const res = await fetch(`${DB_API}/vuons/${vuonId}`, { method: 'DELETE' });
  return res.json();
}


// ========================================================
// VÍ DỤ SỬ DỤNG (xóa khi deploy)
// ========================================================
/*
// Tạo người dùng
const user = await dbCreateUser({
  ho_ten: 'Nguyễn Văn A',
  email:  'a@gmail.com',
  password: '123456',
  so_dien_thoai: '0901234567'
});
console.log(user);

// Thêm vườn cho user id=1
const vuon = await dbCreateVuon({
  user_id:   1,
  ten_vuon:  'Vườn ớt Tây Ninh',
  dien_tich: 500,
  loai_cay:  'Cây ớt',
  dia_chi:   'Tây Ninh',
  ghi_chu:   'Vườn chính'
});
console.log(vuon);

// Lấy tất cả vườn của user id=1
const vuons = await dbGetVuons(1);
console.log(vuons);
*/
