const FC_COLORS = { LOW: '#27ae60', MEDIUM: '#f39c12', HIGH: '#e74c3c' };
const FC_TEXT = {
  LOW: 'No Alert-level flooding is expected at Hanwella or Glencourse tomorrow.',
  MEDIUM: 'Water is close to the Alert level (80% or more). No flood is forecast yet, but keep watching.',
  HIGH: 'Alert level is forecast to be reached, or is already exceeded, at Hanwella or Glencourse.'
};

let fcData = null, fcChart = null;

// 1. FLOOD FORECAST LOGIC
// Fetch forecast data from the backend API
async function loadForecast() {
  const err = document.getElementById('fc-error');
  try {
    const res = await fetch('/api/forecast/live'); 
    if (!res.ok) throw new Error('HTTP ' + res.status);
    fcData = await res.json();
    renderLiveForecast();
    if(err) err.style.display = 'none';
  } catch (e) {
    console.error("Forecast load error:", e);
    if(err) {
        err.style.display = 'block';
        err.textContent = 'Could not load the forecast: ' + e.message;
    }
  }
}

// Render the forecast table, chart, and risk level badge

function renderLiveForecast() {
  const days = fcData.days;
  if (!days || days.length === 0) return;
    // Get the latest day's forecast
  const latestDay = days[days.length - 1];
  
  const lvl = document.getElementById('fc-level');
  if (lvl) {
    lvl.textContent = latestDay.risk_level;
    lvl.className = 'fc-level-badge fc-level-' + latestDay.risk_level;
  }
  
  const setTxt = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
  
  setTxt('fc-forecast-for', 'Forecast made on ' + latestDay.date + ' for ' + latestDay.forecast_for);
  setTxt('fc-prob', (latestDay.flood_probability * 100).toFixed(0) + '%');
  setTxt('fc-h-gauge', latestDay.hanwella_wl + ' m (Alert 7.0 m)');
  setTxt('fc-g-gauge', latestDay.glencourse_wl + ' m (Alert 15.0 m)');
  setTxt('fc-q', latestDay.hanwella_q + ' m³/s');
  setTxt('fc-rain', (latestDay.s01_wl * 100).toFixed(1) + ' cm'); 
  setTxt('fc-explain', FC_TEXT[latestDay.risk_level]);
  
    // Build the forecast table body
  const tbody = document.getElementById('fc-tbody');
  if (tbody) {
    tbody.innerHTML = days.map(d => {
        const alertStatus = (d.risk_level === 'HIGH' || d.risk_level === 'MEDIUM')
            ? '<span style="color:#e74c3c; font-weight:bold;">Yes (Predicted)</span>' 
            : 'No';

        // Convert S01 water level from metres to centimetres
        const s01_cm = d.s01_wl ? (d.s01_wl * 100).toFixed(1) : 0;

        return `
        <tr class="fc-row">
            <td>${d.forecast_for}</td>
            <td><span class="fc-pill fc-pill-${d.risk_level}">${d.risk_level}</span></td>
            <td>${(d.flood_probability * 100).toFixed(0)}%</td>
            <td>${s01_cm}</td>
            <td>${d.s01_q}</td>
            <td>${d.hanwella_wl}</td>
            <td>${d.hanwella_q}</td>
            <td>${d.glencourse_wl}</td>
            <td>${d.glencourse_q}</td>
            <td>${alertStatus}</td>
        </tr>
        `;
    }).join('');
  }
  
    // Update the mode badge to show "LIVE FORECAST"
  const modeEl = document.getElementById('fc-mode');
  if (modeEl) {
      modeEl.textContent = 'LIVE FORECAST';
      modeEl.style.background = '#e0f7fa';
      modeEl.style.color = '#006064';
      modeEl.style.border = '1px solid #80deea';
  }

  // Chart line for s01
  const chartEl = document.getElementById('fc-chart');
  if (chartEl) {
      const labels = days.map(d => d.forecast_for || d.date);
      const hanwellaData = days.map(d => d.hanwella_wl);
      const glencourseData = days.map(d => d.glencourse_wl);
      // S01 value cm 
      const s01Data = days.map(d => d.s01_wl ? (d.s01_wl * 100).toFixed(1) : 0);
      
      if (fcChart) fcChart.destroy(); 
      
      fcChart = new Chart(chartEl, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Hanwella (m)',
                    data: hanwellaData,
                    borderColor: '#0056b3',
                    backgroundColor: 'rgba(0, 86, 179, 0.1)',
                    fill: true,
                    tension: 0.25,
                    yAxisID: 'y' 
                },
                {
                    label: 'Glencourse (m)',
                    data: glencourseData,
                    borderColor: '#8e44ad',
                    backgroundColor: 'rgba(142, 68, 173, 0.1)',
                    fill: true,
                    tension: 0.25,
                    yAxisID: 'y1' 
                },
                {
                    label: 'S01 (cm)',
                    data: s01Data,
                    borderColor: '#e67e22',
                    backgroundColor: 'rgba(230, 126, 34, 0.1)',
                    fill: false,
                    tension: 0.25,
                    yAxisID: 'y2' 
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            scales: {
                y: { type: 'linear', display: true, position: 'left', title: { display: true, text: 'Hanwella WL (m)' } },
                y1: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'Glencourse WL (m)' }, grid: { drawOnChartArea: false } },
                y2: { type: 'linear', display: true, position: 'right', title: { display: true, text: 'S01 (cm)' }, grid: { drawOnChartArea: false } } // S01 අක්ෂය
            }
        }
      });
  }
}

// GIS MAP LOGIC (Only for Forecast Page)
let forecastMapInstance = null;
let forecastGisLayer = null;

// Initialize the Leaflet map for the Forecast page
function initForecastMap() {
    const mapContainer = document.getElementById('gis-forecast-map');
    if (!mapContainer) {
        console.log("Waiting for gis-forecast-map div...");
        return;
    }

    if (forecastMapInstance !== null) {
        forecastMapInstance.invalidateSize();
        return;
    }
    // Create a new map instance centered on the Kelani Basin
    forecastMapInstance = L.map('gis-forecast-map').setView([6.94, 79.89], 11);
        // Add OpenStreetMap tile layer
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(forecastMapInstance);

    setTimeout(() => {
        forecastMapInstance.invalidateSize();
        fetchForecastGisData();
    }, 400);
}

// Fetch GIS risk data and draw colored circles on the map
async function fetchForecastGisData() {
    if (!forecastMapInstance) return;

    try {
        const res = await fetch('/api/forecast/gis');
        const data = await res.json();

        if (forecastGisLayer) {
            forecastMapInstance.removeLayer(forecastGisLayer);
        }
        
        forecastGisLayer = L.layerGroup().addTo(forecastMapInstance);

        data.areas.forEach(area => {
            let color = FC_COLORS.LOW;
            if (area.risk === 'MEDIUM') color = FC_COLORS.MEDIUM;
            if (area.risk === 'HIGH') color = FC_COLORS.HIGH;

            const circle = L.circle([area.lat, area.lon], {
                color: color,
                fillColor: color,
                fillOpacity: 0.4,
                radius: 3000, 
                weight: 2
            });

            circle.bindPopup(`
                <div style="text-align:center; font-family: 'Poppins', sans-serif;">
                    <h4 style="margin:0 0 5px 0; color:#2c3e50;">${area.ds_name}</h4>
                    <span style="background:${color}; color:white; padding:3px 10px; border-radius:10px; font-size:12px; font-weight:bold;">${area.risk} RISK</span>
                </div>
            `);
            
            circle.bindTooltip(`${area.ds_name} (${area.risk})`, {
                permanent: true, 
                direction: 'top', 
                className: 'gis-tooltip'
            });

            forecastGisLayer.addLayer(circle);
        });

        console.log("GIS Forecast Map loaded successfully!");

    } catch (e) {
        console.error("Forecast GIS Map load failed: ", e);
    }
}
// 3. EVENT LISTENERS
document.addEventListener('DOMContentLoaded', () => {
    // When the Forecast tab is clicked, load forecast and initialize map
  const link = document.querySelector('a[onclick="switchPage(\'forecast\')"]');
  if (link) {
      link.addEventListener('click', () => {
          loadForecast();
          setTimeout(initForecastMap, 500);
      });
  }
});