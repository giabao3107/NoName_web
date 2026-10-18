from theme import PAL, TIER_COLORS, status_colors


def test_streamlit_theme_uses_the_team_palette_and_tier_semantics():
    assert PAL == {
        "navy": "#004AAD",
        "orange": "#004AAD",
        "amber": "#C8D1D9",
        "green": "#004AAD",
        "red": "#C51E1E",
        "grey": "#585757",
        "bg": "#C8D1D9",
        "card": "#FFFFFF",
        "ink": "#585757",
    }
    assert TIER_COLORS == {"High": "#004AAD", "Medium": "#C8D1D9", "Low": "#C51E1E"}
    assert status_colors() == ["#C51E1E", "#C8D1D9", "#004AAD"]
