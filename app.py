"""CSAT Copilot: weekly support-quality review of an AI support agent, carried out by AI.

Illustrative demo built by Abel Louis. All markets, conversations and figures are
invented sample data; no real company or customer data is used.
"""

import textwrap
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="CSAT Copilot", page_icon="📊", layout="wide", initial_sidebar_state="collapsed")

DATA = Path(__file__).parent
RED, GREEN, GREY, BLUE = "#D64545", "#2E9E6A", "#9AA3AE", "#2F5BEA"
FAULTS = ["Knowledge gap", "Classification error", "Logic fault"]
KIND_COLOR = {
    "Start": BLUE, "End": BLUE, "Success factor": GREEN, "Volume mix": GREY,
    "Knowledge gap": RED, "Classification error": RED, "Logic fault": RED,
}
MODE_ICON = {
    "Knowledge gap": "🔴", "Classification error": "🟠", "Logic fault": "🟣", "Success": "🟢",
}


@st.cache_data
def load():
    weekly = pd.read_csv(DATA / "weekly_metrics.csv")
    bridge = pd.read_csv(DATA / "bridge.csv").sort_values("step")
    lines = pd.read_csv(DATA / "verticals.csv")
    convs = pd.read_csv(DATA / "conversations.csv")
    return weekly, bridge, lines, convs


def signed(v, dp=1):
    return f"{v:+.{dp}f}".replace("-", "−")


def stretch(fn, *args, **kwargs):
    """Full-width element on both newer (width="stretch") and older Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except Exception:
        return fn(*args, use_container_width=True, **kwargs)


def choose_one(label, options, default):
    """Segmented buttons where available, horizontal radio buttons otherwise."""
    if hasattr(st, "segmented_control"):
        pick = st.segmented_control(label, options, default=default, key="market")
        return pick or default
    return st.radio(label, options, index=options.index(default), horizontal=True, key="market")


def choose_many(label, options):
    """Toggle pills where available, a multiselect otherwise."""
    fmt = lambda x: f"{MODE_ICON.get(x, '⚪')} {x}"
    if hasattr(st, "pills"):
        pick = st.pills(label, options, selection_mode="multi", default=options, format_func=fmt, key="labels")
        return list(pick) if pick else list(options)
    return st.multiselect(label, options, default=options, format_func=fmt, key="labels")


weekly, bridge, lines, convs = load()

markets = sorted(weekly["market"].unique())
weeks = sorted(weekly["week"].unique())
cur_w, prev_w = weeks[-1], weeks[-2]

# ---------- Header and market choice ----------
st.caption("CSAT COPILOT · ILLUSTRATIVE DEMO WITH SAMPLE DATA")
title_slot = st.empty()
market = choose_one("Choose a market to review", markets, "Poland" if "Poland" in markets else markets[0])
title_slot.title(f"Support quality, reviewed by AI · {market} · Week {cur_w}")

with st.expander("About this demo"):
    st.markdown(
        "This demo shows how I would run a weekly quality review of a customer-support AI agent: "
        "spot a metric drop, let AI review the failed support conversations, size each cause, and hand "
        "every fix to a named owner. Hover the bridge chart for the AI's findings, switch markets above, "
        "and filter the reviewed conversations at the bottom. All data is invented. Built by Abel Louis."
    )

m = weekly[weekly["market"] == market].set_index("week")
cur, prev = m.loc[cur_w], m.loc[prev_w]
has_review = market == "Poland"  # the AI review in this demo covers the market that dropped

d_rate = cur["automation_rate"] - prev["automation_rate"]
if has_review:
    faults = bridge[bridge["kind"].isin(FAULTS)]
    top = faults.sort_values("impact_pts").iloc[0]
    win = bridge[bridge["kind"] == "Success factor"].sort_values("impact_pts", ascending=False).iloc[0]
    reviewed = int(faults["evidence"].sum())
    st.markdown(
        f"{market}'s automation rate moved **{signed(d_rate)} points** week on week. "
        f"AI reviewed **{reviewed:,} unresolved support conversations** and traced most of the drop to three fixable faults; "
        f"the largest is **{top['driver']}** ({signed(top['impact_pts'])} pts). "
        f"One change worked and should be reused: **{win['driver']}**."
    )
else:
    st.markdown(
        f"{market}'s automation rate moved **{signed(d_rate)} points** week on week, within its normal range, "
        "so no AI review was triggered this week. Choose **Poland** above to see a full review."
    )

# ---------- KPIs ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Automation rate · Week {cur_w}", f"{cur['automation_rate']:.1f}%", f"{d_rate:+.1f} pts vs Week {prev_w}",
          help="Share of support conversations the AI agent resolved with no human.")
k2.metric("Re-contact within 7 days", f"{cur['recontact_7d']:.1f}%",
          f"{cur['recontact_7d'] - prev['recontact_7d']:+.1f} pts", delta_color="inverse",
          help="'Resolved' conversations where the customer came back within 7 days.")
k3.metric("CSAT on AI-handled conversations (1–5)", f"{cur['csat']:.2f}", f"{cur['csat'] - prev['csat']:+.2f}",
          help="Post-conversation survey score.")
if has_review:
    k4.metric("Conversations reviewed by AI", f"{reviewed:,}",
              f"plus {int(bridge.loc[bridge['kind'] == 'Success factor', 'evidence'].sum()):,} resolved ones",
              delta_color="off", help="Each labelled with a failure mode or a success factor.")
else:
    k4.metric("Support conversations this week", f"{int(cur['contacts']):,}")

st.divider()

# ---------- Bridge ----------
if has_review:
    st.subheader(f"What moved the automation rate: Week {prev_w} to Week {cur_w}")
    st.caption(
        "Each bar is one driver AI found in the reviewed support conversations, sized in percentage points. "
        "Red = fault to fix · green = success to reuse · grey = mix shift, not a quality problem. Hover a bar for the AI's finding."
    )
    b = bridge.copy()
    run, base, height = 0.0, [], []
    for _, r in b.iterrows():
        if r["kind"] in ("Start", "End"):
            base.append(0.0); height.append(r["impact_pts"]); run = r["impact_pts"]
        else:
            lo = run + min(0, r["impact_pts"])
            base.append(lo); height.append(abs(r["impact_pts"])); run += r["impact_pts"]
    b["base"], b["height"] = base, height
    tops = [x + h for x, h in zip(base, height)] + [x for x, k in zip(base, b["kind"]) if k not in ("Start", "End")]
    y_lo, y_hi = int(min(tops)) - 3, int(max(tops)) + 2
    label = [
        f"{v:.1f}%" if k in ("Start", "End") else f"{signed(v)} pts"
        for v, k in zip(b["impact_pts"], b["kind"])
    ]
    hover = [
        f"<b>{d}</b><br>{k} · {lab}" + (f" · {int(e):,} conversations" if e else "") + f"<br><br>{'<br>'.join(textwrap.wrap(f, 60))}"
        for d, k, lab, e, f in zip(b["driver"], b["kind"], label, b["evidence"], b["finding"])
    ]
    fig = go.Figure(go.Bar(
        x=b["short"], y=b["height"], base=b["base"],
        marker_color=[KIND_COLOR.get(k, GREY) for k in b["kind"]],
        text=label, textposition="outside", cliponaxis=False,
        hovertext=hover, hoverinfo="text",
    ))
    level = 0.0
    for i, (_, r) in enumerate(b.iterrows()):
        level = r["impact_pts"] if r["kind"] in ("Start", "End") else level + r["impact_pts"]
        if i < len(b) - 1:
            fig.add_shape(type="line", x0=i + 0.4, x1=i + 0.6, y0=level, y1=level,
                          line=dict(color="#8A94A3", width=1, dash="dot"))
    fig.update_layout(
        height=420, margin=dict(l=10, r=10, t=30, b=10), showlegend=False,
        yaxis=dict(range=[y_lo, y_hi], ticksuffix="%", title=None, gridcolor="rgba(128,128,128,0.15)"),
        xaxis=dict(title=None),
        hoverlabel=dict(align="left"),
    )
    stretch(st.plotly_chart, fig)
    st.caption(f"Axis starts at {y_lo}% to show the change.")

# ---------- Where it happened ----------
st.subheader("Where it happened")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Automation rate by market, last 8 weeks**")
    tf = go.Figure()
    for mk in markets:
        s = weekly[weekly["market"] == mk].sort_values("week")
        hot = mk == market
        tf.add_trace(go.Scatter(
            x=[f"W{w}" for w in s["week"]], y=s["automation_rate"], mode="lines+markers" if hot else "lines",
            name=mk, line=dict(color=BLUE if hot else GREY, width=3 if hot else 1.5),
            hovertemplate=f"{mk}: %{{y:.1f}}%<extra></extra>",
        ))
    tf.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified",
                     yaxis=dict(ticksuffix="%", gridcolor="rgba(128,128,128,0.15)"),
                     legend=dict(orientation="h", y=-0.2))
    stretch(st.plotly_chart, tf)
    st.caption("Only Poland broke from its trend, so this is local, not a model-wide regression.")
with c2:
    st.markdown(f"**{market} by service line, Week {prev_w} vs Week {cur_w}**")
    if has_review:
        t = lines.rename(columns={
            "vertical": "Service line", "share_w40": "Share wk 40 (%)", "share_w41": "Share wk 41 (%)",
            "rate_w40": "Rate wk 40 (%)", "rate_w41": "Rate wk 41 (%)", "change_pts": "Change (pts)",
        })
        stretch(st.dataframe,
            t.style.format({"Rate wk 40 (%)": "{:.1f}", "Rate wk 41 (%)": "{:.1f}", "Change (pts)": "{:+.1f}"})
            .map(lambda v: f"color: {RED if v < 0 else GREEN}; font-weight: 600", subset=["Change (pts)"]),
            hide_index=True,
        )
        st.caption("Payments and Subscriptions carry the drop; Cards improved.")
    else:
        st.info("Service-line detail is only pulled when a market triggers a review.")

# ---------- Findings ----------
if has_review:
    st.subheader("What AI found, and who fixes it")
    st.caption("Sorted by impact. Conversations = reviewed support conversations showing the pattern. "
               "A human owner confirms each finding before the fix goes into the sprint.")
    f = bridge[~bridge["kind"].isin(["Start", "End"])].copy()
    f["order"] = (f["kind"] == "Success factor").astype(int)
    f = f.sort_values(["order", "impact_pts"])
    f["Impact (pts)"] = f["impact_pts"]
    f["Conversations"] = f["evidence"].where(f["evidence"] > 0)
    view = f[["driver", "kind", "Impact (pts)", "Conversations", "finding", "fix", "owner", "status"]].rename(columns={
        "driver": "Driver", "kind": "Type", "finding": "What AI found", "fix": "Fix",
        "owner": "Owner", "status": "Status",
    })
    stretch(st.dataframe,
        view.style.format({"Impact (pts)": "{:+.1f}", "Conversations": "{:,.0f}"}, na_rep="—")
        .map(lambda v: f"color: {GREEN if v > 0 else RED}; font-weight: 600", subset=["Impact (pts)"]),
        hide_index=True,
        column_config={"What AI found": st.column_config.TextColumn(width="large"),
                       "Fix": st.column_config.TextColumn(width="medium")},
    )

    # ---------- Conversations ----------
    st.subheader("Sample of support conversations reviewed by AI")
    st.caption("The evidence behind each finding. Filter by the AI's label or search any word.")
    modes = list(convs["failure_mode"].unique())
    pick = choose_many("Filter by AI label", modes)
    q = st.text_input("Search conversations", placeholder="e.g. refund, charged twice")
    cv = convs[convs["failure_mode"].isin(pick)]
    if q:
        mask = cv.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)
        cv = cv[mask]
    cv = cv.assign(failure_mode=cv["failure_mode"].map(lambda x: f"{MODE_ICON.get(x, '⚪')} {x}"))
    stretch(st.dataframe,
        cv.rename(columns={"conv_id": "Thread ID", "vertical": "Service line", "contact_reason": "Contact reason",
                           "failure_mode": "AI label", "outcome": "Outcome", "ai_note": "AI note"}),
        hide_index=True,
        column_config={"AI note": st.column_config.TextColumn(width="large")},
    )
    st.caption(f"Showing {len(cv)} of {len(convs)} sample support conversations.")

# ---------- Method ----------
st.divider()
st.subheader("How the review works")
steps = [
    ("Confirm the drop is real", "Rule out tracking changes, volume swings and seasonality before acting."),
    ("Find where it happened", "Slice by market, service line, language, contact reason and release."),
    ("AI reviews the conversations", "Each unresolved support conversation is labelled: knowledge gap, classification error or logic fault. Resolved ones are sampled too."),
    ("Size each driver", "Turn the labels into the bridge, so the team works on the biggest driver first."),
    ("Assign, fix, verify", "A named owner confirms the finding, the fix goes into the sprint, and the metric is tracked daily until it recovers."),
]
cols = st.columns(len(steps))
for i, (col, (title, body)) in enumerate(zip(cols, steps), start=1):
    col.markdown(f"**Step {i} · {title}**")
    col.caption(body)

st.divider()
st.caption(
    "Sample data written for this demo: the markets, support conversations and figures are illustrative and "
    "contain no real company or customer data. Built by Abel Louis to show how he would run a weekly quality "
    "review of an AI support agent."
)
