const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const API = ""; // Mini App and API are served from the same HTTPS domain
const dayInput = document.querySelector("#day");
const slotsEl = document.querySelector("#slots");
const totalEl = document.querySelector("#total");
const bookBtn = document.querySelector("#book");
const notice = document.querySelector("#notice");
let selectedHours = 1;
let selectedStart = null;
let config = {price_per_hour:1200};
const now = new Date();
const localDate = new Date(now.getTime() - now.getTimezoneOffset()*60000).toISOString().slice(0,10);
dayInput.min = localDate;
dayInput.value = localDate;

function userId() {
  return tg?.initDataUnsafe?.user?.id || null;
}
function money(n) {
  return new Intl.NumberFormat("ru-RU").format(n) + " ₽";
}
function clearSelection() {
  selectedStart = null;
  bookBtn.disabled = true;
  bookBtn.textContent = "Выбери время";
  totalEl.textContent = "—";
}
async function loadSlots() {
  clearSelection();
  const day = dayInput.value;
  if (!day) return;
    slotsEl.innerHTML = '<p class="muted">Загружаю свободное время…</p>';
  try {
    const response = await fetch(`${API}/api/availability?day=${encodeURIComponent(day)}`);
    const data = await response.json();
    const items = data.slots.filter(x => x.hours === selectedHours);
    slotsEl.innerHTML = "";
    if (!items.length) {
      slotsEl.innerHTML = '<p class="muted">Нет доступных вариантов на эту дату.</p>';
      return;
    }
    items.forEach(item => {
      const b = document.createElement("button");
      b.className = "slot";
      b.textContent = item.start_at.slice(11,16);
      b.disabled = !item.available;
      b.title = item.available ? money(item.total) : "Занято";
      b.addEventListener("click", () => {
        document.querySelectorAll(".slot").forEach(x=>x.classList.remove("selected"));
        b.classList.add("selected");
        selectedStart = item.start_at;
        totalEl.textContent = money(item.total);
        bookBtn.disabled = false;
        bookBtn.textContent = "Оставить заявку";
      });
      slotsEl.appendChild(b);
    });
  } catch {
    slotsEl.innerHTML = '<p class="muted">Не удалось загрузить расписание. Проверь сервер.</p>';
  }
}
document.querySelectorAll("[data-hours]").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll("[data-hours]").forEach(x=>x.classList.remove("selected"));
  b.classList.add("selected");
  selectedHours = Number(b.dataset.hours);
  loadSlots();
}));
dayInput.addEventListener("change", loadSlots);

bookBtn.addEventListener("click", async () => {
  const uid = userId();
  if (!uid || !tg?.initData) {
    notice.textContent = "Открой приложение через кнопку в Telegram, чтобы подтвердить аккаунт.";
    return;
  }
  if (!selectedStart) return;
  bookBtn.disabled = true;
  bookBtn.textContent = "Отправляю…";
  try {
    const response = await fetch(`${API}/api/bookings`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({init_data:tg?.initData || "",start_at:selectedStart,hours:selectedHours})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось создать заявку");
    notice.textContent = `Заявка №${data.booking_id} создана. Стоимость: ${money(data.total)}. Оплата пока не подключена.`;
    tg?.HapticFeedback?.notificationOccurred("success");
    await loadMyBookings();
    await loadSlots();
  } catch(e) {
    notice.textContent = e.message;
    bookBtn.disabled = false;
    bookBtn.textContent = "Повторить";
  }
});
async function loadMyBookings() {
  const uid = userId();
  const target = document.querySelector("#myBookings");
  if (!uid) { target.textContent = "Открой Mini App из Telegram."; return; }
    try {
    const res = await fetch(`${API}/api/my-bookings`, {headers:{"X-Telegram-Init-Data":tg?.initData || ""}});
    const data = await res.json();
    target.innerHTML = "";
    if (!data.bookings.length) { target.textContent = "Бронирований пока нет."; return; }
    data.bookings.forEach(b => {
      const div = document.createElement("div");
      div.className = "booking-item";
      div.textContent = `№${b.id} · ${b.start_at.replace("T"," ")} · ${b.hours} ч. · ${money(b.total)} · ${b.status}`;
      target.appendChild(div);
    });
  } catch { target.textContent = "Не удалось загрузить бронирования."; }
}
document.querySelector("#loadBookings").addEventListener("click",loadMyBookings);
fetch(`${API}/api/config`).then(r=>r.json()).then(c=>{config=c;}).catch(()=>{});
loadSlots();
