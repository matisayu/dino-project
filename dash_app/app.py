"""Interactive dinosaur fossil map dashboard utilizing MapLibre for map
and deck.gl for clickable fossil dot scatterplot.

The map is a self-contained HTML document embedded via html.Iframe.

See modules:
- taxon_filter.py: the left-hand taxon search/checklist nav.
- occurrence_panel.py: the click-to-detail panel that floats over the map.
- slider_marks.py: Adds visual slider marks
- map_dash.py: builds the MapLibre + deck.gl HTML document.
"""

from dash import Input, Output, dcc, html

from data_dash import load_occurrences
from map_dash import build_map
from occurrence_panel import build_click_store, build_panel_box
from server import app
from slider_marks import geo_age_marks, year_marks
from taxon_filter import build_taxon_nav_panel, build_taxon_stores

# 'Geological Age' slider tick labels, oldest to youngest, left to right
EPOCH_BOUNDARIES = [
    '251.9 Ma', '247.2 Ma', '237.0 Ma', '201.3 Ma', '174.1 Ma',
    '163.5 Ma', '145.0 Ma', '100.5 Ma', '66.0 Ma',
]
# Epoch names, one per gap between two adjacent boundaries above.
EPOCH_NAMES = [
    'Early Triassic', 'Middle Triassic', 'Late Triassic',
    'Early Jurassic', 'Middle Jurassic', 'Late Jurassic',
    'Early Cretaceous', 'Late Cretaceous',
]

# BigQuery queried once and cached
df = load_occurrences()
YEAR_MIN = int(df['discovery_year'].min())
YEAR_MAX = int(df['discovery_year'].max())

# Shared card style, used by the taxon nav panel and slider panels
PANEL_STYLE = {
    'background': 'rgba(15, 15, 30, 0.93)',
    'borderRadius': '12px',
    'border': '4px solid rgba(255,255,255,0.07)',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.5)',
    'padding': '16px 24px',
    'marginTop': '10px',
    'flex': 1,
}


def _two_line_label(text):
    """Force each word of `text` onto its own line, ex: 'Early Triassic' becomes 'Early' / 'Triassic'.

    Args:
        text (str): the label to split, ex: 'Early Triassic'.

    Returns:
        list: a mix of str (each word) and html.Br() (one between each pair
        of words), suitable as the `children` of an html.Div.
    """
    words = text.split()
    children = []
    for i, word in enumerate(words):
        if i > 0:
            children.append(html.Br())  # Dash line-break element between each word
        children.append(word)
    return children


# Generate full web app html
app.layout = html.Div(
    style={'background': 'rgba(15, 15, 30, 0.93)', 'minHeight': '100vh', 'padding': '0 24px 24px', 'color': 'white', 'fontFamily': 'sans-serif'},

    children=[
        # title
        html.H1('Mapping the Age of Discovery', style={'margin': '0 0 12px 0', 'paddingTop': '16px'}),

        # Fossil count
        html.Div(id='occurrence-count'),  # filled in by update_map() below

        build_click_store(),
        *build_taxon_stores(),

        # Left-hand nav (taxon name filter) + map/panel, side by side
        html.Div(
            style={'display': 'flex', 'gap': '24px'},
            children=[
                build_taxon_nav_panel(PANEL_STYLE),
                # Map and occurrence/detail panel
                html.Div(
                    style={'position': 'relative', 'flex': 1},  # makes panel-box's absolute positioning relative to map area, not whole page
                    children=[
                        html.Iframe(
                            id='map-frame',
                            srcDoc=build_map(df),  # Map rendering
                            style={'width': '100%', 'height': '620px', 'border': '4px solid rgba(255,255,255,0.07)', 'borderRadius': '12px', 'boxSizing': 'border-box'},
                        ),
                        build_panel_box(),
                    ],
                ),
            ],
        ),
        # Sliders
        html.Div(
            style={'display': 'flex', 'gap': '24px'},
            children=[
                html.Div(style=PANEL_STYLE, children=[
                    html.Label('Discovery Year', style={'display': 'block', 'textAlign': 'center', 'marginBottom': '55px'}),
                    dcc.RangeSlider(
                        id='discovery-slider',
                        min=YEAR_MIN,
                        max=YEAR_MAX,
                        step=1,  # yearly
                        value=[YEAR_MIN, YEAR_MAX],
                        marks=year_marks(YEAR_MIN, YEAR_MAX, step=25),
                        allow_direct_input=False,  # hide int entry boxes slider shows by default
                        tooltip={'placement': 'top', 'always_visible': True},  # show selected year above dial
                    ),
                ]),
                html.Div(style=PANEL_STYLE, children=[
                    html.Label('Geological Age', style={'display': 'block', 'textAlign': 'center', 'marginBottom': '55px'}),
                    dcc.RangeSlider(
                        id='geo-age-slider',
                        min=0,
                        max=len(EPOCH_BOUNDARIES) - 1,
                        step=None,  # restricts dragging to marks
                        value=[0, len(EPOCH_BOUNDARIES) - 1],
                        marks=geo_age_marks(EPOCH_BOUNDARIES),
                        # 'transform' maps the slider's raw 0-8 index value back
                        # to its Ma label for the tooltip, see assets/transforms.js.
                        tooltip={'placement': 'top', 'always_visible': True, 'transform': 'geoAgeLabel'},
                    ),
                    # epoch names, each between two Ma boundaries
                    html.Div(
                        style={'display': 'flex', 'marginTop': '6px'},
                        children=[
                            html.Div(_two_line_label(name), style={'flex': 1, 'textAlign': 'center', 'fontSize': '13px', 'color': 'rgba(255,255,255,0.5)'})
                            for name in EPOCH_NAMES
                        ],
                    ),
                ]),
            ],
        ),
    ],
)


@app.callback(
    Output('map-frame', 'srcDoc'),
    Output('occurrence-count', 'children'),
    Input('discovery-slider', 'value'),
    Input('geo-age-slider', 'value'),
    Input('taxon-selected-store', 'data'),
)
def update_map(discovery_range, geo_idx_range, selected_taxa):
    """Re-filter the dataset and rebuild the map whenever a slider moves or a taxon is (un)checked.

    Args:
        discovery_range (list[int, int]): the Discovery Year slider's
            current [low, high] value, in actual years.
        geo_idx_range (list[int, int]): the Geological Age slider's current
            [low, high] value as indices.
        selected_taxa (list[str]): currently checked taxon names. An empty
            list means "show all".

    Returns:
        tuple[str, str]:
            - the new map document, for map-frame's srcDoc (see map_dash.py build_map()).
            - the new "Showing X of Y occurrences" text, for occurrence count.
    """
    lo_idx, hi_idx = sorted(geo_idx_range)
    selected_epochs = EPOCH_NAMES[lo_idx:hi_idx]  # epochs between two selected boundaries

    filtered = df[
        (df['discovery_year'] >= discovery_range[0]) &
        (df['discovery_year'] <= discovery_range[1]) &
        (df['geological_epoch'].isin(selected_epochs))
    ]
    if selected_taxa:  # empty means no taxon restriction
        filtered = filtered[filtered['taxon_name'].isin(selected_taxa)]

    return build_map(filtered), f'Showing {len(filtered):,} of {len(df):,} occurrences'


if __name__ == '__main__':
    app.run(debug=True)
