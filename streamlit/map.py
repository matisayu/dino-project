import json
import streamlit as st
import requests

@st.cache_data
def _load_us_states():
    url = 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json'
    return requests.get(url, timeout=10).json()

def build_map(df):
    data = (
        df[['modern_latitude', 'modern_longitude', 'taxon_name', 'discovery_year', 'geological_epoch', 'country_code', 'state', 'geology_comments', 'occurrence_id', 'collection_id']]
        .rename(columns={'modern_latitude': 'lat', 'modern_longitude': 'lon'})
        .dropna(subset=['lat', 'lon'])
        .fillna({'country_code': '', 'state': '', 'geology_comments': '', 'occurrence_id': 0, 'collection_id': 0})
        .to_dict(orient='records')
    )
    us_states = _load_us_states()

    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; background: #a8cfe0; }}
  #container {{ width: 100%; height: 100%; }}
  #panel {{
    display: none;
    position: absolute;
    top: 10px;
    right: 10px;
    width: 270px;
    max-height: 420px;
    background: rgba(15, 15, 30, 0.93);
    color: #fff;
    border-radius: 6px;
    font-family: sans-serif;
    font-size: 13px;
    z-index: 1000;
    overflow: hidden;
    box-shadow: 0 2px 12px rgba(0,0,0,0.5);
  }}
  #panel-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 12px;
    background: rgba(255,255,255,0.07);
    border-bottom: 1px solid rgba(255,255,255,0.1);
    font-weight: bold;
  }}
  #panel-close {{
    cursor: pointer;
    opacity: 0.6;
    font-size: 15px;
  }}
  #panel-close:hover {{ opacity: 1; }}
  #panel-content {{
    overflow-y: auto;
    max-height: 370px;
    padding: 4px 0;
  }}
  .occurrence-row {{ cursor: pointer; padding: 7px 12px; border-bottom: 1px solid rgba(255,255,255,0.06); transition: background 0.15s; }}
  .occurrence-row:last-child {{ border-bottom: none; }}
  .occurrence-row:hover {{ background: rgba(255,255,255,0.06); }}
  .occ-name {{ font-weight: bold; color: #c8aaff; }}
  .occ-meta {{ color: #aaa; font-size: 11px; margin-top: 2px; }}
  .occ-loc {{ color: #888; font-size: 11px; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  #panel-detail {{ display: none; padding: 12px; overflow-y: auto; max-height: 370px; }}
  .detail-name {{ font-size: 15px; font-weight: bold; color: #c8aaff; margin-bottom: 10px; line-height: 1.3; }}
  .detail-row {{ margin-bottom: 8px; }}
  .detail-label {{ color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 2px; }}
  .detail-value {{ color: #ddd; font-size: 12px; line-height: 1.4; }}
  #panel-back {{ cursor: pointer; opacity: 0.7; font-size: 12px; }}
  #panel-back:hover {{ opacity: 1; }}
</style>
<link href="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.css" rel="stylesheet" />
<script src="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.js"></script>
<script src="https://unpkg.com/deck.gl@8.9.35/dist.min.js"></script>
</head>
<body>
<div id="container"></div>
<div id="panel">
  <div id="panel-header">
    <span id="panel-title">Occurrences</span>
    <span style="display:flex;gap:10px;align-items:center;">
      <span id="panel-back" style="display:none;">← Back</span>
      <span id="panel-close">✕</span>
    </span>
  </div>
  <div id="panel-content"></div>
  <div id="panel-detail"></div>
</div>
<script id="states-data" type="application/json">{json.dumps(us_states)}</script>
<script id="fossil-data" type="application/json">{json.dumps(data)}</script>
<script>
const DATA    = JSON.parse(document.getElementById('fossil-data').textContent);
const STATES  = JSON.parse(document.getElementById('states-data').textContent);
const {{MapboxOverlay, ScatterplotLayer, GeoJsonLayer}} = deck;

var currentNearby = [];

function showList() {{
  document.getElementById('panel-content').style.display = 'block';
  document.getElementById('panel-detail').style.display = 'none';
  document.getElementById('panel-back').style.display = 'none';
}}

function showDetail(d) {{
  var loc = d.geology_comments || '';
  var place = [d.state, d.country_code].filter(Boolean).join(', ');
  document.getElementById('panel-detail').innerHTML =
    '<div class="detail-name">' + d.taxon_name + '</div>' +
    '<div class="detail-row"><div class="detail-label">Geological Epoch</div><div class="detail-value">' + (d.geological_epoch || '—') + '</div></div>' +
    '<div class="detail-row"><div class="detail-label">Discovery Year</div><div class="detail-value">' + (d.discovery_year || '—') + '</div></div>' +
    (place ? '<div class="detail-row"><div class="detail-label">Location</div><div class="detail-value">' + place + '</div></div>' : '') +
    (loc   ? '<div class="detail-row"><div class="detail-label">Site Description</div><div class="detail-value">' + loc + '</div></div>' : '') +
    (d.occurrence_id ? '<div class="detail-row"><div class="detail-label">PBDB Occurrence</div><div class="detail-value"><a href="https://paleobiodb.org/data1.2/occs/single.json?id=occ:' + d.occurrence_id + '&show=full" target="_blank" style="color:#c8aaff;">occ:' + d.occurrence_id + '</a>' + (d.collection_id ? ' &nbsp;<a href="https://paleobiodb.org/classic/displayCollResults?collection_no=' + d.collection_id + '" target="_blank" style="color:#aaa;font-size:11px;">view collection ↗</a>' : '') + '</div></div>' : '');
  document.getElementById('panel-content').style.display = 'none';
  document.getElementById('panel-detail').style.display = 'block';
  document.getElementById('panel-back').style.display = 'inline';
}}

document.getElementById('panel').addEventListener('click', function(e) {{
  e.stopPropagation();
}});

const map = new maplibregl.Map({{
  container: 'container',
  style: {{
    version: 8,
    sources: {{
      'esri-ocean': {{
        type: 'raster',
        tiles: ['https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{{z}}/{{y}}/{{x}}'],
        tileSize: 256,
        attribution: 'Esri, DeLorme, GEBCO, NOAA NGDC',
      }},
      'esri-labels': {{
        type: 'raster',
        tiles: ['https://services.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Reference/MapServer/tile/{{z}}/{{y}}/{{x}}'],
        tileSize: 256,
      }}
    }},
    layers: [
      {{ id: 'background', type: 'background', paint: {{ 'background-color': '#a8cfe0' }} }},
      {{ id: 'esri-ocean',  type: 'raster', source: 'esri-ocean', paint: {{ 'raster-contrast': 0.1, 'raster-saturation': -0.1, 'raster-brightness-max': 0.9 }} }},
      {{ id: 'esri-labels', type: 'raster', source: 'esri-labels', minzoom: 3 }},
    ]
  }},
  center: [0, 10],
  zoom: 0.5,
  maxZoom: 9,
}});

map.on('load', function() {{
  const w = document.getElementById('container').clientWidth;
  map.setMinZoom(Math.log2(w / 512) + 0.05);
}});

map.on('click', function(e) {{
  const zoom = map.getZoom();
  const degreesPerPixel = 360 / (512 * Math.pow(2, zoom));
  const radius = degreesPerPixel * 10;
  const clickLon = e.lngLat.lng;
  const clickLat = e.lngLat.lat;

  const nearby = DATA.filter(d => {{
    const dx = d.lon - clickLon;
    const dy = d.lat - clickLat;
    return Math.sqrt(dx * dx + dy * dy) < radius;
  }});

  if (nearby.length === 0) {{
    document.getElementById('panel').style.display = 'none';
    return;
  }}

  document.getElementById('panel-title').textContent =
    nearby.length + ' occurrence' + (nearby.length > 1 ? 's' : '');

  currentNearby = nearby;
  var html = '';
  for (var i = 0; i < nearby.length; i++) {{
    var d = nearby[i];
    html += '<div class="occurrence-row" data-idx="' + i + '">' +
      '<div class="occ-name">' + d.taxon_name + '</div>' +
      '<div class="occ-meta">' + (d.geological_epoch || '') + ' &middot; ' + (d.discovery_year || '') +
        (d.state ? ' &middot; ' + d.state : '') + (d.country_code ? ', ' + d.country_code : '') + '</div>' +
      (d.geology_comments ? '<div class="occ-loc" title="' + d.geology_comments + '">' + d.geology_comments + '</div>' : '') +
      '</div>';
  }}
  document.getElementById('panel-content').innerHTML = html;

  var rows = document.getElementById('panel-content').querySelectorAll('.occurrence-row');
  rows.forEach(function(row) {{
    row.addEventListener('click', function() {{
      showDetail(currentNearby[parseInt(this.getAttribute('data-idx'))]);
    }});
  }});

  showList();
  document.getElementById('panel').style.display = 'block';
}});

document.getElementById('panel-back').addEventListener('click', showList);

document.getElementById('panel-close').addEventListener('click', function() {{
  document.getElementById('panel').style.display = 'none';
  showList();
}});

const overlay = new MapboxOverlay({{
  layers: [
    new GeoJsonLayer({{
      id: 'us-states',
      data: STATES,
      stroked: true,
      filled: false,
      getLineColor: [120, 120, 120, 200],
      lineWidthMinPixels: 0.5,
    }}),
    new ScatterplotLayer({{
      id: 'fossils',
      data: DATA,
      getPosition: d => [d.lon, d.lat],
      getRadius: 80000,
      radiusMinPixels: 2,
      radiusMaxPixels: 8,
      getFillColor: [210, 120, 50, 70],
      stroked: false,
      filled: true,
      pickable: true,
    }})
  ],
  getTooltip: ({{object}}) => object && object.taxon_name && {{
    html: `<b>${{object.taxon_name}}</b><br/>${{object.geological_epoch}}<br/>Discovered: ${{object.discovery_year}}`,
    style: {{
      backgroundColor: '#1a1a2e',
      color: '#ffffff',
      fontSize: '13px',
      padding: '6px 10px',
      borderRadius: '4px',
    }}
  }}
}});

map.addControl(overlay);
</script>
</body>
</html>
"""
