"""Presentation styling loader for the VISTA Streamlit dashboard."""

from pathlib import Path


STYLE_PATH = Path(__file__).with_name("styles.css")


def load_css() -> str:
    """Return the dashboard stylesheet wrapped for ``st.markdown`` injection."""
    return f"<style>{STYLE_PATH.read_text(encoding='utf-8')}</style>"
