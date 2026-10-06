"""Streamlit dashboard for the Distributed Returns Optimization Agent.

Run:
    streamlit run app.py

All logic comes from the shared service layer (src/service.py). The UI never
reads raw CSVs, never shows customer comments, and never shows exact counts.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.privacy.local_privacy import SIGNAL_SCORE
from src.service import ReturnsOptimizationService

st.set_page_config(page_title="Distributed Returns Optimizer", page_icon="📦", layout="wide")

# Reference palette: one hue for single-series charts, reserved status colours.
SERIES = "#2a78d6"
SIGNAL_COLORS = {"Emerging": "#86b6ef", "Medium": "#3987e5", "High": "#1c5cab"}
GOOD, CRITICAL = "#0ca30c", "#e34948"
DECISION_ICON = {"APPROVED": "✅ APPROVED", "SUPPRESSED": "⛔ SUPPRESSED"}


@st.cache_resource(show_spinner="Connecting retailer nodes...")
def get_service() -> ReturnsOptimizationService:
    """Cached service: holds only nodes, coordinator and protected results."""
    return ReturnsOptimizationService()


def chart_layout(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=30, b=10), plot_bgcolor="rgba(0,0,0,0)",
                      paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
    fig.update_xaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


svc = get_service()
st.session_state.setdefault("drafts", [])
st.session_state.setdefault("plan", None)

# ---- sidebar -------------------------------------------------------------------
with st.sidebar:
    st.header("📦 Distributed Returns Optimizer")
    st.write("Three retailers analyse returns **locally** and share only protected, banded summaries.")
    st.subheader("Privacy rules")
    st.markdown("- ≥ **3** local records per retailer\n- ≥ **2** contributing retailers\n"
                "- ≥ **5** combined eligible records\n- Banded output only — no exact counts")
    st.subheader("Demo status")
    if svc.data_available:
        st.success("3 retailer nodes connected · synthetic data")
    else:
        st.error("Retailer data missing")
    st.subheader("Navigation")
    st.caption("1 Overview → 2 Patterns → 3 Planner → 4 Forecast → 5 Privacy & MCP → 6 Classification Lab")
    if st.button("Re-run privacy evaluation", disabled=not svc.data_available):
        svc.refresh()
        st.toast("Fresh evaluation complete")

if not svc.data_available:
    st.error("Retailer data files were not found. Run `python generate_data.py` in the project folder, "
             "then reload this page.")
    for node in svc.get_system_status()["nodes"]:
        st.caption(f"{node['name']}: {node['detail']}")
    st.stop()

status = svc.get_system_status()
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1 · Executive Overview", "2 · Protected Pattern Explorer",
                                              "3 · Intervention Planner", "4 · Impact Forecast",
                                              "5 · Privacy & MCP Audit", "6 · Classification Lab"])

# ---- Tab 1: overview -------------------------------------------------------------
with tab1:
    st.title("Distributed Returns Optimization Agent")
    st.write("Retailers learn **why** products come back — without exposing customers, orders, return rates, "
             "or their own weaknesses. Each retailer classifies returns locally; a privacy coordinator releases "
             "only patterns that several retailers share.")
    cols = st.columns(3)
    for col, node in zip(cols, status["nodes"]):
        with col.container(border=True):
            st.markdown(f"**🏬 {node['name']}**")
            st.markdown(f"{'🟢' if node['connected'] else '🔴'} {node['status']}")
            st.caption("Local classification complete · raw data stays local")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Approved collective patterns", status["approved_patterns"])
    m2.metric("Suppressed evaluations", status["suppressed_evaluations"])
    top = status["strongest_driver"]
    m3.metric("Strongest anonymous driver", f"{top['category']} · {top['cause']}" if top else "—")
    m4.metric("Interventions available", status["interventions_available"])
    if top:
        st.info(f"💡 {top['explanation']}")
    st.subheader("Architecture")
    st.markdown("""
| Retailer nodes (local) | | Privacy coordinator | | Shared layer |
|---|---|---|---|---|
| Raw CSVs → local classifier → local aggregate (≥3) | ➜ | Diversity ≥2 · combined ≥5 · banding · audit | ➜ | 4 agents → MCP tools & this dashboard |
""")
    st.warning("Prototype with **synthetic, fictional data**. Privacy uses thresholding and banding, not "
               "production-grade differential privacy or cryptography.")

# ---- Tab 2: pattern explorer ----------------------------------------------------------
with tab2:
    st.header("Protected Pattern Explorer")
    st.caption("Only approved cross-retailer patterns are shown. Signal strength is a band, not a count.")
    all_patterns = svc.analyze_patterns()
    f1, f2 = st.columns(2)
    cat_filter = f1.selectbox("Product category", ["All"] + sorted({p["category"] for p in all_patterns}))
    sig_filter = f2.selectbox("Signal strength", ["All", "High", "Medium", "Emerging"])
    patterns = svc.analyze_patterns(category=None if cat_filter == "All" else cat_filter,
                                    signal=None if sig_filter == "All" else sig_filter)
    if not patterns:
        st.warning("No approved pattern matches these filters. Try a broader category or signal.")
    else:
        df = pd.DataFrame(patterns)
        df["pattern"] = df["category"] + " · " + df["cause"]
        df["signal_score"] = df["signal_strength"].map(SIGNAL_SCORE)
        df["description"] = df["cause"].map(lambda c: svc.intelligence.get_cause_description(c)["label"])
        chart_df = df.iloc[::-1]
        fig = go.Figure(go.Bar(
            x=chart_df["signal_score"], y=chart_df["pattern"], orientation="h",
            marker_color=[SIGNAL_COLORS[s] for s in chart_df["signal_strength"]],
            customdata=chart_df[["signal_strength", "contributor_band", "confidence"]],
            hovertemplate="%{y}<br>Signal: %{customdata[0]}<br>Contributors: %{customdata[1]}"
                          "<br>Confidence: %{customdata[2]:.2f}<extra></extra>"))
        fig.update_xaxes(tickvals=[1, 2, 3], ticktext=["Emerging", "Medium", "High"], range=[0, 3.3],
                         title="Signal strength (banded)")
        st.plotly_chart(chart_layout(fig, max(260, 34 * len(df))), width="stretch")
        st.dataframe(df[["category", "cause", "description", "signal_strength", "contributor_band", "confidence",
                         "privacy_status"]], hide_index=True, width="stretch")
        st.download_button("⬇ Download protected patterns (CSV)",
                           df[["category", "cause", "signal_strength", "contributor_band", "confidence",
                               "privacy_status"]].to_csv(index=False), "protected_patterns.csv", "text/csv")
        with st.expander("Cause descriptions"):
            for cause in sorted(df["cause"].unique()):
                d = svc.intelligence.get_cause_description(cause)
                st.markdown(f"**{d['label']}** (`{cause}`) — {d['description']}")

    st.subheader("Category × cause signal map")
    st.caption("Banded signal per combination. Blank cells were not released (suppressed or never observed).")
    mx = pd.DataFrame(svc.category_cause_matrix())
    mx = mx[mx.groupby("cause")["signal_score"].transform("max") > 0]
    grid = mx.pivot(index="category", columns="cause", values="signal_score")
    labels = mx.pivot(index="category", columns="cause", values="signal_strength")
    heat = go.Figure(go.Heatmap(
        z=grid.where(grid > 0).values, x=list(grid.columns), y=list(grid.index), zmin=1, zmax=3, xgap=2, ygap=2,
        colorscale=[[0, SIGNAL_COLORS["Emerging"]], [0.5, SIGNAL_COLORS["Medium"]], [1, SIGNAL_COLORS["High"]]],
        customdata=labels.values, hovertemplate="%{y} · %{x}<br>%{customdata}<extra></extra>",
        colorbar=dict(tickvals=[1, 2, 3], ticktext=["Emerging", "Medium", "High"], title="Signal")))
    st.plotly_chart(chart_layout(heat, 320), width="stretch")

# ---- Tab 3: intervention planner ---------------------------------------------------------
with tab3:
    st.header("Intervention Planner")
    categories = svc.approved_categories()
    c1, c2 = st.columns(2)
    p_cat = c1.selectbox("Approved category", categories,
                         index=categories.index("Electronics") if "Electronics" in categories else 0)
    causes = svc.approved_causes(p_cat)
    p_cause = c2.selectbox("Approved cause", causes)
    details = svc.get_pattern_details(p_cat, p_cause)
    st.info(f"**{details['cause_details']['label']}** — {details['cause_details']['description']}  \n"
            f"Signal: **{details['signal_strength']}** · Contributors: **{details['contributor_band']}** · "
            f"Confidence: **{details['confidence']:.2f}**")
    pre = svc.get_pre_purchase_recommendations(p_cause)
    post = svc.get_post_purchase_recommendations(p_cause)
    left, right = st.columns(2)
    with left:
        st.subheader("🛒 Pre-purchase")
        for i in pre:
            with st.container(border=True):
                st.markdown(f"**{i['name']}** · effort {i['effort']} · impact {i['expected_impact']}")
                st.caption(f"{i['description']}  \nPlacement: {i['placement']}")
    with right:
        st.subheader("🤝 Post-purchase")
        for i in post:
            with st.container(border=True):
                st.markdown(f"**{i['name']}** · effort {i['effort']} · satisfaction "
                            f"{i['expected_satisfaction_impact']}")
                st.caption(f"{i['description']}  \nChannel: {i['channel']} · 🔒 Draft — human approval required")
    with st.expander("📊 Prioritisation matrix: impact vs effort", expanded=True):
        im = pd.DataFrame(svc.intervention_matrix(p_cause))
        rank = im.groupby(["effort_score", "impact_score"]).cumcount()
        size = im.groupby(["effort_score", "impact_score"])["id"].transform("count")
        im["x"] = im["effort_score"] + (rank - (size - 1) / 2) * 0.15  # spread overlapping points
        sc = go.Figure()
        for stage, symbol in (("Pre-purchase", "circle"), ("Post-purchase", "diamond")):
            d = im[im["stage"] == stage]
            sc.add_trace(go.Scatter(x=d["x"], y=d["impact_score"], mode="markers", name=stage,
                                    text=d["name"], marker=dict(size=14, symbol=symbol, color=SERIES,
                                                                line=dict(width=2, color="white")),
                                    customdata=d[["quadrant", "effort", "expected_impact"]],
                                    hovertemplate="%{text}<br>%{customdata[0]}<br>Effort %{customdata[1]} · "
                                                  "Impact %{customdata[2]}<extra>" + stage + "</extra>"))
        sc.update_xaxes(tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"], range=[0.5, 3.5], title="Effort")
        sc.update_yaxes(tickvals=[1, 2, 3], ticktext=["Low", "Medium", "High"], range=[0.5, 3.5],
                        title="Expected impact")
        sc.add_annotation(x=1.0, y=3.4, text="Quick wins ↖", showarrow=False, font=dict(color="#52514e"))
        chart_layout(sc, 360).update_layout(showlegend=True, legend=dict(orientation="h", y=1.12))
        st.plotly_chart(sc, width="stretch")
        st.dataframe(im[["name", "stage", "effort", "expected_impact", "quadrant"]], hide_index=True,
                     width="stretch")
    options = {i["id"]: f"Pre · {i['name']}" for i in pre} | {i["id"]: f"Post · {i['name']}" for i in post}
    chosen = st.selectbox("Select one intervention", list(options), format_func=options.get)
    if st.button("Generate implementation plan", type="primary"):
        st.session_state.plan = svc.build_intervention_plan(p_cat, p_cause, chosen)
    plan = st.session_state.plan
    if plan and plan["cause"] == p_cause and plan["category"] == p_cat:
        with st.container(border=True):
            st.subheader(f"Plan: {plan['intervention']}")
            a, b, c = st.columns(3)
            a.metric("Effort", plan["effort"])
            b.metric("Expected impact", plan["expected_impact"])
            c.metric("Stage", plan["stage"])
            st.markdown(f"**Cause:** {plan['cause_label']} (`{plan['cause']}`) in {plan['category']}  \n"
                        f"**Placement / channel:** {plan['placement_or_channel']}  \n"
                        f"**What to build:** {plan['description']}  \n"
                        f"**Success metric:** {plan['success_metric']}  \n"
                        f"**Guardrails:** {', '.join(plan['guardrails'])}  \n"
                        f"**Risks:** {', '.join(plan['risks'])}  \n"
                        f"**Suggested experiment:** {plan['suggested_experiment']['design']} — primary metric "
                        f"*{plan['suggested_experiment']['primary_metric']}*")
            if plan["requires_human_approval"]:
                st.warning("🔒 Customer-facing action: remains a DRAFT until a human approves it.")
            st.download_button("⬇ Download plan (Markdown)", svc.plan_to_markdown(plan),
                               f"plan_{plan['intervention_id']}.md", "text/markdown")
            with st.expander("Technical details (JSON)"):
                st.json(plan)
    with st.expander("🔎 Search the intervention knowledge base"):
        q = st.text_input("Keyword", placeholder="e.g. exchange, size, packaging")
        hits = svc.search_knowledge(q)
        if q and not hits:
            st.info("No interventions match that keyword.")
        elif hits:
            st.dataframe(pd.DataFrame(hits), hide_index=True, width="stretch")

# ---- Tab 4: forecast ---------------------------------------------------------------------
with tab4:
    st.header("Impact Forecast")
    st.caption("📐 **Scenario projection**, not a measured result: you enter the affected volume, and "
               "predefined demonstration assumptions are applied.")
    approved = svc.analyze_patterns()
    cause_options = list(dict.fromkeys(p["cause"] for p in approved))
    f1, f2 = st.columns(2)
    f_cause = f1.selectbox("Approved cause", cause_options, key="f_cause")
    interventions = svc.get_pre_purchase_recommendations(f_cause) + svc.get_post_purchase_recommendations(f_cause)
    names = {i["id"]: i["name"] for i in interventions}
    f_int = f2.selectbox("Intervention", list(names), format_func=names.get, key="f_int")
    f3, f4 = st.columns(2)
    volume = int(f3.number_input("Affected return volume (scenario)", min_value=0, max_value=1_000_000,
                                 value=100, step=10))
    duration = int(f4.number_input("Test duration (days)", min_value=1, max_value=180, value=14, step=7))
    fc = svc.forecast_impact(f_cause, f_int, volume, test_duration_days=duration)
    pr = fc["prevented_returns"]
    k1, k2, k3 = st.columns(3)
    k1.metric("Low (projection)", pr["low"])
    k2.metric("Expected (projection)", pr["expected"])
    k3.metric("High (projection)", pr["high"])
    fig = go.Figure(go.Bar(x=["Low", "Expected", "High"], y=[pr["low"], pr["expected"], pr["high"]],
                           marker_color=SERIES, text=[pr["low"], pr["expected"], pr["high"]],
                           textposition="outside",
                           hovertemplate="%{x}: %{y} prevented returns (projection)<extra></extra>"))
    fig.update_yaxes(title="Projected prevented returns", rangemode="tozero")
    st.plotly_chart(chart_layout(fig, 300), width="stretch")
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Confidence", f"{fc['confidence']:.2f}")
    d2.metric("Satisfaction effect", fc["satisfaction_effect"])
    d3.metric("Cost level", fc["implementation_cost"])
    d4.metric("Impact band", fc["impact_band"])
    st.markdown(f"**Recommended validation:** {fc['recommended_validation']}  \n"
                f"**Guardrails:** {', '.join(fc['guardrails'])}")
    st.warning(f"⚠️ {fc['warning']}")

    st.subheader("Portfolio scenario")
    st.caption("Combine several interventions for the same cause. Effects overlap on the same returns, so they "
               "are combined as 1 − ∏(1 − pᵢ) rather than added.")
    chosen_ids = st.multiselect("Interventions in the portfolio", list(names), default=list(names)[:2],
                                format_func=names.get, max_selections=6)
    if chosen_ids:
        pf = svc.forecast_portfolio(f_cause, chosen_ids, volume)
        pdf = pd.DataFrame(pf["interventions"] + [{"name": "Combined portfolio", **pf["combined_prevented_returns"]}])
        bars = go.Figure(go.Bar(
            y=pdf["name"], x=pdf["expected"], orientation="h",
            marker_color=[SERIES] * (len(pdf) - 1) + [SIGNAL_COLORS["High"]],
            error_x=dict(type="data", symmetric=False, array=pdf["high"] - pdf["expected"],
                         arrayminus=pdf["expected"] - pdf["low"], color="#8a8984", thickness=2),
            hovertemplate="%{y}<br>Expected %{x} (projection)<extra></extra>"))
        bars.update_xaxes(title="Projected prevented returns (expected, with low–high range)", rangemode="tozero")
        bars.update_yaxes(autorange="reversed")
        st.plotly_chart(chart_layout(bars, 100 + 45 * len(pdf)), width="stretch")
        c = pf["combined_prevented_returns"]
        st.markdown(f"**Combined projection:** {c['low']} / **{c['expected']}** / {c['high']} prevented returns "
                    f"(overlap adjustment −{pf['overlap_adjustment']} versus adding the expected values).")

    st.subheader("Create a support-intervention draft")
    post_actions = svc.get_post_purchase_recommendations(f_cause)
    action = st.selectbox("Post-purchase action", post_actions, format_func=lambda a: a["name"])
    if st.button("Create draft"):
        draft = svc.create_support_draft(f_cause, action["name"], action["channel"])
        st.session_state.drafts.append(draft)
    if st.session_state.drafts:
        with st.expander(f"Draft queue ({len(st.session_state.drafts)}): awaiting human review, none sent"):
            st.dataframe(pd.DataFrame(st.session_state.drafts)[["draft_id", "cause", "action", "channel", "status",
                                                                "requires_human_approval", "customer_contacted"]],
                         hide_index=True, width="stretch")
    for d in reversed(st.session_state.drafts[-1:]):
        st.success(f"📝 **{d['draft_id']}** · {d['action']} · {d['channel']} · status **{d['status']}** · "
                   f"human approval required · {d['message']}")

# ---- Tab 5: privacy & MCP -------------------------------------------------------------------
with tab5:
    st.header("Privacy & MCP Audit")
    audit = svc.get_privacy_audit()
    t = audit["thresholds"]
    a, b, c = st.columns(3)
    a.metric("Local record threshold", t["local_min_records"])
    b.metric("Collective threshold", t["collective_min_records"])
    c.metric("Retailer diversity threshold", t["min_retailers"])
    for rule in audit["rules"]:
        st.markdown(f"- **{rule['rule']}** — {rule['detail']}")

    st.subheader("Audit events")
    ev = pd.DataFrame(audit["events"])
    ev["decision"] = ev["decision"].map(DECISION_ICON)
    ev["contributor_band"] = ev["contributor_band"].fillna("—")
    choice = st.radio("Show", ["All", "Approved", "Suppressed"], horizontal=True)
    if choice != "All":
        ev = ev[ev["decision"].str.contains(choice.upper())]
    st.dataframe(ev[["decision", "category", "cause", "reason", "privacy_rule", "contributor_band", "timestamp"]],
                 hide_index=True, width="stretch")

    st.download_button("⬇ Download audit log (CSV)", pd.DataFrame(audit["events"]).to_csv(index=False),
                       "privacy_audit.csv", "text/csv")

    st.subheader("🧪 Privacy policy simulator")
    st.caption("Try a *stricter* policy and see what would still be released. The simulation releases and "
               "logs nothing, and the policy floor (3 / 2 / 5) cannot be lowered.")
    s1, s2, s3 = st.columns(3)
    sim_local = s1.slider("Local minimum records", t["local_min_records"], 8, t["local_min_records"])
    sim_div = s2.slider("Minimum retailers", t["min_retailers"], 3, t["min_retailers"])
    sim_coll = s3.slider("Collective minimum records", t["collective_min_records"], 20, t["collective_min_records"])
    sim = svc.simulate_privacy_policy(sim_local, sim_div, sim_coll)
    q1, q2 = st.columns(2)
    q1.metric("Patterns released under this policy", sim["approved_under_policy"],
              delta=sim["approved_under_policy"] - sim["approved_under_current_policy"])
    q2.metric("Patterns released under current policy", sim["approved_under_current_policy"])
    if sim["patterns_that_would_be_withheld"]:
        st.caption("Would be withheld: " + ", ".join(f"{w['category']} · {w['cause']}"
                                                      for w in sim["patterns_that_would_be_withheld"]))

    blocked = audit["blocked_single_retailer_example"]
    if blocked:
        st.error(f"⛔ **Blocked single-retailer pattern:** {blocked['category']} · {blocked['cause']} — "
                 f"{blocked['reason']}. Only one retailer had enough records, so nothing about it is released.")

    st.subheader("MCP tools")
    st.caption("MCP standardizes access to tools; privacy is enforced by the application's thresholding and "
               "output controls.")
    st.dataframe(pd.DataFrame(svc.get_mcp_tool_summary()), hide_index=True, width="stretch")

    l, r = st.columns(2)
    with l:
        st.subheader("Never shared")
        st.markdown("\n".join(f"- `{f}`" for f in audit["never_shared_fields"]))
    with r:
        st.subheader("Prototype limitations")
        st.markdown("\n".join(f"- {x}" for x in audit["limitations"]))

    with st.expander("Mock OMS: sanitized order context (local demo)"):
        oid = st.selectbox("Example local order reference", svc.example_order_ids())
        ctx = svc.get_sanitized_order_context(oid)
        st.caption("Only these four fields leave the order system:")
        st.json({k: v for k, v in ctx.items() if k != "found"})

# ---- Tab 6: classification lab --------------------------------------------------------------
with tab6:
    st.header("Classification Lab")
    st.caption("Try the transparent keyword classifier on your own text. It is rule-based, not a trained model. "
               "Text is processed in memory and is never stored, logged, or shared.")
    examples = ["The case does not fit my phone.", "Shoe was too tight.", "Table looked larger online.",
                "Could not connect Bluetooth.", "Arrived cracked.", "Package was late.", "Caused a rash on my skin."]
    ex = st.selectbox("Start from an example", ["(type your own)"] + examples)
    l1, l2 = st.columns([1, 2])
    reason = l1.text_input("Return reason (optional)", max_chars=200)
    comment = l2.text_input("Customer comment", value="" if ex == "(type your own)" else ex, max_chars=500)
    if comment or reason:
        res = svc.classify_text(reason, comment)
        r1, r2, r3 = st.columns(3)
        r1.metric("Cause", res["label"])
        r2.metric("Confidence", f"{res['confidence']:.2f}")
        r3.metric("Rule applied", res["rule"])
        if res["matched_keywords"]:
            st.markdown("**Matched keywords:** " + " ".join(f"`{k}`" for k in res["matched_keywords"]))
        else:
            st.info("No keyword matched, so this falls back to OTHER. Recurring OTHER themes are candidates for "
                    "new taxonomy keywords, reviewed locally by each retailer.")
    with st.expander("Taxonomy definitions"):
        for cause in svc.intelligence.known_causes():
            d = svc.intelligence.get_cause_description(cause)
            st.markdown(f"**{d['label']}** (`{cause}`): {d['taxonomy_definition']}")
