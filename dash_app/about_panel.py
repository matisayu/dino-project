"""Toggleable About popup, centered over the map."""

from dash import Input, Output, State, dcc, html
from server import app

ABOUT_HIDDEN_STYLE = {'display': 'none'}
ABOUT_VISIBLE_STYLE = {
    'position': 'absolute',
    'top': '50%', 'left': '50%',
    'transform': 'translate(-50%, -50%)',  # center regardless of the panel's own size
    'width': '420px',
    'maxHeight': '480px',
    'overflowY': 'auto',
    'background': 'rgba(15, 15, 30, 0.93)',
    'border': '4px solid rgba(255,255,255,0.07)',
    'borderRadius': '12px',
    'boxShadow': '0 2px 12px rgba(0,0,0,0.5)',
    'padding': '20px 24px',
    'color': '#fff',
    'fontFamily': 'sans-serif',
    'fontSize': '13px',
    'lineHeight': '1.5',
    'zIndex': 1100,  # above panel-box (1000) and stats-panel (900)
}

LINK_STYLE = {'color': 'inherit', 'textDecoration': 'underline'}


@app.callback(
    Output('about-panel-open', 'data'),
    Input('about-toggle-btn', 'n_clicks'),
    Input('about-close-btn', 'n_clicks'),
    State('about-panel-open', 'data'),
    prevent_initial_call=True,
)
def toggle_about_panel(_open_clicks, _close_clicks, is_open):
    """Flip open/closed on either the banner button or the panel's own close button."""
    return not is_open


@app.callback(
    Output('about-panel', 'style'),
    Input('about-panel-open', 'data'),
)
def render_about_panel(is_open):
    """Show/hide the panel based on its open/closed state."""
    return ABOUT_VISIBLE_STYLE if is_open else ABOUT_HIDDEN_STYLE


def build_about_store():
    """Store backing the panel's open/closed state."""
    return dcc.Store(id='about-panel-open', data=False)


def build_about_panel():
    """The About popup itself, starting hidden."""
    return html.Div(
        id='about-panel',
        style=ABOUT_HIDDEN_STYLE,
        children=[
            html.Div([
                html.Span('About DinoTrace', style={'fontWeight': 'bold'}),
                html.Span('✕', id='about-close-btn', n_clicks=0, style={'cursor': 'pointer', 'opacity': 0.6}),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '14px'}),

            html.P([
                'DinoTrace is a non-profit tool for learning about and mapping dinosaur fossils. '
                'All data is sourced from ',
                html.A('PaleobioDB.org', href='https://paleobiodb.org/', target='_blank', style=LINK_STYLE), '.',
            ]),
            html.P("You can filter by taxonomy, geological age, and discovery year."),
            html.P(
                "PaleobioDB discoverer credit is by surname only,  different people sharing "
                "a surname may appear as one entry."
            ),
            html.P(
                "The taxonomy filter is pulled from PaleobioDB's 'taxon_name' attribute, the most "
                "specific classification level recorded for each fossil. Some fossils with "
                "imperfect data may not have a species or genus."
            ),
            html.P([
                'Built with ',
                html.A('MapLibre', href='https://maplibre.org/', target='_blank', style=LINK_STYLE), ', ',
                html.A('deck.gl', href='https://deck.gl/', target='_blank', style=LINK_STYLE), ', and ',
                html.A('Plotly Dash', href='https://dash.plotly.com/', target='_blank', style=LINK_STYLE), '.',
            ]),
            html.P([
                'Questions or feedback? Email ',
                html.A('nhkyt1@gmail.com', href='mailto:nhkyt1@gmail.com', style=LINK_STYLE), '.',
            ]),
            html.P('Thanks for using DinoTrace!', style={'marginBottom': 0}),
        ],
    )
