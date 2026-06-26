"""Renders the interactive fossil map: MapLibre handles basemap (pan,
zoom, tile rendering). deck.gl draws the US-state-border and fossil-dot
layers on top of it.

This module builds the map and reports click events upward via postMessage. 
See app.py for click-to-detail panel that reacts to those click events.
"""

import json
from functools import lru_cache
import requests

@lru_cache(maxsize=1)  # fetch on first startup and cache for rebuild
def _load_us_states():
    """Fetch US state border polygons (GeoJSON) for the GeoJsonLayer overlay.

    Args:
        None.

    Returns:
        dict: a GeoJSON FeatureCollection of US state boundary polygons,
        passed to deck.gl's GeoJsonLayer as its `data`.
    """
    url = 'https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json'
    return requests.get(url, timeout=10).json()


def build_map(df):
    """Build HTML page (MapLibre + deck.gl) for the given fossil rows.

    Recalled with every change on filters.

    Args:
        df (pandas.DataFrame): fossil occurrence rows to plot.
        Must contain:
            modern_latitude, modern_longitude, taxon_name, discovery_year,
            geological_epoch, country_code, state, geology_comments,
            occurrence_id, and collection_id columns.

    Returns:
        str: HTML document (MapLibre + deck.gl + the embedded fossil/state-border data)
        which is passed to html.Iframe.
    """
    data = (
        df[['modern_latitude', 'modern_longitude', 'taxon_name', 'discovery_year', 'geological_epoch', 'country_code', 'state', 'geology_comments', 'occurrence_id', 'collection_id']]
        .rename(columns={'modern_latitude': 'lat', 'modern_longitude': 'lon'}) 
        .dropna(subset=['lat', 'lon'])  # a fossil with no coordinates can't be plotted on a map
        .fillna({'country_code': '', 'state': '', 'geology_comments': '', 'occurrence_id': 0, 'collection_id': 0})  # swap Nan for an empty/zero placeholder
        .to_dict(orient='records')  # one dict per fossil
    )
    us_states = _load_us_states()

    return f"""
<!DOCTYPE html>
<html>
<head>
<style>
  /* Body style for iframe re-renders */
  html, body {{ margin: 0; padding: 0; height: 100%; background: #a8cfe0; }}
  
  /* MapLibre container styling */
  /* 3px keeps this corner concentric inside the iframe's own 12px radius/4px border */
  #container {{ width: 100%; height: 100%; border-radius: 3px; overflow: hidden; }}

  /* deck.gl hover tooltip styling */
  .deck-tooltip {{
    background-color: #1a1a2e;
    color: #ffffff;
    font-size: 13px;
    padding: 6px 10px;
    border-radius: 4px;
  }}
</style>
<link href="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.css" rel="stylesheet" /> <!-- MapLibre CSS  -->
<script src="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.js"></script> <!-- MapLibre engine: tiles, pan, zoom -->
<script src="https://unpkg.com/deck.gl@8.9.35/dist.min.js"></script> <!-- deck.gl for US state lines & scatterplot -->
</head>
<body>
<div id="container"></div>

<!-- Store raw json of states borders & scatterplot -->
<script id="states-data" type="application/json">{json.dumps(us_states)}</script>
<script id="fossil-data" type="application/json">{json.dumps(data)}</script>
<script>
const DATA    = JSON.parse(document.getElementById('fossil-data').textContent);
const STATES  = JSON.parse(document.getElementById('states-data').textContent);
const {{MapboxOverlay, ScatterplotLayer, GeoJsonLayer}} = deck;  // state borders, scatterplot, container

// Compute the zoom level that fits exactly one world copy into the container's width. 
// MapLibre tile size is 512 px, so zoom = log2(containerWidth / 512) is the
// zoom level at which one world-width in tiles exactly equals the container.
const _cw = document.getElementById('container').clientWidth || 800;  // fallback width if not yet laid out
const _fitZoom = Math.log2(_cw / 512) + 0.05;  // +0.05 nudges past the exact boundary to avoid edge repeats

const map = new maplibregl.Map({{
  container: 'container',  // render into the <div id="container"> above
  style: {{
    version: 8,
    sources: {{
      // Raster tile sources, each is just a URL template MapLibre fetches {{z}}/{{x}}/{{y}} tiles from.
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
    // Layers render in order: solid background color, ocean tiles, location labels
    layers: [
      {{ id: 'background', type: 'background', paint: {{ 'background-color': '#a8cfe0' }} }},
      {{ id: 'esri-ocean',  type: 'raster', source: 'esri-ocean', paint: {{ 'raster-contrast': 0.1, 'raster-saturation': -0.4, 'raster-brightness-max': 0.8 }} }},  // map styling
      {{ id: 'esri-labels', type: 'raster', source: 'esri-labels', minzoom: 3, paint: {{ 'raster-opacity': 0.85, 'raster-saturation': -0.2, 'raster-brightness-max': 0.85 }} }},  // location label styling
    ]
  }},
  center: [0, 10],  // initial view: mid-Atlantic, slightly north of the equator
  zoom: _fitZoom,
  minZoom: _fitZoom,  // set to max zoom out
  maxZoom: 9,
}});

// deck.gl overlay, attached to MapLibre map via map.addControl().
// Draws state borders, scatterplott and configures pan/zoom in sync
// with MapLibre map, and handles all click/hover picking.
const overlay = new MapboxOverlay({{
  onClick: ({{x, y}}) => {{
    // Check click radius
    const nearby = overlay.pickMultipleObjects({{
      x,
      y,
      radius: 10,  // 10px tolerance
      layerIds: ['fossils'],  // search scatterplot
    }}).map(p => p.object);  // post click data for Dash store-data to ingest
    window.parent.postMessage({{type: 'fossil-click', data: nearby}}, '*');
  }},
  layers: [
    // US state border lines
    new GeoJsonLayer({{
      id: 'us-states',
      data: STATES,
      stroked: true,
      filled: false,
      getLineColor: [120, 120, 120, 200], // grey
      lineWidthMinPixels: 0.5,
    }}),
    // One dot per fossil occurrence.
    new ScatterplotLayer({{
      id: 'fossils',
      data: DATA,
      getPosition: d => [d.lon, d.lat],  // fossil lat/lon
      getRadius: 80000,  // fossil dot radius in real meters
      radiusMinPixels: 2,  // min size even fully zoomed out
      radiusMaxPixels: 8,  // max size even fully zoomed in
      getFillColor: [210, 120, 50, 70],  // orange, low opacity
      stroked: false,
      filled: true,
      pickable: true,  // click/hover enabled
    }})
  ],
  // Hover tooltip called on pickable objects
  getTooltip: ({{object}}) => object && object.taxon_name && {{
    html: `<b>${{object.taxon_name}}</b><br/>${{object.geological_epoch}}<br/>Discovered: ${{object.discovery_year}}`,
  }}
}});

map.addControl(overlay);  // attach deck.gl overlay
</script>
</body>
</html>
"""
