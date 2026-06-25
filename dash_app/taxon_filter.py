"""Left-hand nav: search box + checklist for filtering the map by taxon name. """

import dash
from dash import MATCH, Input, Output, State, ctx, dcc, html

from data_dash import load_occurrences
from server import app

TAXON_BATCH_SIZE = 100 # load x taxon_names at a single time in the list

# Get cached BigQuery taxon_names
ALL_TAXON_NAMES = sorted(load_occurrences()['taxon_name'].dropna().unique().tolist())


def _taxon_row_children(name, checked):
    """Generate checkbox & name text for one taxon row.

    Args:
        name (str): the taxon name this row represents.
        checked (bool): whether this taxon is currently selected.

    Returns:
        list[dash.html.Span]: the checkbox character + name text.
    """
    
    # Unicode checkbox char instead of actual checkbox input,
    # to avoid restyling native form control colors
    # flexShrink = fixed width column
    return [
        html.Span('☑' if checked else '☐', style={'marginRight': '8px', 'flexShrink': 0, 'color': '#c8aaff' if checked else 'rgba(255,255,255,0.4)'}),
        html.Span(name, style={'minWidth': 0}), # override flex default min-width so this can shrink/wrap in the column
    ]


def _taxon_row(name, checked):
    """Generate one clickable taxon row in the left-hand nav's filter list.

    Args:
        name (str): the taxon name this row represents.
        checked (bool): whether this taxon is currently selected.

    Returns:
        dash.html.Div: one clickable row, showing checked/unchecked state.
    """
    return html.Div(
        _taxon_row_children(name, checked),
        id={'type': 'taxon-row', 'name': name},
        n_clicks=0,  # required by Dash for Input store
        style={'cursor': 'pointer', 'padding': '3px 0', 'fontSize': '12px', 'color': 'rgba(255,255,255,0.85)', 'display': 'flex'}, # create columns for checkbox and label
    )


def _search_taxa(query):
    """
    Search filter taxon_names from list

    Args:
        query (str): lowercased search text.

    Returns:
        list[str]: matching taxon names, in their existing sorted order.
    """
    return [n for n in ALL_TAXON_NAMES if query in n.lower()] if query else ALL_TAXON_NAMES


@app.callback(
    Output('taxon-list-state', 'data', allow_duplicate=True),
    Output('taxon-checklist', 'children', allow_duplicate=True),
    Input('taxon-search', 'value'),
    Input('taxon-scroll-trigger', 'data'),
    State('taxon-list-state', 'data'),
    State('taxon-selected-store', 'data'),
    prevent_initial_call=True,
)
def update_taxon_list(search_text, _scroll_ping, state, selected):
    """Update the search query or grow the visible batch, and rebuild the visible rows in the same round trip.

    A search change always restarts the batch at TAXON_BATCH_SIZE.
    A scroll near bottom ping (from assets/taxon_scroll.js) grows the
    batch by TAXON_BATCH_SIZE, capped at however many taxa currently match.

    Args:
        search_text (str | None): the current text in the search box.
        _scroll_ping (int): timestamp written by the scroll listener. Not
            read directly, only its arrival as a fresh Input matters.
        state (dict): the Store's current value, shaped
            {'query': str, 'visible_count': int}.
        selected (list[str] | None): currently checked taxon names, so
            newly revealed rows still render as checked if applicable.

    Returns:
        tuple[dict, list[dash.html.Div]] | tuple[dash.no_update, dash.no_update]:
        the updated state and the rebuilt rows for the now-current batch.
    """
    triggered = ctx.triggered_id
    if triggered not in ('taxon-search', 'taxon-scroll-trigger'):
        return dash.no_update, dash.no_update

    state = dict(state or {})
    if triggered == 'taxon-search':
        state['query'] = search_text or ''
        state['visible_count'] = TAXON_BATCH_SIZE

    # the just-typed query (search) or the unchanged existing one (scroll)
    matches = _search_taxa(state.get('query', '').lower())

    if triggered == 'taxon-scroll-trigger':
        state['visible_count'] = min(state.get('visible_count', TAXON_BATCH_SIZE) + TAXON_BATCH_SIZE, len(matches))

    visible = matches[:state.get('visible_count', TAXON_BATCH_SIZE)]
    rows = [_taxon_row(n, n in (selected or [])) for n in visible]
    return state, rows


def _toggle_name(name, selected):
    """Flip one name's membership in State selected

    Args:
        name (str): the taxon name being toggled.
        selected (list[str] | None): currently checked taxon names, before this click.

    Returns:
        tuple[bool, list[str]]: the new checked state for name, and the
        updated selection list.
    """
    selected = list(selected or [])
    if name in selected:
        selected.remove(name)
        checked = False
    else:
        selected.append(name)
        checked = True
    return checked, selected


@app.callback(
    Output({'type': 'taxon-row', 'name': MATCH}, 'children'),
    Input({'type': 'taxon-row', 'name': MATCH}, 'n_clicks'),
    State('taxon-selected-store', 'data'),
    State({'type': 'taxon-row', 'name': MATCH}, 'id'),
    prevent_initial_call=True,
)
def update_taxon_row_display(n_clicks, selected, row_id):
    """Flip row's checkbox display when it's clicked.

    Args:
        n_clicks (int | None): this specific row's n_clicks. (required by Dash)
        selected (list[str]): currently State of checked taxon names, before this click.
        row_id (dict): this row's own id, {'type': 'taxon-row', 'name': str}.

    Returns:
        list[dash.html.Span] | dash.no_update: this row's new children,
        checkbox flipped from its pre-click state.
    """
    if not n_clicks:
        return dash.no_update

    checked, _ = _toggle_name(row_id['name'], selected)
    return _taxon_row_children(row_id['name'], checked)


@app.callback(
    Output('taxon-selected-store', 'data'),
    Input({'type': 'taxon-row', 'name': MATCH}, 'n_clicks'),
    State('taxon-selected-store', 'data'),
    State({'type': 'taxon-row', 'name': MATCH}, 'id'),
    prevent_initial_call=True,
)
def toggle_taxon_selection(n_clicks, selected, row_id):
    """Toggle one taxon's checked state in the global selection when its row is clicked.

    Args:
        n_clicks (int | None): this specific row's n_clicks. (required by Dash)
        selected (list[str]): currently checked taxon names, before this click.
        row_id (dict): this row's own id, {'type': 'taxon-row', 'name': str}.

    Returns:
        list[str] | dash.no_update: the updated selection, with the clicked
        taxon added if it wasn't selected, or removed if it was.
    """
    if not n_clicks:
        return dash.no_update

    _, new_selected = _toggle_name(row_id['name'], selected)
    return new_selected


def build_taxon_stores():
    """The Stores backing this feature's state -- standalone since dcc.Store
    renders no DOM node, they can sit anywhere in the layout.

    Args:
        None.

    Returns:
        list[dcc.Store]: [taxon-list-state, taxon-scroll-trigger, taxon-selected-store].
    """
    return [
        # Current search query + how many matching taxon names are currently
        # revealed in the checklist
        dcc.Store(id='taxon-list-state', data={'query': '', 'visible_count': TAXON_BATCH_SIZE}),
        # written by assets/taxon_scroll.js when the checklist is scrolled
        # near its bottom, value itself is not read, just need trigger of scroll
        dcc.Store(id='taxon-scroll-trigger', data=0),
        # currently checked taxon names
        dcc.Store(id='taxon-selected-store', data=[]),
    ]


def build_taxon_nav_panel(panel_style):
    """Build the left-hand nav: taxon search box + checklist + loading indicator.

    Args:
        panel_style (dict): panel styling

    Returns:
        dash.html.Div: the nav panel, ready to drop into app.layout.
    """
    return html.Div(style={**panel_style, 'flex': '0 0 240px', 'marginTop': 0, 'height': '620px', 'boxSizing': 'border-box', 'display': 'flex', 'flexDirection': 'column'}, children=[
        html.Label('Filter by Taxonomy', style={'display': 'block', 'textAlign': 'center', 'marginBottom': '12px'}),
        dcc.Input(
            id='taxon-search',
            type='text',
            placeholder='Search taxon name...',
            style={
                'width': '100%', 'boxSizing': 'border-box', 'marginBottom': '10px',
                'padding': '6px 10px', 'borderRadius': '6px',
                'border': '1px solid rgba(255,255,255,0.15)',
                'background': 'rgba(255,255,255,0.05)', 'color': '#fff',
            },
        ),
        # overflowY:auto recomputes its scrollbar correctly by construction
        html.Div(
            id='taxon-checklist',
            style={'height': '480px', 'overflowY': 'auto'},
            children=[_taxon_row(n, False) for n in ALL_TAXON_NAMES[:TAXON_BATCH_SIZE]],
        ),
    ])
