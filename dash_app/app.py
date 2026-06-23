"""Interactive dinosaur fossil map dashboard utilizing MapLibre for map 
and deck.gl for clickable fossil dot scatterplot.

The map is a self-contained HTML document embedded via html.Iframe.

Clicking a fossil dot:
1) Posts a message out of the iframe
2) assets/message_bridge.js relays it into the `click-store` dcc.Store
3) Sent to the click-to-detail panel's logic is in Python from that
   store's data (see handle_panel_clicks and render_panel).
"""

import os

import dash
from dash import ALL, Dash, Input, Output, State, ctx, dcc, html

from map_dash import build_map
from data_dash import load_occurrences
from slider_marks import geo_age_marks, year_marks

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

# Slide panel styles
PANEL_STYLE = {
    'background': 'rgba(15, 15, 30, 0.93)',
    'borderRadius': '12px',
    'border': '4px solid rgba(255,255,255,0.07)',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.5)',
    'padding': '16px 24px',
    'marginTop': '10px',
    'flex': 1,
}

# Two states for toggled fossil detail panel
PANEL_HIDDEN_STYLE = {'display': 'none'}
PANEL_VISIBLE_STYLE = {
    'position': 'absolute',
    'top': '10px',
    'right': '10px',
    'width': '270px',
    'maxHeight': '420px',
    'background': 'rgba(15, 15, 30, 0.93)',
    'color': '#fff',
    'borderRadius': '6px',
    'fontFamily': 'sans-serif',
    'fontSize': '13px',
    'zIndex': 1000,  # Tell panel-box to float panel above the map iframe
    'overflow': 'hidden',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.5)',
}

def _occurrence_row(d, i):
    """Build one clickable row in the panel's list view, for fossil record `d`.

    Args:
        d (dict): one fossil occurrence record (taxon_name, geological_epoch,
            discovery_year, state, etc).
        i (int): this record's position in the current `nearby` list

    Returns:
        dash.html.Div: one clickable row, ready to drop into the panel's list view.
    """
    
    # Get fossil metadata
    meta = ' · '.join(filter(None, [d.get('geological_epoch') or '', str(d.get('discovery_year') or '')]))
    place = d.get('state') or ''
    if d.get('country_code'):
        place = f"{place}, {d['country_code']}" if place else d['country_code']
    meta_full = ' · '.join(filter(None, [meta, place]))  # append ", US" etc. if present

    # Form occurence row
    children = [
        html.Div(d.get('taxon_name', ''), style={'fontWeight': 'bold', 'color': '#c8aaff'}),
        html.Div(meta_full, style={'color': '#aaa', 'fontSize': '11px', 'marginTop': '2px'}),
    ]
    if d.get('geology_comments'): 
        children.append(html.Div(
            d['geology_comments'],
            title=d['geology_comments'],  # full text on hover
            style={'color': '#888', 'fontSize': '11px', 'marginTop': '2px', 'whiteSpace': 'nowrap', 'overflow': 'hidden', 'textOverflow': 'ellipsis'},
        ))

    return html.Div(
        children,
        id={'type': 'occ-row', 'index': i},  # id ingested into handle_panel_clicks()
        n_clicks=0,  # must be set explicitly so Dash treats this as a valid Input
        style={'cursor': 'pointer', 'padding': '7px 12px', 'borderBottom': '1px solid rgba(255,255,255,0.06)'},
    )

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

def _detail_row(label, value):
    """Generated labeled field in the detail view, ex: label='Discovery Year', value=1902.

    Args:
        label (str): Descriptive label.
        value (str | int | list): the field's content.

    Returns:
        dash.html.Div: Styled label/value pair.
    """
    return html.Div([
        html.Div(label, style={'color': '#888', 'fontSize': '10px', 'textTransform': 'uppercase', 'letterSpacing': '0.05em', 'marginBottom': '2px'}),
        html.Div(value, style={'color': '#ddd', 'fontSize': '12px', 'lineHeight': '1.4'}),
    ], style={'marginBottom': '8px'})


def _detail_view(d):
    """Build the full detail view for one selected fossil record `d`.
    Each field is only included if the data actually has a value for it.

    Args:
        d (dict): one fossil occurrence record (taxon_name, geological_epoch,
            discovery_year, state, country_code, geology_comments,
            occurrence_id, collection_id).

    Returns:
        dash.html.Div: the full detail view -- name, then one _detail_row()
        per populated field, then PBDB links if an occurrence_id is present.
    """
    rows = [
        html.Div(d.get('taxon_name', ''), style={'fontSize': '15px', 'fontWeight': 'bold', 'color': '#c8aaff', 'marginBottom': '10px', 'lineHeight': '1.3'}),
        _detail_row('Geological Epoch', d.get('geological_epoch') or '—'),
        _detail_row('Discovery Year', d.get('discovery_year') or '—'),
    ]
    place = ', '.join(filter(None, [d.get('state'), d.get('country_code')]))
    if place:
        rows.append(_detail_row('Location', place))
    if d.get('geology_comments'):
        rows.append(_detail_row('Site Description', d['geology_comments']))
    if d.get('occurrence_id'):  # link out to the Paleobiology Database
        link_children = [html.A(
            f"occ:{d['occurrence_id']}",
            href=f"https://paleobiodb.org/data1.2/occs/single.json?id=occ:{d['occurrence_id']}&show=full",
            target='_blank', style={'color': '#c8aaff'},
        )]
        if d.get('collection_id'):  # link to fossil's full collection
            link_children.append(html.A(
                '  view collection ↗',
                href=f"https://paleobiodb.org/classic/displayCollResults?collection_no={d['collection_id']}",
                target='_blank', style={'color': '#aaa', 'fontSize': '11px', 'marginLeft': '8px'},
            ))
        rows.append(_detail_row('PBDB Occurrence', link_children))
    return html.Div(rows, style={'padding': '12px', 'overflowY': 'auto', 'maxHeight': '370px'})

app = Dash(
    __name__,
    assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets'),
    # The panel's row ids ({'type': 'occ-row', 'index': i}) only exist once
    # render_panel() has actually created some rows -- they're not part of
    # the initial layout below. This tells Dash that's expected, rather than
    # treating it as a broken callback reference.
    suppress_callback_exceptions=True,
)

# Generate full web app html
app.layout = html.Div(
    style={'background': 'rgba(15, 15, 30, 0.93)', 'minHeight': '100vh', 'padding': '0 24px 24px', 'color': 'white', 'fontFamily': 'sans-serif'},
    
    children=[
        # title
        html.H1('Mapping the Age of Discovery', style={'margin': '0 0 12px 0', 'paddingTop': '16px'}),
        
        # Fossil count
        html.Div(id='occurrence-count'),  # filled in by update_map() below
        
        # Stores state of a click for ingestion by message_bridge.js (map click),
        # handle_panel_clicks(), and render_panel()
        dcc.Store(id='click-store', data={'nearby': [], 'selected': None}),
        
        # Map and occurrence/detail panel
        html.Div(
            style={'position': 'relative'}, # makes PANEL_VISIBLE_STYLE relative to map area, not whole page
            children=[
                html.Iframe(
                    id='map-frame',
                    srcDoc=build_map(df),  # Map rendering
                    style={'width': '100%', 'height': '620px', 'border': '4px solid rgba(255,255,255,0.07)', 'borderRadius': '12px'},
                ),
                html.Div(
                    id='panel-box',
                    style=PANEL_HIDDEN_STYLE,  # hidden until a valid click stored in click-store
                    children=[
                        # the title + back/close buttons is always present in the layout, just toggled via style
                        # avoids a "component doesn't exist yet" error that happens if these ids only appear inside dynamically rendered content.
                        html.Div([
                            html.Span('Occurrences', id='panel-title'),
                            html.Span([
                                html.Span(
                                    '← Back', id='panel-back-btn', n_clicks=0,
                                    style={'cursor': 'pointer', 'opacity': 0.7, 'fontSize': '12px', 'display': 'none'}, # default off
                                ),
                                html.Span('✕', id='panel-close-btn', n_clicks=0, style={'cursor': 'pointer', 'opacity': 0.6, 'fontSize': '15px'}),
                            ], style={'display': 'flex', 'gap': '10px', 'alignItems': 'center'}),
                        ], style={
                            'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
                            'padding': '10px 12px', 'background': 'rgba(255,255,255,0.07)',
                            'borderBottom': '1px solid rgba(255,255,255,0.1)', 'fontWeight': 'bold',
                        }),
                        html.Div(id='panel-body'),  # list view or detail view, filled in by render_panel()
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
)
def update_map(discovery_range, geo_idx_range):
    """Re-filter the dataset and rebuild the map whenever either slider moves.
    
    Args:
        discovery_range (list[int, int]): the Discovery Year slider's
            current [low, high] value, in actual years.
        geo_idx_range (list[int, int]): the Geological Age slider's current
            [low, high] value as indices.

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

    return build_map(filtered), f'Showing {len(filtered):,} of {len(df):,} occurrences'


@app.callback(
    Output('click-store', 'data', allow_duplicate=True), 
    Input({'type': 'occ-row', 'index': ALL}, 'n_clicks'),
    Input('panel-back-btn', 'n_clicks'),
    Input('panel-close-btn', 'n_clicks'),
    State('click-store', 'data'),
    prevent_initial_call=True,
)
def handle_panel_clicks(_row_clicks, _back_clicks, _close_clicks, store_data):
    """Update click-store in response to a row click, back click, or close click.

    Args:
    
        Required by Dash for each Input object (not used):
        _row_clicks (list[int | None]): n_clicks for each row ([0, 1] means row 2 has 1 click) (Required )
        _back_clicks (int | None): the back button's n_clicks. 
        _close_clicks (int | None): the close button's n_clicks. 
        
        
        store_data (dict): click-store's current State object before this click,
            shaped {'nearby': list[dict], 'selected': int | None}.

    Returns:
        dict | dash.no_update: the updated store data 
    """
    triggered = ctx.triggered_id # tells which Input fired 
    
    # Retain previous click data
    store_data = dict(store_data or {})

    if triggered == 'panel-close-btn':
        store_data['nearby'] = []  # empty list hides panel
        store_data['selected'] = None
    elif triggered == 'panel-back-btn':
        store_data['selected'] = None  # back to list view, keep same nearby list
    elif isinstance(triggered, dict) and triggered.get('type') == 'occ-row':
        store_data['selected'] = triggered['index']  # show detail view for this row
    else:
        return dash.no_update

    return store_data


@app.callback(
    Output('panel-box', 'style'),
    Output('panel-body', 'children'),
    Output('panel-title', 'children'),
    Output('panel-back-btn', 'style'),
    Input('click-store', 'data'),
)
def render_panel(store_data):
    """Render the occurence panel's visible state from click-store's data.

    Three states:
    1) hidden (no fossils in nearby)
    2) list view (nearby fossils, none selected for detail view)
    3) detail view (one selected)

    Args:
        store_data (dict): click-store's current value, shaped
            {'nearby': list[dict], 'selected': int | None}.

    Returns:
        tuple[dict, list | dash.html.Div, str, dict]:
            - panel-box's style (PANEL_HIDDEN_STYLE or PANEL_VISIBLE_STYLE).
            - panel-body's children: [] if hidden, else the list view or detail view.
            - panel-title's text: 'Occurrences', or 'N occurrence(s)' in list view.
            - panel-back-btn's style (visible only in detail view).
    """
    store_data = store_data or {}
    nearby = store_data.get('nearby') or []
    selected = store_data.get('selected')

    # Show back button in detail view
    back_style = {'cursor': 'pointer', 'opacity': 0.7, 'fontSize': '12px', 'display': 'inline' if selected is not None else 'none'}

    if not nearby:
        return PANEL_HIDDEN_STYLE, [], 'Occurrences', back_style

    if selected is None:
        title = f"{len(nearby)} occurrence{'s' if len(nearby) > 1 else ''}"  # "1 occurrence" vs "3 occurrences"
        body = html.Div(
            [_occurrence_row(d, i) for i, d in enumerate(nearby)],
            style={'overflowY': 'auto', 'maxHeight': '370px', 'padding': '4px 0'},
        )
    else:
        title = 'Occurrences'  # detail view always shows this generic title, not a count
        body = _detail_view(nearby[selected])

    return PANEL_VISIBLE_STYLE, body, title, back_style


if __name__ == '__main__':
    app.run(debug=True)
