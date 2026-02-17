"""Standalone blotter dashboard — shares orders.json with the pricer dashboard.

Run: python -m options_pricer.dashboard.blotter_app
Serves on http://127.0.0.1:8051
"""

from dash import Dash

from .callbacks import register_blotter_callbacks
from .layouts import create_blotter_layout

app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "Admin Dashboard"
app.layout = create_blotter_layout

# Register the shared blotter callbacks (poll, sync edits, column toggle, column visibility)
register_blotter_callbacks()


def main():
    """Run the blotter-only dashboard."""
    app.run(host="127.0.0.1", port=8051, debug=True)


if __name__ == "__main__":
    main()
