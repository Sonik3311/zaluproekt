/* ===========================
   Конфигурация и состояние
   =========================== */
const API_BASE_URL = "http://localhost:8080"; // Твой сервер на порту 8080

const API_URLS = {
  SETTINGS: API_BASE_URL + "/settings",
  COLOR_PIXEL: API_BASE_URL + "/ColorPixel",
  GET_PIXELS: (x, y, x_end, y_end) =>
    API_BASE_URL + `/GetPixels/${x}/${y}/${x_end}/${y_end}`,
  STREAM: API_BASE_URL + "/stream",
};

// Размеры будем получать с сервера
let LOGICAL_WIDTH = 10000;
let LOGICAL_HEIGHT = 10000;

const canvas = document.getElementById("c");
const wrap = document.getElementById("wrap");
const statusEl = document.getElementById("status");
const scaleLabel = document.getElementById("scaleLabel");
const boardSizeEl = document.getElementById("boardSize");
const paletteEl = document.getElementById("palette");
const eraseBtn = document.getElementById("erase");
const colorBtn = document.getElementById("colorPickerBtn");

/* Viewport / transforms */
let scale = 8;
const MIN_SCALE = 0.5;
const MAX_SCALE = 40;
let offsetX = -(LOGICAL_WIDTH / 2) * scale + window.innerWidth / 2;
let offsetY = -(LOGICAL_HEIGHT / 2) * scale + window.innerHeight / 2;

let dragging = false;
let dragStart = null;
let needsRedraw = true;

/* Pixel storage: sparse map key = "x,y" -> colorIndex */
const pixels = new Map();

/* Палитра и текущий цвет */
let colorPalette = [];
let currentColorIndex = 0;
let eraseMode = false;

/* SSE соединение */
let eventSource = null;

/* ===========================
   Инициализация приложения
   =========================== */
async function init() {
  try {
    // 1. Получаем настройки с сервера
    const settings = await fetchData(API_URLS.SETTINGS);

    // 2. Обновляем размеры доски
    LOGICAL_WIDTH = settings.board_size.x;
    LOGICAL_HEIGHT = settings.board_size.y;
    boardSizeEl.textContent = LOGICAL_WIDTH + "×" + LOGICAL_HEIGHT;

    // 3. Обрабатываем палитру
    colorPalette = settings.palette.colors.map((colorObj) =>
      numberToHexColor(colorObj.hex),
    );

    console.log("Размер доски:", LOGICAL_WIDTH, "x", LOGICAL_HEIGHT);
    console.log("Палитра:", colorPalette);

    // 4. Перестраиваем интерфейс
    rebuildPalette();
    updateOffsets();
    resizeCanvas();

    // 5. Загружаем пиксели
    await loadAllPixels();

    // 6. Подключаемся к real-time потоку
    connectToStream();

    statusEl.textContent = "Готово";
  } catch (error) {
    console.error("Ошибка при инициализации:", error);
    statusEl.textContent = "Ошибка загрузки";
  }
}

// Функция для конвертации числа в HEX-строку
function numberToHexColor(number) {
  let hexString = number.toString(16);
  while (hexString.length < 6) {
    hexString = "0" + hexString;
  }
  return "#" + hexString;
}

// Универсальная функция для GET-запросов
async function fetchData(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Ошибка HTTP: ${response.status}`);
  }
  return await response.json();
}

/* ===========================
   Работа с пикселями
   =========================== */
async function loadAllPixels() {
  try {
    statusEl.textContent = "Загрузка пикселей...";

    // Запрашиваем всю доску
    const pixelsData = await fetchData(
      API_URLS.GET_PIXELS(0, 0, LOGICAL_WIDTH - 1, LOGICAL_HEIGHT - 1),
    );

    // Очищаем текущие пиксели
    pixels.clear();

    // Заполняем данными с сервера
    pixelsData.pixels.forEach((pixel) => {
      // Конвертируем hex в индекс палитры
      const colorHex = numberToHexColor(pixel.color.hex);
      const colorIndex = colorPalette.indexOf(colorHex);

      if (colorIndex !== -1) {
        const key = pixel.x + "," + pixel.y;
        pixels.set(key, colorIndex);
      }
    });

    needsRedraw = true;
    console.log("Загружено пикселей:", pixels.size);
    statusEl.textContent = "Загружено";
  } catch (error) {
    console.error("Ошибка при загрузке пикселей:", error);
    statusEl.textContent = "Ошибка загрузки пикселей";
  }
}

/* ===========================
   Палитра - перестроение под серверные данные
   =========================== */
function rebuildPalette() {
  paletteEl.innerHTML = "";

  const r = 26;
  const cx = 32,
    cy = 32;
  const n = colorPalette.length;

  colorPalette.forEach((color, index) => {
    const ang = (index / n) * Math.PI * 2 - Math.PI / 2;
    const x = cx + Math.cos(ang) * r;
    const y = cy + Math.sin(ang) * r;

    const sw = document.createElement("div");
    sw.className = "swatch";
    sw.style.left = x - 9 + "px";
    sw.style.top = y - 9 + "px";
    sw.style.background = color;
    sw.title = `Цвет ${index}: ${color}`;

    sw.addEventListener("click", () => {
      currentColorIndex = index;
      eraseMode = false;
      updateUI();
    });

    paletteEl.appendChild(sw);
  });

  updateUI();
}

function updateUI() {
  document.querySelectorAll(".swatch").forEach((s, index) => {
    s.style.outline = index === currentColorIndex ? "2px solid #fff" : "";
  });

  paletteEl.style.boxShadow = eraseMode
    ? "inset 0 0 0 3px rgba(255,255,255,.06)"
    : "none";

  eraseBtn.style.backgroundColor = eraseMode ? "#333" : "";
  eraseBtn.style.color = eraseMode ? "#fff" : "";

  // Обновляем цвет кнопки выбора цвета
  colorBtn.style.backgroundColor = eraseMode
    ? "#666"
    : colorPalette[currentColorIndex];
}

/* ===========================
   Real-time обновления через SSE
   =========================== */
function connectToStream() {
  try {
    eventSource = new EventSource(API_URLS.STREAM);

    eventSource.addEventListener("update", function (event) {
      try {
        // Обрабатываем массив изменений
        const changes = JSON.parse(event.data);
        if (Array.isArray(changes)) {
          changes.forEach((pixelChange) => {
            updatePixelFromStream(
              pixelChange.x,
              pixelChange.y,
              pixelChange.color_id,
            );
          });
        }
      } catch (error) {
        console.error("Ошибка парсинга update:", error);
      }
    });

    eventSource.addEventListener("ping", function (event) {
      console.log("Ping от сервера");
    });

    eventSource.onerror = function (error) {
      console.error("Ошибка SSE соединения:", error);
      statusEl.textContent = "Ошибка соединения";
      setTimeout(connectToStream, 3000);
    };

    console.log("Подключились к real-time потоку");
  } catch (error) {
    console.error("Ошибка при подключении к SSE:", error);
  }
}

function updatePixelFromStream(x, y, colorId) {
  if (colorId >= 0 && colorId < colorPalette.length) {
    const key = x + "," + y;
    pixels.set(key, colorId);
    needsRedraw = true;
    console.log("апдейт пикселя:", key, colorId);
  }
}

/* ===========================
   Отправка пикселя на сервер
   =========================== */
async function sendSetPixel(x, y, colorIndex) {
  try {
    const response = await fetch(API_URLS.COLOR_PIXEL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        x: x,
        y: y,
        color: colorIndex,
      }),
    });

    if (!response.ok) {
      if (response.status === 400) {
        throw new Error("Неверный номер цвета");
      }
      throw new Error(`Ошибка HTTP: ${response.status}`);
    }

    console.log(`Пиксель [${x},${y}] закрашен цветом ${colorIndex}`);
  } catch (error) {
    console.error("Ошибка при обновлении пикселя:", error);
    alert(`Ошибка: ${error.message}`);
  }
}

/* ===========================
   Отрисовка и координаты
   =========================== */
function resizeCanvas() {
  canvas.width = wrap.clientWidth;
  canvas.height = wrap.clientHeight;
  needsRedraw = true;
}

function updateOffsets() {
  offsetX = -(LOGICAL_WIDTH / 2) * scale + window.innerWidth / 2;
  offsetY = -(LOGICAL_HEIGHT / 2) * scale + window.innerHeight / 2;
  clampOffsets();
}

function screenToCanvas(px, py) {
  const x = Math.floor((px - offsetX) / scale);
  const y = Math.floor((py - offsetY) / scale);
  return { x, y };
}

function clampOffsets() {
  const boardW = LOGICAL_WIDTH * scale;
  const boardH = LOGICAL_HEIGHT * scale;

  if (boardW <= canvas.width) {
    offsetX = (canvas.width - boardW) / 2;
  } else {
    offsetX = Math.max(canvas.width - boardW, Math.min(0, offsetX));
  }

  if (boardH <= canvas.height) {
    offsetY = (canvas.height - boardH) / 2;
  } else {
    offsetY = Math.max(canvas.height - boardH, Math.min(0, offsetY));
  }
}

function zoomAt(screenX, screenY, factor) {
  const worldX = (screenX - offsetX) / scale;
  const worldY = (screenY - offsetY) / scale;

  let newScale = scale * factor;
  newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, newScale));
  if (Math.abs(newScale - scale) < 1e-6) return;

  offsetX = screenX - worldX * newScale;
  offsetY = screenY - worldY * newScale;
  scale = newScale;

  clampOffsets();
  needsRedraw = true;
  scaleLabel.textContent = `${Math.round(scale * 100)}`;
}

/* Draw loop */
const ctx = canvas.getContext("2d");

function draw() {
  if (!needsRedraw) return;
  needsRedraw = false;
  const w = canvas.width,
    h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  // background
  ctx.fillStyle = "#07121a";
  ctx.fillRect(0, 0, w, h);

  // visible logical bounds
  const left = Math.floor(-offsetX / scale);
  const top = Math.floor(-offsetY / scale);
  const right = Math.ceil((w - offsetX) / scale);
  const bottom = Math.ceil((h - offsetY) / scale);

  const sx = Math.max(0, left);
  const sy = Math.max(0, top);
  const ex = Math.min(LOGICAL_WIDTH - 1, right);
  const ey = Math.min(LOGICAL_HEIGHT - 1, bottom);

  // draw pixels
  const visibleCount = (ex - sx + 1) * (ey - sy + 1);
  if (visibleCount <= 200000) {
    for (let y = sy; y <= ey; y++) {
      for (let x = sx; x <= ex; x++) {
        const key = x + "," + y;
        const colorIndex = pixels.get(key);
        if (colorIndex !== undefined) {
          const sxpx = Math.round(x * scale + offsetX);
          const sypy = Math.round(y * scale + offsetY);
          ctx.fillStyle = colorPalette[colorIndex];
          ctx.fillRect(sxpx, sypy, Math.ceil(scale), Math.ceil(scale));
        }
      }
    }
  } else {
    for (const [key, colorIndex] of pixels) {
      const [xStr, yStr] = key.split(",");
      const x = +xStr,
        y = +yStr;
      if (x < sx || x > ex || y < sy || y > ey) continue;
      const sxpx = Math.round(x * scale + offsetX);
      const sypy = Math.round(y * scale + offsetY);
      ctx.fillStyle = colorPalette[colorIndex];
      ctx.fillRect(
        sxpx,
        sypy,
        Math.ceil(Math.max(scale, 1)),
        Math.ceil(Math.max(scale, 1)),
      );
    }
  }

  // grid
  if (scale >= 6) {
    ctx.strokeStyle = "rgba(255,255,255,0.03)";
    ctx.lineWidth = 1;
    const startX = Math.floor(sx);
    const endX = Math.ceil(ex);
    for (let x = startX; x <= endX; x++) {
      const sxpx = Math.round(x * scale + offsetX) + 0.5;
      ctx.beginPath();
      ctx.moveTo(sxpx, 0);
      ctx.lineTo(sxpx, h);
      ctx.stroke();
    }
    const startY = Math.floor(sy);
    const endY = Math.ceil(ey);
    for (let y = startY; y <= endY; y++) {
      const sypy = Math.round(y * scale + offsetY) + 0.5;
      ctx.beginPath();
      ctx.moveTo(0, sypy);
      ctx.lineTo(w, sypy);
      ctx.stroke();
    }
  }
}

function loop() {
  if (needsRedraw) draw();
  requestAnimationFrame(loop);
}

/* ===========================
   Обработчики событий (масштабирование, клики)
   =========================== */

let lastDown = null;
let lastTouchDistance = null;
let isTouchPanning = false;
let touchStartMid = null;

/* --- Обработчик колеса --- */
function handleWheel(ev) {
  ev.preventDefault();
  const rect = wrap.getBoundingClientRect();
  const mx = ev.clientX - rect.left;
  const my = ev.clientY - rect.top;

  let factor;
  if (ev.ctrlKey) factor = 1 - ev.deltaY * 0.01;
  else factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
  if (Math.abs(factor - 1) < 0.001) factor = 1 + Math.sign(-ev.deltaY) * 0.05;

  zoomAt(mx, my, factor);
}

wrap.addEventListener("wheel", handleWheel, { passive: false });

/* --- Панорамирование мышью --- */
wrap.addEventListener("mousedown", (ev) => {
  if (ev.button !== 0) return;
  dragging = true;
  dragStart = { x: ev.clientX, y: ev.clientY, ox: offsetX, oy: offsetY };
});
window.addEventListener("mousemove", (ev) => {
  if (dragging && dragStart) {
    offsetX = dragStart.ox + (ev.clientX - dragStart.x);
    offsetY = dragStart.oy + (ev.clientY - dragStart.y);
    clampOffsets();
    needsRedraw = true;
  }
});
window.addEventListener("mouseup", () => (dragging = false));

/* --- Сенсор: pan и pinch --- */
wrap.addEventListener(
  "touchstart",
  (ev) => {
    if (ev.touches.length === 1) {
      isTouchPanning = true;
      const t = ev.touches[0];
      touchStartMid = { x: t.clientX, y: t.clientY, ox: offsetX, oy: offsetY };
      lastTouchDistance = null;
    } else if (ev.touches.length === 2) {
      isTouchPanning = false;
      const [t1, t2] = ev.touches;
      lastTouchDistance = Math.hypot(
        t2.clientX - t1.clientX,
        t2.clientY - t1.clientY,
      );
      touchStartMid = {
        x: (t1.clientX + t2.clientX) / 2,
        y: (t1.clientY + t2.clientY) / 2,
      };
    }
  },
  { passive: false },
);

wrap.addEventListener(
  "touchmove",
  (ev) => {
    ev.preventDefault();
    if (ev.touches.length === 1 && isTouchPanning && touchStartMid) {
      const t = ev.touches[0];
      offsetX = touchStartMid.ox + (t.clientX - touchStartMid.x);
      offsetY = touchStartMid.oy + (t.clientY - touchStartMid.y);
      clampOffsets();
      needsRedraw = true;
    } else if (ev.touches.length === 2 && lastTouchDistance != null) {
      const [t1, t2] = ev.touches;
      const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      const factor = dist / lastTouchDistance;
      const rect = wrap.getBoundingClientRect();
      const midX = (t1.clientX + t2.clientX) / 2 - rect.left;
      const midY = (t1.clientY + t2.clientY) / 2 - rect.top;
      zoomAt(midX, midY, factor);
      lastTouchDistance = dist;
    }
  },
  { passive: false },
);

wrap.addEventListener("touchend", () => {
  isTouchPanning = false;
  lastTouchDistance = null;
});

/* --- Клик по пикселю --- */
wrap.addEventListener("pointerdown", (e) => {
  lastDown = { x: e.clientX, y: e.clientY, time: Date.now() };
});
wrap.addEventListener("pointerup", (e) => {
  if (!lastDown) return;
  const dx = Math.abs(e.clientX - lastDown.x);
  const dy = Math.abs(e.clientY - lastDown.y);
  const dt = Date.now() - lastDown.time;

  if (dx < 6 && dy < 6 && dt < 600) {
    const rect = wrap.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;
    const { x, y } = screenToCanvas(px, py);

    if (x < 0 || x >= LOGICAL_WIDTH || y < 0 || y >= LOGICAL_HEIGHT) return;

    const colorIndex = eraseMode ? -1 : currentColorIndex;
    const key = x + "," + y;

    if (eraseMode || colorIndex === -1) {
      pixels.delete(key);
    } else {
      pixels.set(key, colorIndex);
    }

    needsRedraw = true;

    // Отправляем на сервер (для ластика отправляем -1 или обрабатываем на сервере)
    if (!eraseMode) {
      sendSetPixel(x, y, colorIndex);
    }
  }
  lastDown = null;
});

/* --- Клавиши и кнопки --- */
window.addEventListener("keydown", (e) => {
  const rect = wrap.getBoundingClientRect();
  if (e.key === "+" || e.key === "=")
    zoomAt(rect.width / 2, rect.height / 2, 1.2);
  if (e.key === "-") zoomAt(rect.width / 2, rect.height / 2, 1 / 1.2);
});

document.getElementById("zoomIn")?.addEventListener("click", () => {
  const rect = wrap.getBoundingClientRect();
  zoomAt(rect.width / 2, rect.height / 2, 1.2);
});
document.getElementById("zoomOut")?.addEventListener("click", () => {
  const rect = wrap.getBoundingClientRect();
  zoomAt(rect.width / 2, rect.height / 2, 1 / 1.2);
});

eraseBtn.addEventListener("click", () => {
  eraseMode = !eraseMode;
  updateUI();
});

/* --- Кастомный выбор цвета --- */
const nativeColor = document.getElementById("nativeColor");
colorBtn.addEventListener("click", () => {
  nativeColor.value = colorPalette[currentColorIndex];
  nativeColor.click();
});

nativeColor.addEventListener("input", (e) => {
  const newColor = e.target.value;
  const newIndex = colorPalette.indexOf(newColor);

  if (newIndex !== -1) {
    currentColorIndex = newIndex;
  } else {
    // Если цвета нет в палитре, добавляем его (опционально)
    colorPalette.push(newColor);
    currentColorIndex = colorPalette.length - 1;
    rebuildPalette();
  }

  eraseMode = false;
  updateUI();
});

/* ===========================
   Запуск приложения
   =========================== */

// Инициализация при загрузке
window.addEventListener("DOMContentLoaded", init);
window.addEventListener("resize", resizeCanvas);

// Запускаем рендеринг
resizeCanvas();
needsRedraw = true;
loop();
