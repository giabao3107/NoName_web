"""Interactive BI10 customer intelligence dashboard (Streamlit + Plotly)."""

from __future__ import annotations


import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import customer_frame, filter_customers, load_dashboard_data, update_full_population_aggregates
from theme import APP_BACKGROUND, PAL, TIER_COLORS, status_colors

NAVY = PAL["navy"]
ORANGE = PAL["orange"]
AMBER = PAL["amber"]
BG = APP_BACKGROUND
CARD = PAL["card"]
HIGH = TIER_COLORS["High"]
MEDIUM = TIER_COLORS["Medium"]
LOW = TIER_COLORS["Low"]
NEUTRAL = PAL["grey"]
TIER_LABELS = {"High": "High health", "Medium": "Moderate health", "Low": "Financial stress"}

st.set_page_config(
    page_title="Customer Intelligence 360° | BI10",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(
    f"""
    <style>
      .stApp {{ background: {BG}; color: {PAL['ink']}; }}
      [data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid rgba(88,87,87,.22); }}
      .hero {{ background: {NAVY}; color: #fff; padding: 1.55rem 2rem 1.35rem; border-radius: 6px; margin-bottom: 1.1rem; }}
      .hero h1 {{ color: #fff; font-size: clamp(1.6rem, 3vw, 2.25rem); margin: 0 0 .4rem; font-weight: 750; }}
      .hero p {{ color: rgba(255,255,255,.82); margin: 0; }}
      .meta-line {{ color: rgba(255,255,255,.72); font-size: .78rem; margin-top: .9rem; }}
      [data-testid="stMetric"] {{ background:{CARD}; border:1px solid rgba(88,87,87,.22); border-radius:6px; padding:1rem 1.05rem; min-height: 118px; }}
      [data-testid="stMetricLabel"] {{ color:{NEUTRAL}; }}
      div[data-testid="stMetricValue"] {{ color:{NAVY}; font-weight:750; }}
      h2, h3 {{ color:{NAVY}; }}
      div[data-testid="stTabs"] button[aria-selected="true"] {{ color:{NAVY}; border-bottom-color:{ORANGE}; }}
      .note {{ color:{NEUTRAL}; font-size:.82rem; }}
      .stCaption {{ color:{NEUTRAL}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_int(value: float | int) -> str:
    return f"{int(round(value)):,}"


def fmt_pct(value: float | int, digits: int = 1) -> str:
    return f"{float(value) * 100:.{digits}f}%"


def fmt_vnd(value: float | int) -> str:
    magnitude = abs(float(value))
    sign = "-" if value < 0 else ""
    if magnitude >= 1e12:
        return f"{sign}{magnitude / 1e12:.2f}T"
    if magnitude >= 1e9:
        return f"{sign}{magnitude / 1e9:.2f}B"
    if magnitude >= 1e6:
        return f"{sign}{magnitude / 1e6:.1f}M"
    if magnitude >= 1e3:
        return f"{sign}{magnitude / 1e3:.0f}K"
    return f"{sign}{magnitude:.0f}"


def style_figure(fig: go.Figure, *, height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        height=height,
        margin={"l": 18, "r": 18, "t": 18, "b": 18},
        paper_bgcolor=CARD,
        plot_bgcolor=CARD,
        font={"family": "Inter, system-ui, sans-serif", "color": PAL["ink"], "size": 11},
        legend={"orientation": "h", "y": -0.2, "x": 0, "font": {"size": 10}, "visible": legend},
        hoverlabel={"bgcolor": NAVY, "font": {"color": "white"}},
    )
    fig.update_xaxes(showgrid=False, linecolor="rgba(88,87,87,.22)")
    fig.update_yaxes(gridcolor="rgba(88,87,87,.18)", zerolinecolor="rgba(88,87,87,.22)")
    return fig


def bar_histogram(section: dict, tier_selected: str, title: str, logarithmic: bool = False) -> go.Figure:
    edges = section["edges"]
    counts = section["counts"]
    fig = go.Figure()
    for tier in ("High", "Medium", "Low"):
        opacity = 1 if tier_selected == "All" or tier_selected == tier else 0.18
        fig.add_bar(
            name=f"{TIER_LABELS[tier]} ({tier})",
            x=[f"{edge}–{edge + 2}" for edge in edges],
            y=counts[tier],
            marker={"color": TIER_COLORS[tier], "opacity": opacity},
            hovertemplate=f"{tier}: %{{y:,}} customers<extra></extra>",
        )
    fig.update_layout(barmode="stack", title=title)
    fig.update_xaxes(title="Score", tickangle=0, nticks=12)
    fig.update_yaxes(title="Customers", type="log" if logarithmic else "linear")
    return style_figure(fig, height=360)


def draw_profile(profile: dict, score_key: str, score_label: str, *, validation_rate: float | None = None) -> None:
    st.markdown("#### Tier profile")
    col1, col2 = st.columns(2)
    col1.metric("Customers", fmt_int(profile["n"]))
    col2.metric(score_label, f"{profile[score_key]:.1f}")
    col1.metric("Expected delinquency", fmt_pct(profile["expected_bad"], 2) if "expected_bad" in profile else "–")
    col2.metric("Observed validation", fmt_pct(validation_rate, 2) if validation_rate is not None else "–")

    components = profile.get("pillars", profile.get("components", {}))
    if components:
        component_frame = pd.DataFrame({"Component": list(components), "Points": list(components.values())})
        fig = px.bar(
            component_frame,
            x="Points",
            y="Component",
            orientation="h",
            text=component_frame["Points"].map(lambda v: f"{v:.1f}"),
            color="Points",
            color_continuous_scale=status_colors(),
            range_color=(0, 100),
        )
        fig.update_layout(coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_figure(fig, height=240, legend=False), width="stretch")


def tier_selector(prefix: str) -> str:
    return st.selectbox(
        "Highlight tier",
        ["All", "High", "Medium", "Low"],
        format_func=lambda value: "All customers" if value == "All" else TIER_LABELS[value],
        key=f"{prefix}_tier",
    )


def show_financial_health(data: dict) -> None:
    fh = data["fh"]
    left, right = st.columns([1.8, 1])
    with left:
        selected = tier_selector("fh")
        st.plotly_chart(bar_histogram(fh["hist"], selected, "Financial Health Score distribution"), width="stretch")
        st.caption("FHS combines repayment history (40%), credit standing (30%), debt burden / DTI (15%), and down-payment (15%), followed by policy caps.")
    with right:
        profile = fh["tier_profile"][selected]
        tiers = fh["validation"]["tier_table"]
        validation = {row["tier"]: row["bad_rate"] for row in tiers}
        observed = fh["validation"]["bad_rate_dev"] if selected == "All" else validation.get(selected)
        draw_profile(profile, "mean_fhs", "Average FHS", validation_rate=observed)

    st.subheader("Financial health risk analysis")
    product_col, dti_col = st.columns(2)
    with product_col:
        products = pd.DataFrame(fh["product"])
        fig = px.bar(products, x="PRODUCT", y="bad_rate", color="bad_rate", color_continuous_scale=status_colors(),
                     hover_data={"n_contracts": True, "delinquency_rate": ":.2%", "default_rate": ":.2%", "bad_rate": ":.2%"},
                     labels={"PRODUCT": "Product", "bad_rate": "Observed bad rate"}, title="Delinquency and default by product")
        fig.update_yaxes(tickformat=".1%", title="Bad rate")
        st.plotly_chart(style_figure(fig, height=330, legend=False), width="stretch")
        st.caption("Mature signed contracts; delinquency/default are observed associations, not causal product effects.")
    with dti_col:
        dist = fh["dti_dist"]
        fig = go.Figure()
        for tier in ("High", "Medium", "Low"):
            fig.add_bar(name=TIER_LABELS[tier], x=dist["labels"], y=dist["counts"][tier], marker_color=TIER_COLORS[tier])
        fig.update_layout(barmode="stack", title="Current debt-to-income distribution")
        fig.update_xaxes(title="Current DTI band", tickangle=-18)
        fig.update_yaxes(title="Customers")
        st.plotly_chart(style_figure(fig, height=330), width="stretch")
        st.caption(f"DTI tipping point: {fh['dti']['breakpoint']:.1%}; offer ceiling: {fh['dti']['dti_ceiling']:.1%}. No-income cases are kept separate.")

    left, right = st.columns(2)
    with left:
        curve = pd.DataFrame(fh["dti_curve"])
        if not curve.empty:
            fig = px.line(curve, x="mid", y="bad_rate", markers=True, hover_data=["n"],
                          labels={"mid": "DTI at origination", "bad_rate": "Observed bad rate"},
                          title="Observed delinquency by DTI at origination")
            fig.update_traces(line_color=ORANGE)
            fig.update_yaxes(tickformat=".1%")
            st.plotly_chart(style_figure(fig, height=300, legend=False), width="stretch")
    with right:
        deciles = pd.DataFrame(fh["validation"]["decile_table"])
        if not deciles.empty:
            fig = go.Figure()
            fig.add_scatter(x=deciles["decile"], y=deciles["bad_rate"], mode="lines+markers", name="Observed", line={"color": LOW})
            fig.add_scatter(x=deciles["decile"], y=deciles["pd_predicted"], mode="lines+markers", name="Predicted", line={"color": NAVY, "dash": "dash"})
            fig.update_layout(title="Out-of-time calibration by FHS decile", xaxis_title="Risk decile (1 = lowest score)", yaxis_title="Delinquency rate")
            fig.update_yaxes(tickformat=".1%")
            st.plotly_chart(style_figure(fig, height=300), width="stretch")
    st.caption(f"Validation: AUC {fh['validation']['auc_holdout']:.3f}, Gini {fh['validation']['gini_holdout']:.3f}, KS {fh['validation']['ks_holdout']:.3f}; holdout n={fmt_int(fh['validation']['n_holdout'])}.")


def show_engagement(data: dict) -> None:
    eng = data["eng"]
    left, right = st.columns([1.8, 1])
    with left:
        selected = tier_selector("eng")
        logarithmic = st.checkbox("Use logarithmic count scale", value=True, key="eng_log")
        st.plotly_chart(bar_histogram(eng["hist"], selected, "Engagement Score distribution", logarithmic), width="stretch")
        st.caption("Engagement combines digital use (20%), recency (20%), frequency (25%), responsiveness (20%), and product breadth (15%).")
    with right:
        profile = eng["tier_profile"][selected]
        draw_profile(profile, "mean_eng", "Average engagement")

    st.subheader("Engagement drivers and outcomes")
    app_col, leads_col = st.columns(2)
    with app_col:
        app_data = pd.DataFrame(eng["app_band"])
        fig = px.bar(app_data, x="app_band", y="conv", error_y=app_data["ci_hi"] - app_data["conv"],
                     error_y_minus=app_data["conv"] - app_data["ci_lo"], color="conv", color_continuous_scale=[AMBER, HIGH],
                     hover_data={"n": True, "pos": ":.2%", "conv": ":.2%"},
                     labels={"app_band": "App sessions", "conv": "Lead conversion"}, title="App activity and telesales conversion")
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(style_figure(fig, height=330, legend=False), width="stretch")
        st.caption("Descriptive association among customers with a sales-call outcome. App use is not evidence of causing conversion.")
    with leads_col:
        source_data = pd.DataFrame(eng["lead_source"])
        fig = px.bar(source_data, x="LEAD_SOURCE", y="deal_rate", color="deal_rate", color_continuous_scale=status_colors(),
                     hover_data={"n_leads": True, "signed_within_90d": ":.1%", "active_180d_after": ":.1%", "deal_rate": ":.2%"},
                     labels={"LEAD_SOURCE": "Lead source", "deal_rate": "Lead deal rate"}, title="Lead source performance")
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(style_figure(fig, height=330, legend=False), width="stretch")
        st.caption("Deal rate, 90-day signed-within-offer, and 180-day active retention are separate outcomes.")

    temporal = pd.DataFrame(eng["early_temporal"])
    if not temporal.empty:
        fig = px.bar(temporal, x="trend", y="bad_rate", color="trend", color_discrete_map={"Rising": PAL["red"], "Stable": NEUTRAL, "Declining": PAL["navy"], "No prior activity": PAL["amber"]},
                     hover_data={"n": True, "bad_rate": ":.2%"}, labels={"trend": "Activity trajectory", "bad_rate": "Observed delinquency"},
                     title="Early-warning test: engagement trajectory and delinquency")
        fig.update_yaxes(tickformat=".1%")
        st.plotly_chart(style_figure(fig, height=310), width="stretch")
    validation = eng["validation"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Apply conversion AUC", f"{validation['auc_apply']:.3f}")
    c2.metric("Sign conversion AUC", f"{validation['auc_sign']:.3f}")
    c3.metric("Lead deal AUC", f"{validation['auc_lead_deal']:.3f}")
    st.caption(f"Validation sample n={fmt_int(validation['n'])}; apply rate {fmt_pct(validation['apply_rate'], 2)}. Validation indicates association / discrimination, not causality.")


def show_segments(data: dict, customers: pd.DataFrame) -> None:
    cells = pd.DataFrame(data["matrix"]["cells"])
    health_order = ["Low", "Medium", "High"]
    engagement_order = ["Low", "Medium", "High"]
    cell_counts = cells.pivot(index="eng", columns="fh", values="customers").reindex(index=engagement_order, columns=health_order)
    fig = px.imshow(cell_counts, text_auto=":,", aspect="auto", color_continuous_scale=[PAL["amber"], PAL["navy"]],
                    labels={"x": "Financial health tier", "y": "Engagement tier", "color": "Customers"},
                    title="Customer opportunity matrix")
    fig.update_xaxes(tickmode="array", tickvals=list(range(3)), ticktext=["Financial stress", "Moderate health", "High health"])
    fig.update_yaxes(tickmode="array", tickvals=list(range(3)), ticktext=["Low / dormant", "Medium", "High"])
    fig.update_traces(hovertemplate="Engagement: %{y}<br>Financial health: %{x}<br>Customers: %{z:,}<extra></extra>")
    st.plotly_chart(style_figure(fig, height=390, legend=False), width="stretch")
    st.caption("Matrix counts cover the full scored customer population; source-cohort counts remain tied to each analysis's own eligibility window.")

    actions = pd.DataFrame(data["matrix"]["nba"]).sort_values("n", ascending=True)
    fig = px.bar(actions.tail(14), x="n", y="Next_Best_Action", orientation="h", color="persona",
                 hover_data={"n": ":,", "low_variant": True},
                 labels={"n": "Customers", "Next_Best_Action": "Recommended next best action", "persona": "Segment"},
                 title="Next Best Action volume (top 14)")
    st.plotly_chart(style_figure(fig, height=440), width="stretch")

    economics = data["matrix"]["economics"]
    ev_cols = st.columns(3)
    ev_cols[0].metric("Value from blanket calling", f"{fmt_vnd(sum(c['ev_blanket'] for c in data['matrix']['cells']))} VND")
    ev_cols[1].metric("Value-based routed calls", f"{fmt_vnd(sum(c['ev_routed'] for c in data['matrix']['cells']))} VND")
    ev_cols[2].metric("Customers worth calling", fmt_int(data["kpi"]["call_worthy"]))
    st.caption(f"Value model parameters: gross yield {fmt_pct(economics['gross_yield'])}, roll rate {fmt_pct(economics['roll_rate'])}, LGD {fmt_pct(economics['lgd'])}, call attempt cost {fmt_vnd(economics['cost_per_attempt'])} VND. This is modeled expected value, not realized profit.")

    st.subheader("Customer-level drilldown")
    if customers.empty:
        st.info(f"Population analytics above summarize all {fmt_int(data['meta']['n_customers'])} scored customers and {fmt_int(data['kpi']['n_rows_raw'])} source records across five tables. Individual records are omitted from the public snapshot to protect financial information.")
    else:
        st.info(f"Local full-output file loaded: {fmt_int(len(customers))} of {fmt_int(data['meta']['n_customers'])} customers. Record-level drilldown is local only; public aggregate charts remain full-population.")
        search_col, health_col, engagement_col = st.columns([1.4, 1, 1])
        search = search_col.text_input("Search customer ID", placeholder="e.g. 3733")
        health = health_col.multiselect("Financial health", ["High", "Medium", "Low"], default=[])
        engagement = engagement_col.multiselect("Engagement", ["High", "Medium", "Low"], default=[])
        priorities = []
        if "prio" in customers.columns:
            priority_col = st.columns([1, 1, 1, 1])[3]
            priorities = priority_col.multiselect("Priority", [0, 1, 2, 3, 4], default=[], format_func=lambda value: f"P{value}")
        filtered = filter_customers(customers, search=search, fh_tiers=health, engagement_tiers=engagement, priorities=priorities)
        sort_labels = {"fhs": "Financial health", "eng": "Engagement", "offer": "Offer cap", "id": "Customer ID"}
        sort_options = [key for key in ("ev", "fhs", "eng", "prio", "offer", "id") if key in filtered.columns]
        sort_col = st.selectbox("Sort customer records by", sort_options, format_func=lambda value: sort_labels.get(value, "Call expected value"))
        filtered = filtered.sort_values(sort_col, ascending=sort_col == "prio", na_position="last")
        display = filtered.head(100).copy()
        rename = {"id": "Customer ID", "fhs": "Financial health", "eng": "Engagement", "fh_tier": "Health tier", "eng_tier": "Engagement tier", "persona": "Segment", "action": "Next best action", "channel": "Channel", "prio": "Priority", "offer": "Offer cap (VND)", "ev": "Call EV (VND)", "rationale": "Why this action", "opportunity": "Opportunity", "matrix_segment": "Matrix segment"}
        fields = [key for key in rename if key in display.columns]
        display = display[fields].rename(columns=rename)
        st.caption(f"Showing up to 100 of {len(filtered):,} matching local full-output records; filters/search apply across the loaded population.")
        st.dataframe(display, hide_index=True, width="stretch", height=460)


def main() -> None:
    data = load_dashboard_data()
    local_output = os.environ.get("BI10_CUSTOMER_OUTPUT_CSV")
    try:
        customers = customer_frame(data, local_output)
    except (OSError, ValueError) as exc:
        st.error(f"Could not load the configured local customer output: {exc}")
        st.stop()
    if local_output and len(customers) != data["meta"]["n_customers"]:
        st.error(f"Full local CSV has {len(customers):,} rows; expected {data['meta']['n_customers']:,} customers.")
        st.stop()
    if local_output:
        data = update_full_population_aggregates(data, customers)
    meta, kpi = data["meta"], data["kpi"]
    fh_profiles = data["fh"]["tier_profile"]
    eng_profiles = data["eng"]["tier_profile"]
    population = sum(fh_profiles[tier]["n"] for tier in ("High", "Medium", "Low"))
    average_fh = sum(fh_profiles[tier]["n"] * fh_profiles[tier]["mean_fhs"] for tier in ("High", "Medium", "Low")) / population
    average_eng = sum(eng_profiles[tier]["n"] * eng_profiles[tier]["mean_eng"] for tier in ("High", "Medium", "Low")) / population
    expected_bad = sum(fh_profiles[tier]["n"] * fh_profiles[tier]["expected_bad"] for tier in ("High", "Medium", "Low")) / population

    st.markdown(
        f"""<header class="hero"><h1>Customer Intelligence 360° Dashboard</h1>
        <p>Financial health, customer engagement, and actionable next-best actions for financial services.</p>
        <div class="meta-line">{fmt_int(meta['n_customers'])} customers · Snapshot {meta['snapshot']} · Calls {meta['call_window'][0][:7]} to {meta['call_window'][1][:7]} · BI Season 10, Round 2</div></header>""",
        unsafe_allow_html=True,
    )
    kpi_cards = st.columns(5)
    kpi_cards[0].metric("Customers scored", fmt_int(population), f"{fmt_int(kpi['n_rows_raw'])} raw rows / 5 tables")
    kpi_cards[1].metric("Average financial health", f"{average_fh:.1f} / 100", f"Expected delinquency {fmt_pct(expected_bad, 2)}")
    kpi_cards[2].metric("Average engagement", f"{average_eng:.1f} / 100", f"{fmt_pct(kpi['active_90d'])} active in last 90 days")
    kpi_cards[3].metric("Top next-best action", fmt_int(kpi["top_nba_count"]), kpi["top_nba"])
    kpi_cards[4].metric("Financial stress tier", fmt_int(kpi["low_fh"]), f"{fmt_pct(kpi['low_fh'] / population)} of scored customers")

    with st.sidebar:
        st.markdown("### Explore the analysis")
        st.markdown(f"Explore full-population aggregate analysis across {fmt_int(meta['n_customers'])} customers and five source tables. No individual records are published in this version.")
        st.markdown("---")
        st.markdown("**Scoring methodology**")
        st.caption("Financial health: 40% repayment, 30% credit standing, 15% DTI, 15% down-payment; policy caps applied after base score.")
        st.caption("Engagement: 20% digital, 20% recency, 25% frequency, 20% responsiveness, 15% product breadth.")
        st.markdown("---")
        st.caption(f"Snapshot {meta['snapshot']}; {fmt_int(meta['n_customers'])} scored customers; {fmt_int(kpi['n_rows_raw'])} raw rows across five source tables.")

    tabs = st.tabs(["Overview", "Challenge 1 · Financial health", "Challenge 2 · Engagement", "Challenge 3 · Segments & actions"])
    with tabs[0]:
        st.subheader("Executive overview")
        st.caption(f"Full-population view: {fmt_int(population)} scored customers; each chart uses the analysis cohort defined for that metric.")
        left, right = st.columns(2)
        with left:
            tiers = ("High", "Medium", "Low")
            tier_counts = pd.DataFrame({"Tier": tiers, "Customers": [fh_profiles[t]["n"] for t in tiers]})
            fig = px.pie(tier_counts, names="Tier", values="Customers", hole=0.58, color="Tier", color_discrete_map=TIER_COLORS,
                         title="Financial health portfolio mix")
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(style_figure(fig, height=350), width="stretch")
        with right:
            tiers = ("High", "Medium", "Low")
            eng_counts = pd.DataFrame({"Tier": tiers, "Customers": [eng_profiles[t]["n"] for t in tiers]})
            fig = px.pie(eng_counts, names="Tier", values="Customers", hole=0.58, color="Tier", color_discrete_map=TIER_COLORS,
                         title="Engagement portfolio mix")
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(style_figure(fig, height=350), width="stretch")
        st.subheader("Business implications")
        implications = [
            ("Protect customers in financial stress", f"{fmt_int(kpi['low_fh'])} are in the low-health tier; {fmt_int(kpi['stressed'])} have stress evidence and {fmt_int(kpi['thin_file'])} are thin-file. Use risk-aware support and avoid overextension."),
            ("Re-engage selectively", f"{fmt_pct(kpi['active_90d'])} were active in the last 90 days and {fmt_pct(kpi['app_users'])} use the app. Route calls by expected value; use lower-cost digital outreach where appropriate."),
            ("Make the next action segment-specific", f"{fmt_int(kpi['call_worthy'])} customers are worth a call under the expected-value rule; prioritize fit, affordability and channel preferences."),
        ]
        for title, copy in implications:
            st.markdown(f"**{title}.** {copy}")
        st.info("Interpret scores as explainable prioritization aids. Validation and descriptive comparisons do not establish that a product, contact, or behavior causes an outcome.")
    with tabs[1]:
        show_financial_health(data)
    with tabs[2]:
        show_engagement(data)
    with tabs[3]:
        show_segments(data, customers)

    st.markdown("---")
    st.caption("Source: BI10 Round 2 analysis snapshot. Portfolio metrics summarize the complete scored customer population and eligible source cohorts. Individual customer records are not bundled in this public demo; scores and actions remain decision support, not causal claims or credit decisions.")


if __name__ == "__main__":
    main()
