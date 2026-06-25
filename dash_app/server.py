"""The shared Dash app instance, imported by app.py and every
feature module that builds layout or registers a callback against it.
"""

import os
from dash import Dash

app = Dash(
    __name__,
    assets_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets'),
    # Prevent exception from taxon-row, occ-row ids generating after initalization
    suppress_callback_exceptions=True,
)
