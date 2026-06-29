"""Toggleable overlay panel showing top dinosaurs/countries/discoverers for the current filters."""

from dash import Input, Output, State, dcc, html
import plotly.graph_objects as go
import pycountry
from data_dash import filter_occurrences, load_occurrences
from server import app
from slider_marks import EPOCH_NAMES

STATS_HIDDEN_STYLE = {'display': 'none'}
STATS_VISIBLE_STYLE = {
    'position': 'absolute', # fill parent map container
    # explicit height (matching map-frame's) instead of top+bottom stretch --
    # stretch mode adds border/padding on top of it regardless of boxSizing
    'top': 0, 'left': 0, 'right': 0, 'height': '620px',
    'background': 'rgba(15, 15, 30, 0.93)',
    'border': '4px solid rgba(255,255,255,0.07)',  # matches map-frame's border exactly
    'borderRadius': '12px',
    'boxSizing': 'border-box',
    'color': '#fff',
    'fontFamily': 'sans-serif',
    'zIndex': 900,  # below occurrence_panel 1000, so occurrence detail stays on top if both are open
    'padding': '20px',
    'overflowY': 'auto',  # scroll instead of spilling past the panel
    'display': 'flex',
    'gap': '24px',
}

COLUMN_STYLE = {
    'flex': 1,
    'background': 'rgba(15, 15, 30, 1)',
    'border': '4px solid rgba(255,255,255,0.07)',
    'borderRadius': '12px',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.5)',
    'overflow': 'hidden'
}

SUB_COLUMN_STYLE = {
    'background': 'rgba(255,255,255,0.03)',
    'border': '1px solid rgba(255,255,255,0.07)',
    'borderRadius': '8px',
    'padding': '10px',
    'margin': '10px',
}
 # used when mapping PBDB country codes to country names with pycountry
COUNTRY_CODE_OVERRIDES = {'UK': 'GB'}  # PBDB uses UK, not the ISO code GB

def _country_name(code):
    """Resolve a country code to its full name, with PBDB's non-ISO quirks handled."""
    country = pycountry.countries.get(alpha_2=COUNTRY_CODE_OVERRIDES.get(code, code))
    return country.name if country else code  # fall back to the raw code if unresolvable


def _top_taxa(filtered, n=5):
    """Top n taxon names by occurrence count."""
    return filtered['taxon_name'].value_counts().head(n)


def _top_countries(filtered, n=5):
    """Top n country codes by occurrence count, blanks excluded."""
    codes = filtered.loc[filtered['country_code'].notna() & (filtered['country_code'] != ''), 'country_code']
    top = codes.value_counts().head(n)
    top.index = top.index.map(_country_name) # index is key in code : count
    return top



def _top_discoverers(filtered, n=5):
    """Top n discoverers by occurrence count. `author` is pre-cleaned in dbt."""
    return filtered['author'].value_counts().head(n)


def _stat_column_children(title, counts, footnote=None):
    """A heading + a 'name -- count' row per entry, for one column's content.

    Args:
        title (str): column heading, ex: 'Top Dinosaurs'.
        counts (pandas.Series): value_counts() result to display.
        footnote (str | None): optional small note shown below the list.

    Returns:
        list: ready to drop into a column Div's `children`.
    """


    children = [
        # title -- same horizontal margin as the sub-columns, so its width matches theirs
        html.Div(title, style={
            'fontWeight': 'bold', 'color': '#fff',
            'padding': '10px 12px', 'background': 'rgba(255,255,255,0.07)',
            'borderBottom': '1px solid rgba(255,255,255,0.1)',
            'margin': '10px', 'borderRadius': '8px'}),

        # pie chart
        html.Div(
            dcc.Graph(figure=_build_pie(counts), config={'displayModeBar': False}), # hide default bar
            style=SUB_COLUMN_STYLE,
        ),
        
        # list
        html.Div(
            [
                html.Div([
                    html.Span('Name', style={'color': '#fff'}),
                    html.Span('Counts', style={'color': '#fff'}),
                ], style={
                    'display': 'flex', 'justifyContent': 'space-between',
                    'fontSize': '16px', 'padding': '4px 0',
                    'borderBottom': '1px solid rgba(255,255,255,0.06)',
                    }),
                *[
                    html.Div([
                        html.Span(name, style={'color': 'rgba(255,255,255,0.5)'}),
                        html.Span(str(count), style={'color': 'rgba(255,255,255,0.5)'}),
                    ], style={
                        'display': 'flex', 'justifyContent': 'space-between',
                        'fontSize': '16px', 'padding': '4px 0',
                        'borderBottom': '1px solid rgba(255,255,255,0.06)',
                    })
                    for name, count in counts.items()
                ],
            ],
            style=SUB_COLUMN_STYLE,
        ),
    ]
    if footnote:
        children.append(html.Div(footnote, style={'fontSize': '11px', 'color': 'rgba(255,255,255,0.4)', 'margin': '10px'}))
    return children
    
def _build_pie(counts):
    fig = go.Figure(go.Pie(labels=counts.index, values=counts.values))
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',  # transparent, blends into the panel's own background
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=10, b=10, l=10, r=10),
        height=240,
        showlegend=True,
    )
    return fig


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
    discoverers_col = _stat_column_children(
        'Top Discoverers', _top_discoverers(filtered),
        footnote='PaleobioDB Discoverer credit is by surname only, different people sharing a surname may appear as one entry.',
    )
    return style, taxa_col, countries_col, discoverers_col


def build_stats_store():
    """The Store backing this feature's open/closed state."""
    return dcc.Store(id='stats-panel-open', data=False)


def build_stats_toggle_button():
    """Button that toggles the statistics panel open/closed."""
    return html.Span(
        'View Top Dinosaurs, Countries & Discoverers',
        id='stats-toggle-btn',
        n_clicks=0,
        style={
            'cursor': 'pointer', 'padding': '10px 20px', 'borderRadius': '8px',
            'border': '1px solid rgba(255,255,255,0.15)', 'background': 'rgba(255,255,255,0.05)',
            'fontSize': '15px', 'fontWeight': 'bold',
        },
    )


def build_stats_panel():
    """The overlay itself: three columns, starting hidden.

    Returns:
        dash.html.Div: ready to drop alongside the map iframe.
    """
    return html.Div(
        id='stats-panel',
        style=STATS_HIDDEN_STYLE,
        children=[
            html.Div(id='stats-taxa-column', style=COLUMN_STYLE),
            html.Div(id='stats-countries-column', style=COLUMN_STYLE),
            html.Div(id='stats-discoverers-column', style=COLUMN_STYLE),
        ],
    )
