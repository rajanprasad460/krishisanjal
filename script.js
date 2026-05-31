const quickLocation = document.getElementById('quickLocation');
const latInput = document.getElementById('latInput');
const lonInput = document.getElementById('lonInput');
const checkBtn = document.getElementById('checkBtn');
const useLocationBtn = document.getElementById('useLocationBtn');
const statusText = document.getElementById('statusText');
const locationDetails = document.getElementById('locationDetails');

const placeName = document.getElementById('placeName');
const rainProbability = document.getElementById('rainProbability');
const heroRain = document.getElementById('heroRain');
const rainSummary = document.getElementById('rainSummary');
const rainAmount = document.getElementById('rainAmount');
const safeWindow = document.getElementById('safeWindow');
const confidence = document.getElementById('confidence');
const adviceList = document.getElementById('adviceList');
const hourlyList = document.getElementById('hourlyList');
const dailyList = document.getElementById('dailyList');

quickLocation.addEventListener('change', () => {
  const [lat, lon] = quickLocation.value.split(',');
  latInput.value = lat;
  lonInput.value = lon;
});

checkBtn.addEventListener('click', async () => {
  const selected = quickLocation.value.split(',');
  const selectedName = selected.slice(2).join(', ');
  const lat = Number(latInput.value);
  const lon = Number(lonInput.value);

  const place = selectedName
    ? { name: selectedName, fullName: selectedName }
    : await reverseGeocode(lat, lon);

  fetchForecast(lat, lon, place.name || 'Selected Location', place);
});

useLocationBtn.addEventListener('click', () => {
  if (!navigator.geolocation) {
    statusText.textContent = 'GPS location is not supported by this browser.';
    return;
  }

  statusText.textContent = 'Getting your location...';
  navigator.geolocation.getCurrentPosition(
    async position => {
      const lat = Number(position.coords.latitude.toFixed(5));
      const lon = Number(position.coords.longitude.toFixed(5));
      latInput.value = lat;
      lonInput.value = lon;

      statusText.textContent = 'Finding your location name...';
      const place = await reverseGeocode(lat, lon);
      fetchForecast(lat, lon, place.name || 'Your Current Location', place);
    },
    () => {
      statusText.textContent = 'Location permission denied. Please enter latitude and longitude manually.';
    }
  );
});


async function reverseGeocode(lat, lon) {
  if (!lat || !lon) {
    return { name: 'Selected Location', fullName: 'Location name unavailable' };
  }

  const url = new URL('https://nominatim.openstreetmap.org/reverse');
  url.searchParams.set('format', 'jsonv2');
  url.searchParams.set('lat', lat);
  url.searchParams.set('lon', lon);
  url.searchParams.set('zoom', '12');
  url.searchParams.set('addressdetails', '1');

  try {
    const response = await fetch(url.toString(), {
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) throw new Error('Reverse geocoding failed');
    const data = await response.json();
    const address = data.address || {};

    const localName =
      address.city ||
      address.town ||
      address.village ||
      address.municipality ||
      address.county ||
      address.state_district ||
      data.name ||
      'Detected Location';

    const district = address.county || address.state_district || '';
    const province = address.state || '';
    const country = address.country || '';
    const fullName = [localName, district, province, country].filter(Boolean).join(', ');

    return {
      name: localName,
      fullName: fullName || data.display_name || 'Detected Location'
    };
  } catch (error) {
    console.warn(error);
    return {
      name: 'Your Current Location',
      fullName: 'Location name unavailable. Forecast is still based on your GPS coordinates.'
    };
  }
}

function renderLocationDetails(lat, lon, place) {
  if (!locationDetails) return;

  const name = place?.fullName || place?.name || 'Location name not available';
  locationDetails.innerHTML = `
    <strong>📍 ${name}</strong><br>
    Latitude: ${Number(lat).toFixed(5)} · Longitude: ${Number(lon).toFixed(5)}
  `;
}

async function fetchForecast(lat, lon, name, place = null) {
  if (!lat || !lon) {
    statusText.textContent = 'Please enter valid latitude and longitude.';
    return;
  }

  statusText.textContent = 'Fetching rain forecast...';
  renderLocationDetails(lat, lon, place);

  const params = new URLSearchParams({
    latitude: lat,
    longitude: lon,
    timezone: 'auto',
    forecast_days: 7,
    hourly: 'precipitation_probability,precipitation,temperature_2m,relative_humidity_2m',
    daily: 'precipitation_probability_max,precipitation_sum'
  });

  try {
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params}`);
    if (!response.ok) throw new Error('Forecast request failed');
    const data = await response.json();
    renderForecast(data, name);
    statusText.textContent = `Forecast updated for ${name}.`;
    renderLocationDetails(lat, lon, place);
  } catch (error) {
    console.error(error);
    statusText.textContent = 'Could not fetch forecast. Please try again later.';
  }
}

function renderForecast(data, name) {
  const todayProb = Math.round(data.daily.precipitation_probability_max[0] ?? 0);
  const todayRain = Number(data.daily.precipitation_sum[0] ?? 0).toFixed(1);

  placeName.textContent = name;
  rainProbability.textContent = `${todayProb}%`;
  heroRain.textContent = `${todayProb}%`;
  rainAmount.textContent = `${todayRain} mm`;

  const confidenceText = getConfidence(todayProb, todayRain);
  confidence.textContent = confidenceText;

  const likelyHours = getLikelyRainHours(data.hourly);
  safeWindow.textContent = likelyHours.length ? 'Before rain window' : 'Most of day';
  rainSummary.textContent = likelyHours.length
    ? `Rain is more likely around ${likelyHours[0]} to ${likelyHours[likelyHours.length - 1]}.`
    : 'Low rain signal for today based on current forecast.';

  renderAdvice(todayProb, Number(todayRain), likelyHours);
  renderHourly(data.hourly);
  renderDaily(data.daily);
}

function getConfidence(prob, rain) {
  if (prob >= 70 && rain >= 5) return 'High';
  if (prob >= 45 || rain >= 2) return 'Medium';
  return 'Low';
}

function getLikelyRainHours(hourly) {
  const today = new Date().toISOString().slice(0, 10);
  const hours = [];

  hourly.time.forEach((time, index) => {
    if (!time.startsWith(today)) return;
    const probability = hourly.precipitation_probability[index] ?? 0;
    const rain = hourly.precipitation[index] ?? 0;
    if (probability >= 50 || rain > 0.5) {
      hours.push(formatHour(time));
    }
  });

  return hours;
}

function renderAdvice(prob, rain, likelyHours) {
  const advice = [];

  if (prob >= 70 || rain >= 8) {
    advice.push(['Avoid pesticide spraying today.', 'danger']);
    advice.push(['Irrigation is probably not required.', 'warn']);
    advice.push(['Protect harvested crops and stored grains.', 'danger']);
  } else if (prob >= 40 || rain >= 2) {
    advice.push(['Spray only if you can finish early and leaves can dry.', 'warn']);
    advice.push(['Delay irrigation until the next forecast update.', 'warn']);
    advice.push(['Field work is safer before the likely rain period.', '']);
  } else {
    advice.push(['Pesticide spraying is likely safer today, but avoid windy periods.', '']);
    advice.push(['Irrigation may be needed for water-sensitive crops.', 'warn']);
    advice.push(['Good day for harvesting if soil condition is suitable.', '']);
  }

  if (likelyHours.length) {
    advice.push([`Likely rain window: ${likelyHours[0]} - ${likelyHours[likelyHours.length - 1]}.`, 'warn']);
  }

  adviceList.innerHTML = advice.map(([text, type]) => `
    <div class="advice-item">
      <span>${text}</span>
      <span class="badge ${type}">${type === 'danger' ? 'High Risk' : type === 'warn' ? 'Caution' : 'OK'}</span>
    </div>
  `).join('');
}

function renderHourly(hourly) {
  const today = new Date().toISOString().slice(0, 10);
  const rows = hourly.time
    .map((time, index) => ({
      time,
      probability: hourly.precipitation_probability[index] ?? 0,
      rain: hourly.precipitation[index] ?? 0
    }))
    .filter(row => row.time.startsWith(today))
    .filter((_, index) => index % 2 === 0)
    .slice(0, 12);

  hourlyList.innerHTML = rows.map(row => {
    const risk = row.probability >= 70 || row.rain > 2 ? 'danger' : row.probability >= 40 || row.rain > 0.3 ? 'warn' : '';
    return `
      <div class="hour-row">
        <strong>${formatHour(row.time)}</strong>
        <span>${Math.round(row.probability)}% chance · ${Number(row.rain).toFixed(1)} mm</span>
        <span class="badge ${risk}">${risk === 'danger' ? 'Rain likely' : risk === 'warn' ? 'Possible' : 'Low'}</span>
      </div>
    `;
  }).join('');
}

function renderDaily(daily) {
  dailyList.innerHTML = daily.time.map((date, index) => {
    const prob = Math.round(daily.precipitation_probability_max[index] ?? 0);
    const rain = Number(daily.precipitation_sum[index] ?? 0).toFixed(1);
    const risk = prob >= 70 || rain > 8 ? 'danger' : prob >= 40 || rain > 2 ? 'warn' : '';
    return `
      <div class="day-row">
        <strong>${formatDate(date)}</strong>
        <span>${prob}% chance · ${rain} mm</span>
        <span class="badge ${risk}">${risk === 'danger' ? 'Wet' : risk === 'warn' ? 'Watch' : 'Dry'}</span>
      </div>
    `;
  }).join('');
}

function formatHour(time) {
  return new Date(time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

function formatDate(date) {
  return new Date(date).toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' });
}

fetchForecast(27.7172, 85.3240, 'Kathmandu');
