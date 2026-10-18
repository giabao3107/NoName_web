from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "app.py"


def test_streamlit_dashboard_renders_without_exceptions():
    app = AppTest.from_file(str(APP_PATH), default_timeout=40).run()

    assert not app.exception
    assert len(app.tabs) == 4
    assert len(app.get("plotly_chart")) >= 10
    assert any("Record-level customer rows are excluded" in warning.value for warning in app.warning)
