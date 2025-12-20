/* ===========================
   Конфигурация и состояние
   =========================== */
const API_BASE_URL = "http://localhost:8080";

const API_URLS = {
  SETTINGS: API_BASE_URL + "/api/settings",
  COLOR_PIXEL: API_BASE_URL + "/api/ColorPixel",
  GET_PIXELS: (x, y, x_end, y_end) =>
    API_BASE_URL + `/api/GetPixels/${x}/${y}/${x_end}/${y_end}`,
  STREAM: API_BASE_URL + "/api/stream",
};

// Резервная палитра на 12 цветов (используется если сервер недоступен)
const FALLBACK_PALETTE = [
  "#ff6b6b", "#ff9e6d", "#ffcc5c", "#a8e6cf", "#4ecdc4", "#45b7d1",
  "#96ceb4", "#588157", "#3a5a40", "#344e41", "#9a8c98", "#4a4e69"
];

// Размеры будем получать с сервера
let LOGICAL_WIDTH = 2500;
let LOGICAL_HEIGHT = 2500;

const canvas = document.getElementById("c");
const wrap = document.getElementById("wrap");
const statusEl = document.getElementById("status");
const scaleLabel = document.getElementById("scaleLabel");
const boardSizeEl = document.getElementById("boardSize");
const paletteEl = document.getElementById("palette");
const hintText = document.getElementById("hintText");

/* Viewport / transforms */
let scale = 8;
const MIN_SCALE = 0.5;
const MAX_SCALE = 40;
let offsetX = 0;
let offsetY = 0;

let dragging = false;
let dragStart = null;
let needsRedraw = true;

/* Pixel storage: sparse map key = "x,y" -> colorIndex */
const pixels = new Map();

/* Палитра и текущий цвет */
let colorPalette = FALLBACK_PALETTE; // Начинаем с резервной
let currentColorIndex = null; // null означает "цвет не выбран"
let isServerOnline = false;

/* SSE соединение */
let eventSource = null;

/* ===========================
   Инициализация приложения
   =========================== */
async function init() {
  try {
    // 1. Пробуем получить настройки с сервера
    let serverSettings = null;
    try {
      serverSettings = await fetchWithTimeout(API_URLS.SETTINGS, 3000);
      isServerOnline = true;
    } catch (serverError) {
      console.log("Сервер недоступен, используем локальную палитру");
      isServerOnline = false;
    }

    if (isServerOnline && serverSettings) {
      // Сервер доступен - используем его настройки
      LOGICAL_WIDTH = serverSettings.board_size.x;
      LOGICAL_HEIGHT = serverSettings.board_size.y;
      
      // Берем первые 12 цветов с сервера
      const allColors = serverSettings.palette.colors;
      const colorsToUse = allColors.slice(0, 12);
      colorPalette = colorsToUse.map((colorObj) => 
        numberToHexColor(colorObj.hex)
      );
      
      statusEl.textContent = "Сервер онлайн";
      console.log("Используем палитру с сервера:", colorPalette);
      
      // Пробуем загрузить пиксели
      try {
        await loadAllPixels();
      } catch (pixelError) {
        console.log("Не удалось загрузить пиксели, продолжаем без них");
      }
      
      // Пробуем подключиться к SSE
      try {
        connectToStream();
      } catch (sseError) {
        console.log("SSE недоступен");
      }
      
    } else {
      // Сервер недоступен - используем локальные данные
      LOGICAL_WIDTH = 2500;
      LOGICAL_HEIGHT = 2500;
      colorPalette = FALLBACK_PALETTE;
      statusEl.textContent = "Сервер оффлайн (только просмотр)";
      console.log("Используем локальную палитру:", colorPalette);
    }

    // Обновляем интерфейс
    boardSizeEl.textContent = LOGICAL_WIDTH + "×" + LOGICAL_HEIGHT;
    rebuildPalette();
    updateOffsets();
    resizeCanvas();
    updateHint();

    console.log("Размер доски:", LOGICAL_WIDTH, "x", LOGICAL_HEIGHT);
    console.log("Палитра (12 цветов):", colorPalette);

  } catch (error) {
    console.error("Ошибка при инициализации:", error);
    statusEl.textContent = "Ошибка загрузки";
    // Все равно показываем интерфейс с резервной палитрой
    boardSizeEl.textContent = "2500×2500";
    rebuildPalette();
    resizeCanvas();
  }
}

// Функция fetch с таймаутом
async function fetchWithTimeout(url, timeout = 5000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`Ошибка HTTP: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
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

/* ===========================
   Работа с пикселями (только при онлайн режиме)
   =========================== */
async function loadAllPixels() {
  if (!isServerOnline) return;
  
  try {
    statusEl.textContent = "Загрузка пикселей...";

    // Запрашиваем всю доску
    const pixelsData = await fetchWithTimeout(
      API_URLS.GET_PIXELS(0, 0, LOGICAL_WIDTH - 1, LOGICAL_HEIGHT - 1),
      10000
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
    statusEl.textContent = "Сервер онлайн";

  } catch (error) {
    console.error("Ошибка при загрузке пикселей:", error);
    statusEl.textContent = "Сервер онлайн (пиксели не загружены)";
  }
}

/* ===========================
   Палитра - 12 цветов по кругу (работает всегда)
   =========================== */
function rebuildPalette() {
  paletteEl.innerHTML = "";

  const radius = 24;
  const centerX = 32;
  const centerY = 32;
  const totalColors = colorPalette.length;

  colorPalette.forEach((color, index) => {
    // Рассчитываем позицию на круге
    const angle = (index / totalColors) * Math.PI * 2 - Math.PI / 2;
    const x = centerX + Math.cos(angle) * radius;
    const y = centerY + Math.sin(angle) * radius;

    const swatch = document.createElement("div");
    swatch.className = "swatch";
    swatch.style.left = (x - 10) + "px";
    swatch.style.top = (y - 10) + "px";
    swatch.style.background = color;
    
    // Номер цвета (1-12)
    swatch.textContent = index + 1;
    
    // Подсказка при наведении
    let titleText = `Цвет ${index + 1}: ${color}\nКлик: выбрать/отменить`;
    if (!isServerOnline) {
      titleText += "\n(сервер оффлайн - нельзя закрашивать)";
    }
    swatch.title = titleText;

    swatch.addEventListener("click", () => {
      toggleColorSelection(index);
    });

    paletteEl.appendChild(swatch);
  });

  updateUI();
}

function toggleColorSelection(index) {
  if (currentColorIndex === index) {
    // Повторное нажатие на тот же цвет - снимаем выбор
    currentColorIndex = null;
    console.log("Выбор цвета отменен");
  } else {
    // Выбираем новый цвет
    currentColorIndex = index;
    console.log(`Выбран цвет ${index + 1}: ${colorPalette[index]}`);
  }
  updateUI();
  updateHint();
}

function updateUI() {
  // Снимаем выделение со всех цветов
  document.querySelectorAll(".swatch").forEach((swatch, index) => {
    swatch.classList.remove("selected");
  });

  // Выделяем выбранный цвет (если есть)
  if (currentColorIndex !== null) {
    const selectedSwatch = document.querySelectorAll(".swatch")[currentColorIndex];
    if (selectedSwatch) {
      selectedSwatch.classList.add("selected");
    }
  }
}

function updateHint() {
  if (!hintText) return;
  
  if (!isServerOnline) {
    hintText.textContent = "Сервер недоступен. Можно только просматривать и выбирать цвета.";
  } else if (currentColorIndex === null) {
    hintText.textContent = "Колесо — зум, перетаскивать — пан. Выберите цвет для закрашивания";
  } else {
    const colorName = colorPalette[currentColorIndex];
    hintText.textContent = `Колесо — зум, перетаскивать — пан. Выбран цвет ${currentColorIndex + 1} (${colorName}) — клик для отмены`;
  }
}

/* ===========================
   Real-time обновления через SSE (только при онлайн)
   =========================== */
function connectToStream() {
  if (!isServerOnline) return;
  
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
              pixelChange.color.color_id,
            );
          });
        }
      } catch (error) {
        console.error("Ошибка парсинга update:", error);
      }
    });

    eventSource.onerror = function (error) {
      console.error("Ошибка SSE соединения:", error);
      statusEl.textContent = "Сервер онлайн (SSE ошибка)";
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
  }
}

/* ===========================
   Отправка пикселя на сервер (только при онлайн)
   =========================== */
async function sendSetPixel(x, y, colorIndex) {
  if (!isServerOnline) {
    alert("Сервер недоступен. Невозможно закрасить пиксель.");
    return;
  }
  
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
   Отрисовка и координаты (работает всегда)
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
   Обработчики событий
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
    // Проверяем, выбран ли цвет
    if (currentColorIndex === null) {
      console.log("Цвет не выбран. Нажмите на цвет в палитре.");
      return;
    }

    const rect = wrap.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const py = e.clientY - rect.top;
    const { x, y } = screenToCanvas(px, py);

    if (x < 0 || x >= LOGICAL_WIDTH || y < 0 || y >= LOGICAL_HEIGHT) return;

    // В оффлайн режиме только визуальное закрашивание
    if (!isServerOnline) {
      const key = x + "," + y;
      pixels.set(key, currentColorIndex);
      needsRedraw = true;
      console.log(`Пиксель [${x},${y}] закрашен локально (оффлайн)`);
      return;
    }

    // В онлайн режиме отправляем на сервер
    const key = x + "," + y;
    pixels.set(key, currentColorIndex);
    needsRedraw = true;

    // Отправляем на сервер
    sendSetPixel(x, y, currentColorIndex);
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
