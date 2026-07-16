/* ============================================================
   رصيد | Raseed AI — Frontend logic
   يحاول الاتصال بالـ API الحقيقي (FastAPI backend). إذا تعذّر
   الاتصال (لا يوجد سيرفر شغّال، أو رابط غير محدث) يتحول تلقائيًا
   لوضع تجريبي محلي بنفس منطق main.py حتى يبقى العرض شغّالاً.
   ============================================================ */

// 🔧 رابط API على Railway
const API_URL = "https://raseed-backend-production.up.railway.app";
const FETCH_TIMEOUT = 2500;

let apiAvailable = false;

/* ---------- fetch helper مع timeout ---------- */
async function apiPost(path, body) {
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
  try {
    const res = await fetch(API_URL + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    clearTimeout(t);
    if (!res.ok) throw new Error("bad status");
    return await res.json();
  } catch (e) {
    clearTimeout(t);
    throw e;
  }
}

/* ---------- health check ---------- */
async function checkHealth() {
  const dot = document.getElementById("apiDot");
  const txt = document.getElementById("apiStatusText");
  try {
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), FETCH_TIMEOUT);
    const res = await fetch(API_URL + "/health", { signal: controller.signal });
    clearTimeout(t);
    if (!res.ok) throw new Error("down");
    const data = await res.json();
    apiAvailable = true;
    dot.classList.add("ok");
    txt.textContent = data.model_loaded ? "متصل — النموذج جاهز" : "متصل — وضع القواعد";
  } catch (e) {
    apiAvailable = false;
    dot.classList.add("err");
    txt.textContent = "وضع تجريبي (بدون خادم)";
  }
}
checkHealth();

/* ============================================================
   ١. الشات
   ============================================================ */
const chatWindow = document.getElementById("chatWindow");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");

function appendMsg(role, html) {
  const row = document.createElement("div");
  row.className = "msg msg-" + role;
  row.innerHTML = `
    <div class="msg-avatar">${role === "bot" ? "ر" : "أ"}</div>
    <div class="msg-bubble">${html}</div>`;
  chatWindow.appendChild(row);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return row;
}

function showTyping() {
  const row = appendMsg("bot", `<div class="typing"><span></span><span></span><span></span></div>`);
  row.id = "typingRow";
  return row;
}

/* منطق محلي مطابق لـ main.py /chat */
function localChatReply(message, inc, exp, bal) {
  const msg = message.toLowerCase();
  const sav = inc - exp;
  if (/سيارة|سياره|car/.test(msg)) {
    const mp = Math.round(120000 / 60);
    const pct = +(mp / inc * 100).toFixed(1);
    return `🚗 تحليل شراء سيارة بـ 120,000 ريال:\n\n• راتبك: ${inc.toLocaleString()} ريال\n• القسط المتوقع (60 شهر): ${mp.toLocaleString()} ريال (${pct}% من راتبك)\n\n` +
      (pct < 25 ? "✅ القرار آمن." : `⚠️ القسط مرتفع (${pct}%). ننصح بدفعة أولى أكبر.`);
  }
  if (/ادخار|وفر|توفير/.test(msg)) {
    const sp = Math.round(sav * 0.2);
    return `💰 خطة الادخار:\n\n• الادخار المقترح (20%): ${sp.toLocaleString()} ريال/شهر\n• بعد سنة: ${(sp*12).toLocaleString()} ريال\n• بعد 5 سنوات: ${(sp*60).toLocaleString()} ريال`;
  }
  if (/قرض|تمويل/.test(msg)) {
    return `🏦 الحد الأقصى الآمن للقرض: ${Math.round(inc*0.33*60).toLocaleString()} ريال\n• القسط الشهري الآمن: ${Math.round(inc*0.33).toLocaleString()} ريال`;
  }
  if (/رصيد|حساب|كم عندي/.test(msg)) {
    return `💳 رصيدك: ${bal.toLocaleString()} ريال\n• دخل: ${inc.toLocaleString()} | مصاريف: ${exp.toLocaleString()}\n• صافي الشهر: ${sav.toLocaleString()} ريال\n` +
      (sav > 0 ? "✅ وضعك جيد." : "⚠️ مصاريفك تتجاوز دخلك!");
  }
  if (/مصاريف|انفاق|إنفاق/.test(msg)) {
    const r = +(exp / inc * 100).toFixed(1);
    return `📊 إنفاقك ${exp.toLocaleString()} ريال (${r}% من دخلك)\n` + (r < 70 ? "✅ في الحد المعقول." : "⚠️ مرتفع — قلل الكماليات.");
  }
  return "أنا Raseed AI 🤖 — اسألني عن:\n• 🚗 شراء سيارة أو منزل\n• 💰 خطة ادخار\n• 🏦 تقييم قرض\n• 📊 تحليل إنفاق\n• 💳 رصيدك";
}

async function sendChat(text) {
  appendMsg("user", text);
  showTyping();

  const income = +document.getElementById("chatIncome").value || 12000;
  const expenses = +document.getElementById("chatExpenses").value || 7200;
  const balance = +document.getElementById("chatBalance").value || 15400;

  let reply;
  try {
    if (!apiAvailable) throw new Error("skip");
    const data = await apiPost("/chat", {
      message: text, monthly_income: income, monthly_expenses: expenses, balance: balance,
    });
    reply = data.reply;
  } catch (e) {
    await new Promise((r) => setTimeout(r, 500)); // إحساس طبيعي بالرد
    reply = localChatReply(text, income, expenses, balance);
  }

  document.getElementById("typingRow")?.remove();
  appendMsg("bot", reply.replace(/\n/g, "<br>"));
}

chatForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  sendChat(text);
});

document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => sendChat(chip.dataset.q));
});

/* ============================================================
   ٢. التوأم المالي (Financial Twin)
   ============================================================ */
const twinRunBtn = document.getElementById("twinRun");
const twinChart = document.getElementById("twinChart");
const ctx = twinChart.getContext("2d");

function localSimulate({ income, expenses, decision, months, label }) {
  let bal = 0;
  const timeline = [];
  for (let m = 1; m <= months; m++) {
    const net = income - expenses - decision;
    bal += net;
    timeline.push({ month: m, balance: +bal.toFixed(2), danger: bal < 0 });
  }
  const neg = timeline.filter((t) => t.danger).length;
  let risk, safe, advice;
  if (neg > 6) { risk = "مرتفع"; safe = false; advice = `⚠️ خطر — عجز في ${neg} شهرًا.`; }
  else if (neg > 0) { risk = "متوسط"; safe = false; advice = `⚠️ مخاطر في ${neg} شهر.`; }
  else { risk = "منخفض"; safe = true; advice = `✅ آمن. رصيدك بعد ${months} شهر: ${Math.round(bal).toLocaleString()} ريال`; }
  return { decision: label, risk_level: risk, safe_to_proceed: safe, advice, final_balance: bal, negative_months: neg, timeline };
}

function drawChart(timeline) {
  const w = twinChart.width, h = twinChart.height, pad = 20;
  ctx.clearRect(0, 0, w, h);

  const balances = timeline.map((t) => t.balance);
  const max = Math.max(...balances, 0);
  const min = Math.min(...balances, 0);
  const range = max - min || 1;

  // خط الصفر
  const zeroY = h - pad - ((0 - min) / range) * (h - pad * 2);
  ctx.strokeStyle = "rgba(237,240,247,0.15)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(pad, zeroY);
  ctx.lineTo(w - pad, zeroY);
  ctx.stroke();

  // منحنى الرصيد
  ctx.beginPath();
  timeline.forEach((t, i) => {
    const x = pad + (i / (timeline.length - 1)) * (w - pad * 2);
    const y = h - pad - ((t.balance - min) / range) * (h - pad * 2);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  const grad = ctx.createLinearGradient(0, 0, w, 0);
  grad.addColorStop(0, "#E8825A");
  grad.addColorStop(1, "#5FCF9B");
  ctx.strokeStyle = grad;
  ctx.lineWidth = 2.5;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();

  // تعبئة خفيفة تحت المنحنى
  ctx.lineTo(w - pad, zeroY);
  ctx.lineTo(pad, zeroY);
  ctx.closePath();
  ctx.fillStyle = "rgba(232,130,90,0.08)";
  ctx.fill();
}

function runTwin() {
  const income = +document.getElementById("twinIncome").value || 0;
  const expenses = +document.getElementById("twinExpenses").value || 0;
  const decision = +document.getElementById("twinDecision").value || 0;
  const label = document.getElementById("twinLabel").value || "قرار مالي";

  const finish = (result, timelineFull) => {
    const badge = document.getElementById("verdictBadge");
    const text = document.getElementById("verdictText");
    badge.textContent = result.risk_level + " مخاطرة";
    badge.className = "verdict-badge " + (result.safe_to_proceed ? "safe" : "risk");
    text.textContent = result.advice;

    drawChart(timelineFull);

    document.getElementById("twinStats").innerHTML = `
      <div class="stat"><span class="stat-val">${Math.round(result.final_balance).toLocaleString()}</span><span class="stat-lbl">الرصيد بعد الفترة (ريال)</span></div>
      <div class="stat"><span class="stat-val">${result.negative_months}</span><span class="stat-lbl">أشهر بعجز مالي</span></div>
      <div class="stat"><span class="stat-val">${Math.round(decision / income * 1000) / 10}%</span><span class="stat-lbl">من الدخل الشهري</span></div>`;
  };

  (async () => {
    if (apiAvailable) {
      try {
        const data = await apiPost("/simulate", {
          monthly_income: income, fixed_expenses: expenses, decision_cost: decision,
          months: 60, decision_label: label,
        });
        // الـ API يرجع أول 12 شهر فقط للـ timeline — نبني منحنى كامل محليًا للعرض البصري
        const local = localSimulate({ income, expenses, decision, months: 60, label });
        finish(data, local.timeline);
        return;
      } catch (e) { /* fallback below */ }
    }
    const local = localSimulate({ income, expenses, decision, months: 60, label });
    finish(local, local.timeline);
  })();
}

twinRunBtn.addEventListener("click", runTwin);

/* ============================================================
   ٣. الصندوق الاستثماري
   ملاحظة: نسخة سابقة كانت تطبّق العائد كنسبة ثابتة مرة واحدة على
   إجمالي الادخار (totalSaved * 1.08) بغض النظر عن المدة — رياضيًا
   غلط (يعطي نفس العائد سواء كانت الخطة 3 أشهر أو 5 سنوات). هذا
   يحسب عائد مركّب شهري فعلي: كل شهر يكبر الرصيد بنسبة العائد
   الشهري قبل إضافة السحب الجديد.
   ============================================================ */
function monthsToReachGoal(goal, monthly, annualReturnPct) {
  const r = annualReturnPct / 100 / 12;
  if (monthly <= 0) return Infinity;
  if (r === 0) return Math.ceil(goal / monthly);
  const n = Math.log(1 + (goal * r) / monthly) / Math.log(1 + r);
  return Math.max(1, Math.ceil(n));
}

function buildFundSchedule(monthly, annualReturnPct, months) {
  const r = annualReturnPct / 100 / 12;
  let balance = 0;
  const rows = [];
  for (let m = 1; m <= months; m++) {
    balance = balance * (1 + r) + monthly;
    rows.push({ month: m, contributed: monthly * m, balance });
  }
  return rows;
}

function runFund() {
  const goal = +document.getElementById("fundGoal").value || 0;
  const monthly = +document.getElementById("fundMonthly").value || 0;
  const returnPct = +document.getElementById("fundReturn").value || 0;

  if (goal <= 0 || monthly <= 0) {
    document.getElementById("fundVerdictText").textContent = "أدخل هدف وسحب شهري أكبر من صفر.";
    return;
  }

  const months = monthsToReachGoal(goal, monthly, returnPct);
  const cappedMonths = Math.min(months, 600); // سقف أمان 50 سنة لمنع حلقات غير واقعية
  const schedule = buildFundSchedule(monthly, returnPct, cappedMonths);
  const final = schedule[schedule.length - 1];
  const totalContributed = monthly * cappedMonths;
  const growth = final.balance - totalContributed;

  const badge = document.getElementById("fundBadge");
  const text = document.getElementById("fundVerdictText");
  const years = (cappedMonths / 12).toFixed(1);
  if (months <= 600) {
    badge.textContent = "قابل للتحقيق";
    badge.className = "verdict-badge safe";
    text.textContent = `تقدر توصل لهدفك خلال ${cappedMonths} شهر تقريبًا (${years} سنة) بسحب ${monthly.toLocaleString()} ريال/شهر.`;
  } else {
    badge.textContent = "يحتاج تعديل";
    badge.className = "verdict-badge risk";
    text.textContent = `بهذا السحب الشهري، الهدف بياخذ وقت طويل جدًا — جرّب ترفع مبلغ السحب.`;
  }

  document.getElementById("fundProgressBar").style.width = "100%";
  document.getElementById("fundProgressLabel").textContent = `الرصيد النهائي المتوقع: ${Math.round(final.balance).toLocaleString()} ريال`;

  document.getElementById("fundStats").innerHTML = `
    <div class="stat"><span class="stat-val">${cappedMonths}</span><span class="stat-lbl">شهر حتى الهدف</span></div>
    <div class="stat"><span class="stat-val">${Math.round(totalContributed).toLocaleString()}</span><span class="stat-lbl">إجمالي السحب (ريال)</span></div>
    <div class="stat"><span class="stat-val">${Math.round(growth).toLocaleString()}</span><span class="stat-lbl">عائد الاستثمار (ريال)</span></div>`;

  const shown = schedule.slice(0, 24);
  let rowsHtml = shown.map(r => `
    <tr><td>${r.month}</td><td>${monthly.toLocaleString()} ريال</td>
    <td>${Math.round(r.contributed).toLocaleString()} ريال</td>
    <td>${Math.round(r.balance).toLocaleString()} ريال</td></tr>`).join("");
  if (schedule.length > 24) {
    rowsHtml += `<tr><td colspan="4">... و ${schedule.length - 24} شهر إضافي حتى الهدف</td></tr>`;
  }
  document.getElementById("fundSchedule").innerHTML = `
    <table><thead><tr><th>#</th><th>السحب الشهري</th><th>إجمالي المسحوب</th><th>الرصيد مع العائد</th></tr></thead>
    <tbody>${rowsHtml}</tbody></table>`;
}

document.getElementById("fundRun").addEventListener("click", runFund);
window.addEventListener("load", runFund);

/* ============================================================
   ٤. تصنيف المعاملات
   ============================================================ */
const ICONS = { "مطاعم":"🍔","وقود":"⛽","تسوق":"🛍️","سوبرماركت":"🛒","كهرباء":"⚡","اتصالات":"📱","صحة":"🏥","ترفيه":"🎬","أثاث":"🛋️","إلكترونيات":"💻","ملابس":"👕","مواد غذائية":"🥦","أجهزة":"🔌","خدمات":"🧰","غير محدد":"❓" };

/* مولّد من merchant_map.py (عبدالله) — مصدر واحد للحقيقة، مطابق main.py حرفيًا.
   مطابقة احتواء (contains) مرتّبة بالطول، مو تطابق تام — يحل مشكلة
   "محطة بترومين" لا تطابق "بترومين". القاموس بـ 8 فئات أساسية فقط،
   لأنه مبني على نفس البيانات اللي دُرّب عليها نموذج التصنيف الحقيقي. */
const MERCHANT_MAP = {
  "لولو هايبر": "سوبرماركت", "سوق الظهران": "سوبرماركت", "كارفور": "سوبرماركت",
  "دانوب": "سوبرماركت", "العثيم": "سوبرماركت", "التميمي": "سوبرماركت",
  "بنده": "سوبرماركت", "لولو": "سوبرماركت", "المزرعة": "سوبرماركت",
  "مطعم الأهرام": "مطاعم", "ماكدونالدز": "مطاعم", "برجر كنج": "مطاعم",
  "ستاربكس": "مطاعم", "دانكن": "مطاعم", "الطازج": "مطاعم", "هرفي": "مطاعم",
  "البيك": "مطاعم", "كودو": "مطاعم", "كافيه": "مطاعم", "مطعم": "مطاعم",
  "محطة بترومين": "وقود", "بترومين": "وقود", "أرامكو": "وقود", "ساسكو": "وقود",
  "النقل": "وقود", "بنزين": "وقود", "محطة": "وقود",
  "شركة الكهرباء": "كهرباء", "الكهرباء": "كهرباء", "SEC": "كهرباء",
  "موبايلي": "اتصالات", "STC": "اتصالات", "زين": "اتصالات", "سلامة": "اتصالات",
  "مستشفى الحبيب": "صحة", "مستشفى": "صحة", "النهدي": "صحة", "الدواء": "صحة",
  "صيدلية": "صحة", "مجمع طبي": "صحة", "عيادة": "صحة",
  "أمازون": "تسوق", "نون": "تسوق", "شي إن": "تسوق", "اكسترا": "تسوق",
  "جرير": "تسوق", "ايكيا": "تسوق", "الدانوب هوم": "تسوق",
  "نتفلكس": "ترفيه", "شاهد": "ترفيه", "موسيقى": "ترفيه", "سينما": "ترفيه",
  "vox": "ترفيه", "ملاهي": "ترفيه",
};

function classifyMerchant(merchant) {
  const m = (merchant || "").trim().toLowerCase();
  if (!m) return "غير محدد";
  const keys = Object.keys(MERCHANT_MAP).sort((a, b) => b.length - a.length);
  for (const k of keys) {
    if (m.includes(k.toLowerCase())) return MERCHANT_MAP[k];
  }
  return "غير محدد";
}

function bucket(a) {
  if (a < 100) return "منخفض";
  if (a < 300) return "متوسط-منخفض";
  if (a < 600) return "متوسط";
  if (a < 1000) return "مرتفع";
  return "عالي";
}

function localClassify(merchant, amount) {
  const cat = classifyMerchant(merchant);
  return { merchant, amount, category: cat, icon: ICONS[cat] || "💳", confidence: "تجريبي", bucket: bucket(amount) };
}

document.getElementById("clsRun").addEventListener("click", async () => {
  const merchant = document.getElementById("clsMerchant").value.trim() || "غير معروف";
  const amount = +document.getElementById("clsAmount").value || 0;
  const box = document.getElementById("clsResult");
  box.innerHTML = `<p class="muted">جاري التصنيف…</p>`;

  let result;
  try {
    if (!apiAvailable) throw new Error("skip");
    result = await apiPost("/classify", { merchant, amount, type: "شراء", payment_method: "مدى", description: "" });
  } catch (e) {
    result = localClassify(merchant, amount);
  }

  box.innerHTML = `
    <div class="result-card">
      <div class="result-icon">${result.icon}</div>
      <div>
        <div class="result-cat">${result.category}</div>
        <div class="result-conf">الثقة: ${result.confidence} · فئة المبلغ: ${result.bucket}</div>
      </div>
    </div>`;
});

/* ============================================================
   ٥. أرقام سريعة في الهيرو (تجميلية، من بيانات تقديرية)
   ============================================================ */
(function heroFigures() {
  const scoreEl = document.getElementById("figScore");
  const txEl = document.getElementById("figTx");
  const targetScore = 78, targetTx = 200000;
  let i = 0;
  const steps = 40;
  const timer = setInterval(() => {
    i++;
    scoreEl.textContent = Math.round((targetScore / steps) * i);
    txEl.textContent = Math.round((targetTx / steps) * i).toLocaleString();
    if (i >= steps) {
      scoreEl.textContent = targetScore;
      txEl.textContent = targetTx.toLocaleString();
      clearInterval(timer);
    }
  }, 30);
})();

/* رسم أولي للمخطط عند تحميل الصفحة بقيم افتراضية */
window.addEventListener("load", runTwin);
