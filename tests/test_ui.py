from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "ui" / "streamlit_app.py"


def test_ui_shows_form_without_errors():
    app = AppTest.from_file(str(APP)).run(timeout=30)
    assert not app.exception
    assert app.title[0].value == "AI Travel Planner"
    assert app.text_input[0].value == "Goa"
