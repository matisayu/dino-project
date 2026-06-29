"""Toggleable Tutorial popup, centered over the map."""

from dash import Input, Output, State, dcc, html
from server import app

TUTORIAL_HIDDEN_STYLE = {'display': 'none'}
TUTORIAL_VISIBLE_STYLE = {
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


@app.callback(
    Output('tutorial-panel-open', 'data'),
    Input('tutorial-toggle-btn', 'n_clicks'),
    Input('tutorial-close-btn', 'n_clicks'),
    State('tutorial-panel-open', 'data'),
    prevent_initial_call=True,
)
def toggle_tutorial_panel(_open_clicks, _close_clicks, is_open):
    """Flip open/closed on either the banner button or the panel's own close button."""
    return not is_open


@app.callback(
    Output('tutorial-panel', 'style'),
    Input('tutorial-panel-open', 'data'),
)
def render_tutorial_panel(is_open):
    """Show/hide the panel based on its open/closed state."""
    return TUTORIAL_VISIBLE_STYLE if is_open else TUTORIAL_HIDDEN_STYLE


def build_tutorial_store():
    """Store backing the panel's open/closed state."""
    return dcc.Store(id='tutorial-panel-open', data=False)


def build_tutorial_panel():
    """The Tutorial popup itself, starting hidden."""
    return html.Div(
        id='tutorial-panel',
        style=TUTORIAL_HIDDEN_STYLE,
        children=[
            html.Div([
                html.Span('Tutorial', style={'fontWeight': 'bold'}),
                html.Span('✕', id='tutorial-close-btn', n_clicks=0, style={'cursor': 'pointer', 'opacity': 0.6}),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '14px'}),

            html.P("Welcome to DinoTrace! Here's a quick rundown of the features available."),
            html.P(
                "In the center is an interactive map with a clickable scatterplot of dinosaur "
                "fossils. Click an occurrence dot to see the fossils in that radius, then click "
                "any row in the list for more detail -- discovery year, attribution, finding "
                "details, and a link to the full collection."
            ),
            html.P("The number of occurrences matching the current filters is shown in the map's bottom-left corner."),
            html.P("The left-hand panel is a searchable list of taxonomy names."),
            html.P("Below the map are sliders to filter by geological age and discovery year."),
            html.P(
                'Combine the taxonomy and slider filters to ask specific questions, e.g. '
                '"Find all Stegosaurus discovered between 1800-1900 in the Early Cretaceous."'
            ),
            html.P(
                'The "View Top Dinosaurs, Countries & Discoverers" button shows the top 5 '
                'dinosaurs, countries by fossil density, and discoverers, for the current filter '
                'set, update the filters with it open and watch it change!'
            ),
        ],
    )
