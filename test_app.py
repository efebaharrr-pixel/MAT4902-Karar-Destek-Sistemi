from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_app_starts_without_exceptions():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not app.exception


def test_app_has_expected_controls():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    assert not app.exception
    assert app.selectbox
    assert app.slider


def test_app_runs_after_form_submission():
    app = AppTest.from_file("app.py", default_timeout=30).run()
    app.slider("mean_demand").set_value(600).run()
    app.button[0].click().run()

    assert not app.exception
    assert app.metric
