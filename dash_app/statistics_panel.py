"""Toggleable overlay panel showing top dinosaurs/countries/discoverers for the current filters."""

from dash import Input, Output, State, dcc, html

from data_dash import filter_occurrences, load_occurrences
from server import app
from slider_marks import EPOCH_NAMES

STATS_HIDDEN_STYLE = {'display': 'none'}
STATS_VISIBLE_STYLE = {
    'position': 'absolute', # fill parent map container
    'top': 0, 'left': 0, 'right': 0, 'bottom': 0,
    'background': 'rgba(15, 15, 30, 0.93)',
    'color': '#fff',
    'borderRadius': '12px',
    'fontFamily': 'sans-serif',
    'zIndex': 900,  # below occurrence_panel 1000, so occurrence detail stays on top if both are open
    'padding': '20px',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.5)',
    'display': 'flex',
    'gap': '24px',
}


def _top_taxa(filtered, n=5):
    """Top n taxon names by occurrence count."""
    return filtered['taxon_name'].value_counts().head(n)


def _top_countries(filtered, n=5):
    """Top n country codes by occurrence count, blanks excluded."""
    codes = filtered.loc[filtered['country_code'].notna() & (filtered['country_code'] != ''), 'country_code']
    return codes.value_counts().head(n)


def _top_discoverers(filtered, n=5):
    """Top n discoverers by occurrence count. `author` is pre-cleaned in dbt."""
    return filtered['author'].value_counts().head(n)


def _stat_column_children(title, counts):
    """A heading + a 'name -- count' row per entry, for one column's content.

    Args:
        title (str): column heading, ex: 'Top Dinosaurs'.
        counts (pandas.Series): value_counts() result to display.

    Returns:
        list: ready to drop into a column Div's `children`.
    """
    return [
        html.Div(title, style={'fontWeight': 'bold', 'color': '#c8aaff', 'marginBottom': '8px'}),
        html.Div([
            html.Div(f'{name} -- {count}', style={'fontSize': '13px', 'padding': '2px 0'})
            for name, count in counts.items()
        ]),
    ]


@app.callback(
    Output('stats-panel-open', 'data'),
    Input('stats-toggle-btn', 'n_clicks'),
    State('stats-panel-open', 'data'),
    prevent_initial_call=True,
)
def toggle_stats_panel(_n_clicks, is_open):
    """Flip the panel's open/closed state when the toggle button is clicked."""
    return not is_open


@app.callback(
    Output('stats-panel', 'style'),
    Output('stats-taxa-column', 'children'),
    Output('stats-countries-column', 'children'),
    Output('stats-discoverers-column', 'children'),
    Input('discovery-slider', 'value'),
    Input('geo-age-slider', 'value'),
    Input('taxon-selected-store', 'data'),
    Input('stats-panel-open', 'data'),
)
def render_statistics_panel(discovery_range, geo_idx_range, selected_taxa, is_open):
    """Rebuild the three stat columns from the current filters, and show/hide the panel.

    Args:
        discovery_range (list[int, int]): Discovery Year slider's [low, high].
        geo_idx_range (list[int, int]): Geological Age slider's [low, high] indices.
        selected_taxa (list[str]): currently checked taxon names.
        is_open (bool): whether the panel is currently toggled open.

    Returns:
        tuple[dict, list, list, list]: the panel's style, and the three columns' content.
    """
    df = load_occurrences()
    lo_idx, hi_idx = sorted(geo_idx_range)
    selected_epochs = EPOCH_NAMES[lo_idx:hi_idx]
    filtered = filter_occurrences(df, discovery_range, selected_epochs, selected_taxa)

    style = STATS_VISIBLE_STYLE if is_open else STATS_HIDDEN_STYLE
    taxa_col = _stat_column_children('Top Dinosaurs', _top_taxa(filtered))
    countries_col = _stat_column_children('Top Countries', _top_countries(filtered))
    discoverers_col = _stat_column_children('Top Discoverers', _top_discoverers(filtered))
    return style, taxa_col, countries_col, discoverers_col


def build_stats_store():
    """The Store backing this feature's open/closed state."""
    return dcc.Store(id='stats-panel-open', data=False)


def build_stats_toggle_button():
    """Small button that toggles the statistics panel open/closed."""
    return html.Span(
        'Statistics',
        id='stats-toggle-btn',
        n_clicks=0,
        style={
            'cursor': 'pointer', 'padding': '6px 14px', 'borderRadius': '6px',
            'border': '1px solid rgba(255,255,255,0.15)', 'background': 'rgba(255,255,255,0.05)',
            'fontSize': '13px',
        },
    )


def build_stats_panel():
    """The overlay itself: three columns + a disclaimer, starting hidden.

    Returns:
        dash.html.Div: ready to drop alongside the map iframe.
    """
    return html.Div(
        id='stats-panel',
        style=STATS_HIDDEN_STYLE,
        children=[
            html.Div(id='stats-taxa-column', style={'flex': 1}),
            html.Div(id='stats-countries-column', style={'flex': 1}),
            html.Div(id='stats-discoverers-column', style={'flex': 1}),
            html.Div( # disclaimer
                'Discoverer credit is by surname only, as recorded in PBDB -- different people sharing a surname may appear as one entry.',
                style={'position': 'absolute', 'bottom': '12px', 'left': '20px', 'right': '20px', 'fontSize': '11px', 'color': 'rgba(255,255,255,0.4)'},
            ),
        ],
    )
