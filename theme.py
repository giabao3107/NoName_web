"""BI10 plotting palette, shared with Code/config/utils.py."""

PAL = {
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

TIER_COLORS = {
    "High": PAL["navy"],
    "Medium": PAL["amber"],
    "Low": PAL["red"],
}


def status_colors() -> list[str]:
    """Return the team's red-to-neutral-to-blue score gradient."""
    return [PAL["red"], PAL["amber"], PAL["navy"]]
