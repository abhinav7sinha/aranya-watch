"""FastAPI routes for aranya-watch."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.schemas import FireAlertRead
from app.services.fire_alerts import (
    get_alerts_in_bbox,
    get_alerts_within_radius,
    get_recent_alerts,
)
from app.services.live_firms import fetch_india_live_alerts
from app.services.preview_alerts import (
    get_preview_alerts_in_bbox,
    get_preview_alerts_within_radius,
    get_recent_preview_alerts,
)

router = APIRouter()
INDIA_BBOX = {
    "min_lat": 6.0,
    "max_lat": 37.5,
    "min_lon": 68.0,
    "max_lon": 97.5,
}


@router.get("/health")
def healthcheck(request: Request) -> dict[str, str | bool]:
    """Return service health information."""

    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "preview_mode": bool(getattr(request.app.state, "preview_mode", False)),
    }


@router.get("/alerts/recent", response_model=list[FireAlertRead])
def recent_alerts(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_db_session),
) -> list[FireAlertRead]:
    """Return the latest N fire alerts."""

    if getattr(request.app.state, "preview_mode", False):
        return get_recent_preview_alerts(limit=limit)

    alerts = get_recent_alerts(session=session, limit=limit)
    return [FireAlertRead.from_orm_with_risk(alert) for alert in alerts]


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    limit: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    """Render a minimal dashboard with recent alerts."""

    preview_mode = getattr(request.app.state, "preview_mode", False)
    alerts = (
        get_recent_preview_alerts(limit=limit)
        if preview_mode
        else [FireAlertRead.from_orm_with_risk(alert) for alert in get_recent_alerts(session=session, limit=limit)]
    )
    rows = "\n".join(
        [
            (
                "<tr>"
                f"<td>{alert.acq_datetime.isoformat()}</td>"
                f"<td>{alert.latitude:.4f}</td>"
                f"<td>{alert.longitude:.4f}</td>"
                f"<td>{alert.brightness:.1f}</td>"
                f"<td>{alert.confidence}</td>"
                f"<td>{alert.risk_score:.2f}</td>"
                "</tr>"
            )
            for alert in alerts
        ]
    )
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>aranya-watch Dashboard</title>
      <style>
        :root {{
          color-scheme: light;
          --bg: #f7f3ea;
          --panel: #fffdf8;
          --ink: #17261d;
          --muted: #53645b;
          --accent: #b94f2d;
          --border: #d9cbb6;
        }}
        body {{
          margin: 0;
          font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
          background: linear-gradient(180deg, #efe2c5 0%, var(--bg) 30%, #f5f2eb 100%);
          color: var(--ink);
        }}
        main {{
          max-width: 1100px;
          margin: 0 auto;
          padding: 48px 20px 64px;
        }}
        .hero {{
          margin-bottom: 24px;
        }}
        h1 {{
          margin: 0 0 8px;
          font-size: 2.5rem;
        }}
        p {{
          margin: 0;
          color: var(--muted);
        }}
        .panel {{
          background: rgba(255, 253, 248, 0.92);
          border: 1px solid var(--border);
          border-radius: 20px;
          overflow: hidden;
          box-shadow: 0 12px 40px rgba(32, 38, 35, 0.08);
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
        }}
        th, td {{
          padding: 14px 16px;
          text-align: left;
          border-bottom: 1px solid #eee4d6;
          font-size: 0.95rem;
        }}
        th {{
          background: #f8efe0;
          color: var(--ink);
        }}
        .accent {{
          color: var(--accent);
          font-weight: 700;
        }}
      </style>
    </head>
    <body>
      <main>
        <section class="hero">
          <h1>aranya-watch</h1>
          <p>Recent NASA FIRMS fire alerts with a simple heuristic risk score.</p>
          {"<p class='accent'>Preview mode is active. Showing sample alerts because the database is unavailable.</p>" if preview_mode else ""}
        </section>
        <section class="panel">
          <table>
            <thead>
              <tr>
                <th>Acquired</th>
                <th>Latitude</th>
                <th>Longitude</th>
                <th>Brightness</th>
                <th>Confidence</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>{rows or '<tr><td colspan="6">No alerts available.</td></tr>'}</tbody>
          </table>
        </section>
      </main>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/visualizer/india", response_class=HTMLResponse)
def india_visualizer(request: Request) -> HTMLResponse:
    """Render an India-focused fire monitoring map."""

    preview_mode = getattr(request.app.state, "preview_mode", False)
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>aranya-watch India Firewatch</title>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
      <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      <link rel="stylesheet" href="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css" />
      <style>
        :root {{
          color-scheme: light;
          --bg: #f6f0e6;
          --bg-deep: #ede4d6;
          --panel: rgba(255, 251, 245, 0.88);
          --panel-strong: rgba(255, 250, 244, 0.96);
          --border: rgba(58, 74, 60, 0.12);
          --ink: #14261d;
          --muted: #5d6f63;
          --forest: #184d3b;
          --accent: #d45c2d;
          --accent-soft: #f4ddcf;
          --signal-mid: #ebb84b;
          --ok: #5d9b69;
          --shadow: 0 24px 80px rgba(40, 46, 38, 0.12);
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          min-height: 100vh;
          font-family: "Manrope", sans-serif;
          color: var(--ink);
          background:
            radial-gradient(circle at 12% 14%, rgba(82, 141, 102, 0.16), transparent 24%),
            radial-gradient(circle at 88% 10%, rgba(215, 126, 84, 0.18), transparent 18%),
            linear-gradient(180deg, var(--bg) 0%, var(--bg-deep) 100%);
        }}
        .shell {{
          display: grid;
          grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
          min-height: 100vh;
        }}
        .sidebar {{
          position: relative;
          z-index: 1;
          padding: 28px 24px 24px;
          background: linear-gradient(180deg, rgba(250, 245, 238, 0.98), rgba(246, 239, 229, 0.92));
          border-right: 1px solid var(--border);
          backdrop-filter: blur(14px);
        }}
        .eyebrow {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 7px 12px;
          border-radius: 999px;
          background: rgba(24, 77, 59, 0.08);
          color: var(--forest);
          font-size: 0.78rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          font-weight: 700;
        }}
        h1 {{
          margin: 18px 0 10px;
          font-family: "Fraunces", serif;
          font-size: clamp(2.4rem, 5vw, 3.7rem);
          line-height: 1;
          letter-spacing: -0.04em;
        }}
        .lede {{
          margin: 0 0 22px;
          max-width: 28rem;
          color: var(--muted);
          font-size: 1.02rem;
          line-height: 1.72;
        }}
        .notice {{
          margin: 0 0 20px;
          padding: 14px 15px;
          border: 1px solid rgba(212, 92, 45, 0.16);
          border-radius: 18px;
          background: rgba(212, 92, 45, 0.06);
          color: #8c4326;
        }}
        .toggle-row {{
          display: flex;
          gap: 10px;
          margin-bottom: 18px;
        }}
        .toggle {{
          appearance: none;
          border: 1px solid var(--border);
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.7);
          color: var(--ink);
          padding: 10px 14px;
          font: inherit;
          font-size: 0.9rem;
          font-weight: 700;
          cursor: pointer;
          transition: 180ms ease;
        }}
        .toggle.active {{
          background: var(--forest);
          color: #f6f3ed;
          border-color: var(--forest);
          box-shadow: 0 14px 28px rgba(24, 77, 59, 0.18);
        }}
        .stats {{
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 14px;
          margin-bottom: 18px;
        }}
        .stat {{
          padding: 16px;
          border-radius: 20px;
          background: var(--panel);
          border: 1px solid var(--border);
          box-shadow: var(--shadow);
        }}
        .stat-label {{
          font-size: 0.82rem;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          color: var(--muted);
        }}
        .stat-value {{
          margin-top: 8px;
          font-size: 1.8rem;
          font-weight: 800;
          letter-spacing: -0.04em;
        }}
        .panel {{
          margin-top: 16px;
          padding: 18px;
          border-radius: 22px;
          background: var(--panel);
          border: 1px solid var(--border);
          box-shadow: var(--shadow);
        }}
        .panel h2 {{
          margin: 0 0 12px;
          font-size: 0.95rem;
          text-transform: uppercase;
          letter-spacing: 0.09em;
          color: var(--muted);
        }}
        .legend-item,
        .alert-row {{
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }}
        .legend-item + .legend-item,
        .alert-row + .alert-row {{
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid rgba(20, 38, 29, 0.08);
        }}
        .swatch {{
          width: 12px;
          height: 12px;
          border-radius: 999px;
          box-shadow: 0 0 20px currentColor;
        }}
        .map-wrap {{
          position: relative;
          min-height: 100vh;
          overflow: hidden;
          background: linear-gradient(180deg, #edf2eb 0%, #e4ece5 100%);
        }}
        #map {{
          position: absolute;
          inset: 0;
        }}
        .map-overlay {{
          pointer-events: none;
          position: absolute;
          inset: 0;
          background:
            radial-gradient(circle at 58% 42%, rgba(255, 255, 255, 0.02), rgba(17, 38, 29, 0.12)),
            linear-gradient(180deg, rgba(246, 240, 230, 0.04), rgba(20, 38, 29, 0.08));
        }}
        .hud {{
          position: absolute;
          right: 24px;
          top: 24px;
          max-width: 360px;
          padding: 18px;
          background: var(--panel-strong);
          border: 1px solid var(--border);
          border-radius: 22px;
          box-shadow: var(--shadow);
          backdrop-filter: blur(14px);
        }}
        .hud-title {{
          margin: 0 0 6px;
          font-size: 1rem;
          letter-spacing: 0.03em;
        }}
        .hud-copy {{
          margin: 0;
          color: var(--muted);
          line-height: 1.55;
          font-size: 0.93rem;
        }}
        .pill {{
          display: inline-flex;
          align-items: center;
          gap: 8px;
          margin-top: 14px;
          padding: 8px 12px;
          border-radius: 999px;
          background: var(--accent-soft);
          color: #8c4326;
          font-size: 0.8rem;
          font-weight: 700;
        }}
        .alert-meta {{
          color: var(--muted);
          font-size: 0.82rem;
        }}
        .alert-risk {{
          font-weight: 700;
          color: #985331;
        }}
        .footer-note {{
          margin-top: 16px;
          color: var(--muted);
          font-size: 0.82rem;
          line-height: 1.5;
        }}
        .maplibregl-popup-content {{
          background: rgba(255, 251, 245, 0.96);
          color: var(--ink);
          border: 1px solid var(--border);
          border-radius: 16px;
          box-shadow: var(--shadow);
        }}
        .maplibregl-popup-tip {{
          border-top-color: rgba(255, 251, 245, 0.96) !important;
        }}
        .popup-title {{
          margin: 0 0 8px;
          font-size: 1rem;
          font-weight: 700;
        }}
        .popup-meta {{
          margin: 4px 0;
          color: #44594d;
          font-size: 0.9rem;
        }}
        @media (max-width: 1080px) {{
          .shell {{
            grid-template-columns: 1fr;
          }}
          .sidebar {{
            min-height: auto;
            border-right: 0;
            border-bottom: 1px solid var(--border);
          }}
          .map-wrap {{
            min-height: 72vh;
          }}
          .hud {{
            left: 16px;
            right: 16px;
            top: 16px;
            max-width: none;
          }}
        }}
      </style>
    </head>
    <body>
      <div class="shell">
        <aside class="sidebar">
          <div class="eyebrow">India Firewatch</div>
          <h1>See India's fire signal at a glance.</h1>
          <p class="lede">
            A calmer, flatter India-first map with live NASA detections, clustered hotspots, and fast context for where fire activity is building.
          </p>
          {"<p class='notice'>Preview mode is active. The map is showing curated India sample detections because the database is unavailable.</p>" if preview_mode else ""}
          <div class="toggle-row">
            <button class="toggle active" id="mode-nasa">Live NASA</button>
            <button class="toggle" id="mode-platform">Platform API</button>
          </div>
          <section class="stats">
            <div class="stat">
              <div class="stat-label">Visible Alerts</div>
              <div class="stat-value" id="stat-count">0</div>
            </div>
            <div class="stat">
              <div class="stat-label">High Risk</div>
              <div class="stat-value" id="stat-high-risk">0</div>
            </div>
            <div class="stat">
              <div class="stat-label">Peak Risk</div>
              <div class="stat-value" id="stat-risk">0</div>
            </div>
            <div class="stat">
              <div class="stat-label">Data Source</div>
              <div class="stat-value" id="stat-source">--</div>
            </div>
          </section>
          <section class="panel">
            <h2>Signal Legend</h2>
            <div class="legend-item"><span><span class="swatch" style="display:inline-block;color:#67b06f;background:#67b06f;"></span> Lower risk</span><span class="alert-meta">0-40</span></div>
            <div class="legend-item"><span><span class="swatch" style="display:inline-block;color:#ebb84b;background:#ebb84b;"></span> Elevated</span><span class="alert-meta">41-70</span></div>
            <div class="legend-item"><span><span class="swatch" style="display:inline-block;color:#d45c2d;background:#d45c2d;"></span> Critical</span><span class="alert-meta">71-100</span></div>
          </section>
          <section class="panel">
            <h2>Recent Detections</h2>
            <div id="recent-alerts">
              <div class="alert-meta">Loading latest India detections...</div>
            </div>
          </section>
          <p class="footer-note">
            The live NASA view uses a wide FIRMS area query plus an India-focused polygon filter so the experience stays centered on India rather than neighboring bbox spillover.
          </p>
        </aside>
        <main class="map-wrap">
          <div id="map"></div>
          <div class="map-overlay"></div>
          <section class="hud">
            <h2 class="hud-title">India Focused View</h2>
            <p class="hud-copy">
              Live NASA mode pulls fresh FIRMS detections directly for an India-shaped viewport. Platform mode shows what aranya-watch currently has in its own API and database.
            </p>
            <div class="pill" id="refresh-pill">Auto-refresh every 60 seconds</div>
          </section>
        </main>
      </div>
      <script src="https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.js"></script>
      <script>
        const INDIA_BBOX = {{ minLat: 6.0, maxLat: 37.5, minLon: 68.0, maxLon: 97.5 }};
        const INDIA_BOUNDS = [
          [INDIA_BBOX.minLon, INDIA_BBOX.minLat],
          [INDIA_BBOX.maxLon, INDIA_BBOX.maxLat]
        ];
        let activeMode = 'nasa';
        const map = new maplibregl.Map({{
          container: 'map',
          center: [79.3, 22.6],
          zoom: 4.55,
          pitch: 0,
          bearing: 0,
          maxPitch: 0,
          style: {{
            version: 8,
            sources: {{
              carto: {{
                type: 'raster',
                tiles: ['https://a.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}.png'],
                tileSize: 256,
                attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
              }}
            }},
            layers: [
              {{ id: 'carto', type: 'raster', source: 'carto' }}
            ]
          }}
        }});

        map.addControl(new maplibregl.NavigationControl({{ visualizePitch: false }}), 'top-left');
        map.fitBounds(INDIA_BOUNDS, {{ padding: 44, duration: 0 }});

        function toFeature(alert) {{
          return {{
            type: 'Feature',
            geometry: {{
              type: 'Point',
              coordinates: [alert.longitude, alert.latitude]
            }},
            properties: alert
          }};
        }}

        function formatTime(value) {{
          const date = new Date(value);
          return date.toLocaleString('en-IN', {{
            day: '2-digit',
            month: 'short',
            hour: '2-digit',
            minute: '2-digit'
          }});
        }}

        function updateStats(alerts) {{
          const highRisk = alerts.filter((alert) => alert.risk_score >= 71).length;
          const peakRisk = alerts.length ? Math.max(...alerts.map((alert) => alert.risk_score)) : 0;
          document.getElementById('stat-count').textContent = alerts.length;
          document.getElementById('stat-high-risk').textContent = highRisk;
          document.getElementById('stat-risk').textContent = peakRisk ? peakRisk.toFixed(0) : '0';
        }}

        function updateRecentAlerts(alerts) {{
          const container = document.getElementById('recent-alerts');
          if (!alerts.length) {{
            container.innerHTML = '<div class="alert-meta">No detections available for the current India view.</div>';
            return;
          }}

          container.innerHTML = alerts
            .slice(0, 6)
            .map((alert) => `
              <div class="alert-row">
                <div>
                  <div>${{formatTime(alert.acq_datetime)}}</div>
                  <div class="alert-meta">${{alert.latitude.toFixed(2)}}, ${{alert.longitude.toFixed(2)}} · ${{alert.confidence}}</div>
                </div>
                <div class="alert-risk">${{alert.risk_score.toFixed(0)}}</div>
              </div>
            `)
            .join('');
        }}

        function setMode(mode) {{
          activeMode = mode;
          document.getElementById('mode-nasa').classList.toggle('active', mode === 'nasa');
          document.getElementById('mode-platform').classList.toggle('active', mode === 'platform');
        }}

        function updateMeta(payload) {{
          const sourceLabel = payload.mode === 'live_nasa'
            ? payload.source.replaceAll('_NRT', '').replaceAll('_', ' ')
            : 'aranya-watch';
          const datedLabel = payload.date ? `${{sourceLabel}} · ${{
            new Date(`${{payload.date}}T00:00:00Z`).toLocaleDateString('en-IN', {{ day: '2-digit', month: 'short' }})
          }}` : sourceLabel;
          document.getElementById('stat-source').textContent = datedLabel;
          document.getElementById('refresh-pill').textContent = `Refreshed ${{new Date().toLocaleTimeString('en-IN', {{ hour: '2-digit', minute: '2-digit' }})}}`;
        }}

        function ensureSources() {{
          if (map.getSource('alerts')) return;

          map.addSource('alerts', {{
            type: 'geojson',
            data: {{ type: 'FeatureCollection', features: [] }},
            cluster: true,
            clusterRadius: 42,
            clusterMaxZoom: 8
          }});

          map.addLayer({{
            id: 'alert-heat',
            type: 'heatmap',
            source: 'alerts',
            maxzoom: 8,
            paint: {{
              'heatmap-weight': ['interpolate', ['linear'], ['get', 'risk_score'], 0, 0.05, 100, 1],
              'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 3, 0.6, 8, 1.4],
              'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 3, 16, 8, 34],
              'heatmap-opacity': ['interpolate', ['linear'], ['zoom'], 3, 0.75, 9, 0.15],
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                0, 'rgba(76, 124, 91, 0)',
                0.25, '#67b06f',
                0.55, '#ebb84b',
                0.8, '#e88443',
                1, '#d45c2d'
              ]
            }}
          }});

          map.addLayer({{
            id: 'clusters',
            type: 'circle',
            source: 'alerts',
            filter: ['has', 'point_count'],
            paint: {{
              'circle-color': [
                'step',
                ['get', 'point_count'],
                '#eec062',
                10, '#e68a46',
                30, '#cf5d32'
              ],
              'circle-radius': [
                'step',
                ['get', 'point_count'],
                18,
                10, 24,
                30, 30
              ],
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff9ef'
            }}
          }});

          map.addLayer({{
            id: 'cluster-count',
            type: 'symbol',
            source: 'alerts',
            filter: ['has', 'point_count'],
            layout: {{
              'text-field': ['get', 'point_count_abbreviated'],
              'text-font': ['Open Sans Bold'],
              'text-size': 13
            }},
            paint: {{
              'text-color': '#fff8ef'
            }}
          }});

          map.addLayer({{
            id: 'unclustered-points',
            type: 'circle',
            source: 'alerts',
            filter: ['!', ['has', 'point_count']],
            paint: {{
              'circle-radius': [
                'interpolate',
                ['linear'],
                ['get', 'risk_score'],
                0, 5,
                100, 13
              ],
              'circle-color': [
                'interpolate',
                ['linear'],
                ['get', 'risk_score'],
                0, '#67b06f',
                40, '#b7c96b',
                70, '#ebb84b',
                100, '#d45c2d'
              ],
              'circle-opacity': 0.92,
              'circle-stroke-color': '#fff9ef',
              'circle-stroke-width': 1.5
            }}
          }});

          map.on('click', 'clusters', (event) => {{
            const features = map.queryRenderedFeatures(event.point, {{ layers: ['clusters'] }});
            const clusterId = features[0].properties.cluster_id;
            map.getSource('alerts').getClusterExpansionZoom(clusterId).then((zoom) => {{
              map.easeTo({{
                center: features[0].geometry.coordinates,
                zoom
              }});
            }});
          }});

          map.on('click', 'unclustered-points', (event) => {{
            const feature = event.features[0];
            const props = feature.properties;
            const html = `
              <div>
                <div class="popup-title">Fire Detection</div>
                <div class="popup-meta"><strong>Risk:</strong> ${{Number(props.risk_score).toFixed(2)}}</div>
                <div class="popup-meta"><strong>Brightness:</strong> ${{Number(props.brightness).toFixed(1)}}</div>
                <div class="popup-meta"><strong>Confidence:</strong> ${{props.confidence}}</div>
                <div class="popup-meta"><strong>Acquired:</strong> ${{formatTime(props.acq_datetime)}}</div>
              </div>
            `;

            new maplibregl.Popup({{ closeButton: false, offset: 14 }})
              .setLngLat(feature.geometry.coordinates)
              .setHTML(html)
              .addTo(map);
          }});

          map.on('mouseenter', 'clusters', () => {{
            map.getCanvas().style.cursor = 'pointer';
          }});
          map.on('mouseleave', 'clusters', () => {{
            map.getCanvas().style.cursor = '';
          }});
          map.on('mouseenter', 'unclustered-points', () => {{
            map.getCanvas().style.cursor = 'pointer';
          }});
          map.on('mouseleave', 'unclustered-points', () => {{
            map.getCanvas().style.cursor = '';
          }});
        }}

        async function loadIndiaAlerts() {{
          let payload;
          if (activeMode === 'nasa') {{
            const query = new URLSearchParams({{
              day_range: '3',
              limit: '2000'
            }});
            const response = await fetch(`/alerts/india/live?${{query.toString()}}`);
            if (!response.ok) throw new Error(`Failed to load NASA detections: ${{response.status}}`);
            payload = await response.json();
          }} else {{
            const query = new URLSearchParams({{
              min_lat: INDIA_BBOX.minLat,
              max_lat: INDIA_BBOX.maxLat,
              min_lon: INDIA_BBOX.minLon,
              max_lon: INDIA_BBOX.maxLon
            }});
            const response = await fetch(`/alerts/bbox?${{query.toString()}}`);
            if (!response.ok) throw new Error(`Failed to load platform alerts: ${{response.status}}`);
            payload = {{
              mode: 'platform_api',
              source: 'aranya-watch',
              alerts: await response.json()
            }};
          }}
          const alerts = payload.alerts;
          const collection = {{
            type: 'FeatureCollection',
            features: alerts.map(toFeature)
          }};

          ensureSources();
          map.getSource('alerts').setData(collection);
          updateStats(alerts);
          updateMeta(payload);
          updateRecentAlerts(
            [...alerts].sort((a, b) => new Date(b.acq_datetime) - new Date(a.acq_datetime))
          );
        }}

        map.on('load', async () => {{
          ensureSources();
          try {{
            await loadIndiaAlerts();
          }} catch (error) {{
            document.getElementById('recent-alerts').innerHTML = `<div class="alert-meta">${{error.message}}</div>`;
          }}
          window.setInterval(loadIndiaAlerts, 60000);
        }});

        document.getElementById('mode-nasa').addEventListener('click', async () => {{
          setMode('nasa');
          await loadIndiaAlerts();
        }});
        document.getElementById('mode-platform').addEventListener('click', async () => {{
          setMode('platform');
          await loadIndiaAlerts();
        }});
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/alerts/india/live")
def india_live_alerts(
    day_range: int = Query(default=3, ge=1, le=5),
    limit: int = Query(default=1500, ge=1, le=5000),
    source: str | None = Query(default=None),
    query_date: date | None = Query(default=None, alias="date"),
) -> dict[str, object]:
    """Return live NASA FIRMS detections for an India-focused map."""

    settings = get_settings()
    if not settings.firms_api_key:
        raise HTTPException(status_code=503, detail="FIRMS_API_KEY is not configured.")

    return fetch_india_live_alerts(
        day_range=day_range,
        limit=limit,
        source=source,
        query_date=query_date,
    )


@router.get("/alerts/bbox", response_model=list[FireAlertRead])
def bbox_alerts(
    request: Request,
    min_lat: float = Query(..., ge=-90, le=90),
    max_lat: float = Query(..., ge=-90, le=90),
    min_lon: float = Query(..., ge=-180, le=180),
    max_lon: float = Query(..., ge=-180, le=180),
    session: Session = Depends(get_db_session),
) -> list[FireAlertRead]:
    """Return fire alerts inside a bounding box."""

    if min_lat > max_lat or min_lon > max_lon:
        raise HTTPException(status_code=400, detail="Bounding box minimums must be less than maximums.")

    if getattr(request.app.state, "preview_mode", False):
        return get_preview_alerts_in_bbox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
        )

    alerts = get_alerts_in_bbox(
        session=session,
        min_lat=min_lat,
        max_lat=max_lat,
        min_lon=min_lon,
        max_lon=max_lon,
    )
    return [FireAlertRead.from_orm_with_risk(alert) for alert in alerts]


@router.get("/alerts/fire", response_model=list[FireAlertRead])
def nearby_fire_alerts(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(..., gt=0, le=1000),
    session: Session = Depends(get_db_session),
) -> list[FireAlertRead]:
    """Return fire alerts near a location."""

    if getattr(request.app.state, "preview_mode", False):
        return get_preview_alerts_within_radius(lat=lat, lon=lon, radius_km=radius_km)

    alerts = get_alerts_within_radius(
        session=session,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )
    return [FireAlertRead.from_orm_with_risk(alert) for alert in alerts]
