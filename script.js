const useLocationBtn = document.getElementById("useLocationBtn");
const checkBtn = document.getElementById("checkBtn");
const quickLocation = document.getElementById("quickLocation");
const latInput = document.getElementById("latInput");
const lonInput = document.getElementById("lonInput");

const statusText = document.getElementById("statusText");
const locationDetails = document.getElementById("locationDetails");

function setStatus(text) {
  statusText.innerText = text;
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatValue(value, fallback = "--") {
  if (value === null || value === undefined || Number.isNaN(value)) return fallback;
  return value;
}

function formatNumber(value, decimals = 1, fallback = "--") {
  const number = Number(value);
  if (!Number.isFinite(number)) return fallback;
  return number.toFixed(decimals).replace(/\.0$/, "");
}

function getSelectedLocation() {
  const [lat, lon, ...nameParts] = quickLocation.value.split(",");

  return {
    lat: Number(lat),
    lon: Number(lon),
    name: nameParts.join(",").trim() || "Selected Location"
  };
}

function getConfidence(rainChance, rainAmount) {
  if (rainChance >= 75 || rainAmount >= 10) return "High";
  if (rainChance >= 45 || rainAmount >= 3) return "Moderate";
  return "Low";
}

function getSafeWindow(rainChance) {
  if (rainChance >= 70) return "Avoid outdoor work";
  if (rainChance >= 40) return "Work carefully";
  return "Mostly safe";
}

function renderAdvice(rainChance, rainAmount, temp) {
  const adviceList = document.getElementById("adviceList");

  const advice = [];

  if (rainChance >= 70) {
    advice.push("High rain possibility. Avoid pesticide spraying and fertilizer application.");
    advice.push("Check drainage in vegetable fields and lowland areas.");
  } else if (rainChance >= 40) {
    advice.push("Moderate rain possibility. Complete urgent field work early.");
    advice.push("Delay chemical spraying if clouds are increasing.");
  } else {
    advice.push("Low rain possibility. Irrigation may be needed for dry fields.");
    advice.push("Good window for harvesting, drying, and spraying if wind is calm.");
  }

  if (rainAmount >= 10) {
    advice.push("Heavy rainfall expected. Protect seedlings and avoid waterlogging.");
  }

  if (Number(temp) >= 34) {
    advice.push("High temperature. Irrigate sensitive crops and avoid midday field work.");
  }

  adviceList.innerHTML = advice.map(item => `<div class="advice-item">${escapeHTML(item)}</div>`).join("");
}

function renderHourly(hourly) {
  const chart = document.getElementById("hourlyChart");
  chart.innerHTML = "";

  const now = new Date();
  let count = 0;

  for (let i = 0; i < hourly.time.length; i++) {
    const time = new Date(hourly.time[i]);
    if (time < now) continue;

    const hour = time.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit"
    });

    const temp = hourly.temperature_2m[i];
    const rainChance = hourly.precipitation_probability[i] || 0;
    const rainAmount = hourly.precipitation[i] || 0;

    const barHeight = Math.max(4, rainChance);

    const column = document.createElement("div");
    column.className = "chart-column";

    column.innerHTML = `
      <div class="temp-label">🌡️ ${temp}°C</div>

      <div class="bar-wrap">
        <div class="rain-bar" style="height:${barHeight}%"></div>
      </div>

      <div class="rain-label">🌧️ ${rainChance}%</div>
      <div class="rain-label">${rainAmount} mm</div>
      <div class="time-label">${hour}</div>
    `;

    chart.appendChild(column);

    count++;
    if (count >= 12) break;
  }
}

function renderDaily(daily) {
  const chart = document.getElementById("dailyChart");
  chart.innerHTML = "";

  for (let i = 0; i < daily.time.length; i++) {
    const date = new Date(daily.time[i]);

    const label = date.toLocaleDateString([], {
      weekday: "short",
      month: "short",
      day: "numeric"
    });

    const rainChance = daily.precipitation_probability_max[i] || 0;
    const rainAmount = daily.precipitation_sum[i] || 0;
    const maxTemp = daily.temperature_2m_max[i];
    const minTemp = daily.temperature_2m_min[i];

    const barHeight = Math.max(4, rainChance);

    const column = document.createElement("div");
    column.className = "chart-column week-column";

    column.innerHTML = `
      <div class="temp-label">🌡️ ${minTemp}° / ${maxTemp}°C</div>

      <div class="bar-wrap">
        <div class="rain-bar" style="height:${barHeight}%"></div>
      </div>

      <div class="rain-label">🌧️ ${rainChance}%</div>
      <div class="rain-label">${rainAmount} mm</div>
      <div class="time-label">${label}</div>
    `;

    chart.appendChild(column);
  }
}



async function checkRain(lat, lon, name = "Selected Location") {
  try {
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
      setStatus("Please enter a valid latitude and longitude.");
      return;
    }

    setStatus("Loading forecast...");

    const url =
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}` +
      `&current=temperature_2m,relative_humidity_2m,precipitation,rain` +
      `&hourly=temperature_2m,precipitation_probability,precipitation` +
      `&daily=precipitation_probability_max,precipitation_sum,temperature_2m_max,temperature_2m_min` +
      `&timezone=auto`;

    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Weather request failed with status ${response.status}`);
    }

    const data = await response.json();

    const rainChance = Number(data.daily?.precipitation_probability_max?.[0] ?? 0);
    const rainAmount = Number(data.daily?.precipitation_sum?.[0] ?? 0);
    const currentTempRaw = data.current?.temperature_2m ?? data.current_weather?.temperature ?? data.hourly?.temperature_2m?.[0];
    const currentTemp = formatNumber(currentTempRaw, 1);

    document.getElementById("placeName").innerText = name;
    locationDetails.innerText = `${name} · Latitude: ${Number(lat).toFixed(4)}, Longitude: ${Number(lon).toFixed(4)}`;

    document.getElementById("heroRain").innerText = `${rainChance}%`;
    document.getElementById("heroTemp").innerText = `Temperature: ${currentTemp}°C`;

    document.getElementById("rainProbability").innerText = `${rainChance}%`;
    document.getElementById("currentTemp").innerText = `${currentTemp}°C`;
    document.getElementById("rainAmount").innerText = `${rainAmount} mm`;

    document.getElementById("rainSummary").innerText =
      `Current temperature is ${currentTemp}°C. Rain chance today is ${rainChance}%, with expected rainfall of ${rainAmount} mm.`;

    document.getElementById("safeWindow").innerText = getSafeWindow(rainChance);
    document.getElementById("confidence").innerText = getConfidence(rainChance, rainAmount);

    renderAdvice(rainChance, rainAmount, currentTemp);
    renderHourly(data.hourly);
    renderDaily(data.daily);

    setStatus("Forecast updated.");
  } catch (error) {
    console.error(error);
    setStatus("Could not load forecast. Please try again.");
  }
}

async function getLocationName(lat, lon) {
  try {
    const url = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`;
    const response = await fetch(url);
    if (!response.ok) return "Your Location";

    const data = await response.json();
    return data.city || data.locality || data.principalSubdivision || data.countryName || "Your Location";
  } catch (error) {
    return "Your Location";
  }
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    checkRain(27.7172, 85.3240, "Kathmandu");
    return;
  }

  setStatus("Getting your location...");

  navigator.geolocation.getCurrentPosition(
    async position => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;

      latInput.value = lat.toFixed(4);
      lonInput.value = lon.toFixed(4);

      const locationName = await getLocationName(lat, lon);
      checkRain(lat, lon, locationName);
    },
    () => {
      setStatus("Location permission denied. Showing Kathmandu forecast.");
      checkRain(27.7172, 85.3240, "Kathmandu");
    },
    {
      enableHighAccuracy: true,
      timeout: 10000
    }
  );
}

useLocationBtn.addEventListener("click", useCurrentLocation);

checkBtn.addEventListener("click", () => {
  const lat = Number(latInput.value);
  const lon = Number(lonInput.value);

  checkRain(lat, lon, "Manual Location");
});

quickLocation.addEventListener("change", () => {
  const { lat, lon, name } = getSelectedLocation();

  latInput.value = lat.toFixed(4);
  lonInput.value = lon.toFixed(4);

  checkRain(lat, lon, name);
});

window.addEventListener("load", () => {
  const { lat, lon, name } = getSelectedLocation();
  checkRain(lat, lon, name);
});


/* ---------------- AKC NOTICES ---------------- */

const noticesContainer = document.getElementById("noticesContainer");
const noticeSearch = document.getElementById("noticeSearch");

const BS_MONTH_DAYS = [31, 31, 32, 32, 31, 30, 30, 29, 30, 29, 30, 30];

function bsToNumber(bsDate) {
  if (!bsDate || !String(bsDate).includes("-")) return null;

  const [y, m, d] = String(bsDate).split("-").map(Number);

  if (!y || !m || !d || m < 1 || m > 12 || d < 1 || d > 32) return null;

  const daysBeforeMonth = BS_MONTH_DAYS.slice(0, m - 1).reduce((sum, days) => sum + days, 0);
  return y * 365 + daysBeforeMonth + d;
}

function formatListItem(item) {
  if (item && typeof item === "object") {
    const values = Object.values(item).filter(Boolean);
    return values.length ? values.join(": ") : JSON.stringify(item);
  }

  return item;
}
function listItems(items) {
  if (!items || items.length === 0) {
    return "<p class='empty-text'>Not mentioned.</p>";
  }

  return `
    <ul class="detail-list">
      ${items.map(item => `<li>${item}</li>`).join("")}
    </ul>
  `;
}
function latestPublishedNumber(notices) {
  const dates = notices
    .map(n => bsToNumber(n.published_date))
    .filter(Boolean);

  return dates.length ? Math.max(...dates) : null;
}

function isClosedDeadline(value) {
  return /closed|expired|समाप्त|बन्द/i.test(String(value || ""));
}

function isContinuousDeadline(value) {
  return /continuous|ongoing|open|निरन्तर/i.test(String(value || ""));
}

function getDeadlineInfo(deadline, latestDateNumber) {
  const deadlineText = String(deadline || "").trim();

  if (!deadlineText) {
    return { state: "none", daysLeft: null };
  }

  if (isClosedDeadline(deadlineText)) {
    return { state: "expired", daysLeft: null };
  }

  if (isContinuousDeadline(deadlineText)) {
    return { state: "active", daysLeft: null };
  }

  const deadlineNumber = bsToNumber(deadlineText);

  if (!deadlineNumber || !latestDateNumber) {
    return { state: "none", daysLeft: null };
  }

  const daysLeft = deadlineNumber - latestDateNumber;
  return {
    state: daysLeft >= 0 ? "active" : "expired",
    daysLeft
  };
}

function normalizeNotice(notice) {
  return {
    ...notice,
    published_date: notice.published_date || notice.date || "",
    deadline: notice.deadline || notice.deadline_ai || "",
    pdf_url: notice.pdf_url || notice.link || "",
    source: notice.source || "",
    summary: notice.summary || "Summary not available for this notice.",
    details: notice.details || "",
    plain_explanation: notice.plain_explanation || notice.details || "",
    eligibility: notice.eligibility || [],
    required_documents: notice.required_documents || [],
    benefits: notice.benefits || [],
    application_process: notice.application_process || [],
    important_points: notice.important_points || [],
    contact_information: notice.contact_information || []
  };
}

function renderNotices(notices) {
  const normalizedNotices = notices
    .map(normalizeNotice)
    .sort((a, b) => (bsToNumber(b.published_date) || 0) - (bsToNumber(a.published_date) || 0));
  const latest = latestPublishedNumber(normalizedNotices);

  let activeCount = 0;
  let expiredCount = 0;

  noticesContainer.innerHTML = normalizedNotices.map(notice => {
    const deadline = notice.deadline_ai || notice.deadline || "";
    const deadlineInfo = getDeadlineInfo(deadline, latest);

    let deadlineClass = "neutral-notice";
    let clock = "";
    let badgeClass = "badge-neutral";
    let badgeText = "NO DEADLINE";

    if (deadlineInfo.state === "active") {
      activeCount++;
      deadlineClass = "active-notice";
      badgeClass = "badge-active";
      badgeText = "ACTIVE";
      clock = deadlineInfo.daysLeft === null
        ? `<div class="deadline-clock active-deadline">⏰ Open / continuous</div>`
        : `<div class="deadline-clock active-deadline">⏰ ${deadlineInfo.daysLeft} day(s) left</div>`;
    } else if (deadlineInfo.state === "expired") {
      expiredCount++;
      deadlineClass = "expired-notice";
      badgeClass = "badge-closed";
      badgeText = "EXPIRED";
      clock = `<div class="deadline-clock expired-deadline">⏰ Deadline expired</div>`;
    }

    return `
      <article class="notice-card ${deadlineClass}">
        <div class="notice-top">
          <span class="notice-badge ${badgeClass}">
            ${badgeText}
          </span>
          <span class="notice-badge badge-new">LAST 30 DAYS</span>
        </div>

        <h3>${escapeHTML(notice.title || "Untitled Notice")}</h3>

        <div class="notice-meta">
          <span>Published: <strong>${escapeHTML(notice.published_date || "N/A")}</strong></span>
          <span>Deadline: <strong>${escapeHTML(deadline || "Not mentioned")}</strong></span>
        </div>

        ${clock}

        <div class="ai-summary">
          <strong>AI Summary</strong>
          <p>${escapeHTML(notice.summary || "Summary not available.")}</p>
        </div>

        
		<details class="notice-details">
  <summary>View organized details</summary>

  <div class="details-grid">
    <section class="detail-box highlight-box">
      <h4>Plain Explanation</h4>
      <p>${notice.plain_explanation || notice.details || "No detailed explanation available."}</p>
    </section>

    <section class="detail-box">
      <h4>Who Can Apply</h4>
      ${listItems(notice.eligibility)}
    </section>

    <section class="detail-box">
      <h4>Required Documents</h4>
      ${listItems(notice.required_documents)}
    </section>

    <section class="detail-box">
      <h4>Benefits / Support</h4>
      ${listItems(notice.benefits)}
    </section>

    <section class="detail-box">
      <h4>Application Process</h4>
      ${listItems(notice.application_process)}
    </section>

    <section class="detail-box">
      <h4>Important Points</h4>
      ${listItems(notice.important_points || notice.important_dates)}
    </section>

    <section class="detail-box">
      <h4>Contact Information</h4>
      ${listItems(notice.contact_information)}
    </section>

    <section class="detail-box raw-box">
      <h4>Extracted Text Preview</h4>
      <p>${notice.details || "No extracted text preview available."}</p>
    </section>
  </div>
</details>
		
		

        <div class="notice-links">
          ${notice.pdf_url ? `<a href="${escapeHTML(notice.pdf_url)}" target="_blank" rel="noopener">Original File</a>` : ""}
          ${notice.source ? `<a class="source-link" href="${escapeHTML(notice.source)}" target="_blank" rel="noopener">Source</a>` : ""}
        </div>
      </article>
    `;
  }).join("");

  document.getElementById("totalNotices").innerText = normalizedNotices.length;
  document.getElementById("activeNotices").innerText = activeCount;
  document.getElementById("expiredNotices").innerText = expiredCount;

  if (normalizedNotices.length === 0) {
    noticesContainer.innerHTML = "<p>No notices found for the latest 30-day period.</p>";
  }
}

fetch("notices.json")
  .then(response => {
    if (!response.ok) {
      throw new Error(`Notice request failed with status ${response.status}`);
    }

    return response.json();
  })
  .then(allNotices => {
    const normalizedNotices = allNotices.map(normalizeNotice);
    const latest = latestPublishedNumber(normalizedNotices);

    const recentOnly = normalizedNotices.filter(notice => {
      const published = bsToNumber(notice.published_date);
      return published && latest && latest - published <= 30;
    });

    renderNotices(recentOnly);

    noticeSearch.addEventListener("input", () => {
      const q = noticeSearch.value.toLowerCase();

      const filtered = recentOnly.filter(notice =>
        JSON.stringify(notice).toLowerCase().includes(q)
      );

      renderNotices(filtered);
    });
  })
  .catch(error => {
    console.error(error);
    noticesContainer.innerHTML = "Could not load notices.json";
  });
