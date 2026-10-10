const tg = window.Telegram?.WebApp;
tg?.ready();
tg?.expand();

const API = "";
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const dayInput = $("#day"), slotsEl = $("#slots"), totalEl = $("#total"), bookBtn = $("#book"), notice = $("#notice");
let selectedHours = 1, selectedStart = null, config = {price_per_hour:1200};
const money = n => new Intl.NumberFormat("ru-RU").format(n) + " ₽";
const now = new Date();
const localDate = new Date(now.getTime() - now.getTimezoneOffset()*60000).toISOString().slice(0,10);
dayInput.min = localDate; dayInput.value = localDate;

function goTab(name) {
  $$(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === name));
  $$(".view").forEach(v => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "booking") loadSlots();
  if (name === "my") loadMyBookings();
  window.scrollTo({top:0, behavior:"smooth"});
  tg?.HapticFeedback?.selectionChanged();
}
$$(".tab").forEach(b => b.addEventListener("click", () => goTab(b.dataset.tab)));
$$("[data-go]").forEach(b => b.addEventListener("click", () => {
  if (b.dataset.go === "booking") $("#bookingTab").classList.remove("hidden-tab");
  goTab(b.dataset.go);
}));

function clearSelection() {
  selectedStart = null; bookBtn.disabled = true; bookBtn.textContent = "Выбери время"; totalEl.textContent = "—";
}
async function loadSlots() {
  clearSelection();
  const day = dayInput.value;
  if (!day) return;
  slotsEl.innerHTML = '<p class="muted">Загружаю свободное время…</p>';
  try {
    const response = await fetch(`${API}/api/availability?day=${encodeURIComponent(day)}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось загрузить расписание");
    const items = data.slots.filter(x => x.hours === selectedHours);
    slotsEl.innerHTML = "";
    if (!items.length) { slotsEl.innerHTML = '<p class="muted">На эту дату нет подходящих интервалов.</p>'; return; }
    items.forEach(item => {
      const b = document.createElement("button"); b.className = "slot";
      b.textContent = item.start_at.slice(11,16); b.disabled = !item.available;
      b.title = item.available ? money(item.total) : "Время занято";
      if (!item.available) b.classList.add("unavailable");
      b.addEventListener("click", () => {
        $$(".slot").forEach(x=>x.classList.remove("selected")); b.classList.add("selected");
        selectedStart = item.start_at; totalEl.textContent = money(item.total);
        bookBtn.disabled = false; bookBtn.textContent = "Отправить заявку";
        $("#slotHint").textContent = `Выбрано: ${b.textContent}`;
      });
      slotsEl.appendChild(b);
    });
  } catch(e) { slotsEl.innerHTML = `<p class="muted">${e.message || "Проверь соединение с сервером."}</p>`; }
}
$$("[data-hours]").forEach(b => b.addEventListener("click", () => {
  $$("[data-hours]").forEach(x=>x.classList.toggle("selected",x===b));
  selectedHours = Number(b.dataset.hours); loadSlots();
}));
dayInput.addEventListener("change", loadSlots);

bookBtn.addEventListener("click", async () => {
  if (!tg?.initDataUnsafe?.user?.id || !tg?.initData) {
    notice.textContent = "Открой приложение через Telegram, чтобы подтвердить аккаунт."; return;
  }
  if (!selectedStart) return;
  bookBtn.disabled = true; bookBtn.textContent = "Отправляю…";
  try {
    const response = await fetch(`${API}/api/bookings`, {method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({init_data:tg.initData,start_at:selectedStart,hours:selectedHours})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Не удалось создать заявку");
    notice.textContent = `Заявка №${data.booking_id} создана на ${data.start_at.replace("T"," ")}. Сумма: ${money(data.total)}. Дождись подтверждения администратора.`;
    tg?.HapticFeedback?.notificationOccurred("success");
    await loadMyBookings(); await loadSlots();
  } catch(e) { notice.textContent = e.message; bookBtn.disabled = false; bookBtn.textContent = "Повторить"; }
});

async function loadMyBookings() {
  const target = $("#myBookings");
  if (!tg?.initData) { target.textContent = "Открой Mini App из Telegram."; return; }
  target.innerHTML = '<p class="muted">Загружаю…</p>';
  try {
    const res = await fetch(`${API}/api/my-bookings`, {headers:{"X-Telegram-Init-Data":tg.initData}});
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Не удалось загрузить бронирования");
    target.innerHTML = "";
    if (!data.bookings.length) { target.innerHTML = '<p class="muted">Пока нет заявок. Перейди во вкладку «Бронь», чтобы выбрать время.</p>'; return; }
    data.bookings.forEach(b => {
      const card = document.createElement("article"); card.className="booking-item";
      const title = document.createElement("b"); title.textContent = `Заявка №${b.id}`;
      const line = document.createElement("p"); line.textContent = `${b.start_at.replace("T"," ")} · ${b.hours} ч. · ${money(b.total)}`;
      const status = document.createElement("span"); status.className = "status"; status.textContent = ({pending:"Ожидает подтверждения",confirmed:"Подтверждена",cancelled:"Отменена",completed:"Завершена"})[b.status] || b.status;
      card.append(title,line,status); target.appendChild(card);
    });
  } catch(e) { target.textContent = e.message; }
}
$("#loadBookings").addEventListener("click", loadMyBookings);
fetch(`${API}/api/config`).then(r=>r.json()).then(c=>{config=c;}).catch(()=>{});
