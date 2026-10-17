"""CSAT Copilot: weekly AI quality review for a customer-support AI agent.

Illustrative demo built by Abel Louis. All markets, chats and figures are
invented sample data; no real company or customer data is used.
"""

import textwrap
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="CSAT Copilot", page_icon="📊", layout="wide")

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
    chats = pd.read_csv(DATA / "conversations.csv")
    return weekly, bridge, lines, chats


def signed(v, dp=1):
    return f"{v:+.{dp}f}".replace("-", "−")


weekly, bridge, lines, chats = load()

markets = sorted(weekly["market"].unique())
weeks = sorted(weekly["week"].unique())

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### CSAT Copilot")
    st.caption("Illustrative demo · sample data")
    market = st.selectbox("Market", markets, index=markets.index("Poland") if "Poland" in markets else 0)
    st.markdown(
        "This demo shows how I would run a weekly quality review for a customer-support AI agent: "
        "spot a metric drop, let AI review the failed chats, size each cause, and hand fixes to named owners."
    )
    st.caption("Built by Abel Louis")

cur_w, prev_w = weeks[-1], weeks[-2]
m = weekly[weekly["market"] == market].set_index("week")
cur, prev = m.loc[cur_w], m.loc[prev_w]
has_review = market == "Poland"  # the AI review in this demo covers the market that dropped

# ---------- Header ----------
st.caption("WEEKLY AI QUALITY REVIEW · ILLUSTRATIVE SAMPLE DATA")
st.title(f"Support AI quality review · {market}, week {cur_w}")

d_rate = cur["automation_rate"] - prev["automation_rate"]
if has_review:
    faults = bridge[bridge["kind"].isin(FAULTS)]
    top = faults.sort_values("impact_pts").iloc[0]
    win = bridge[bridge["kind"] == "Success factor"].sort_values("impact_pts", ascending=False).iloc[0]
    reviewed = int(faults["evidence"].sum())
    st.markdown(
        f"{market}'s automation rate moved **{signed(d_rate)} points** week on week. "
        f"The AI review of **{reviewed:,} failed chats** traced most of it to three fixable faults; "
        f"the largest is **{top['driver']}** ({signed(top['impact_pts'])} pts). "
        f"One change worked and should be reused: **{win['driver']}**."
    )
else:
    st.markdown(
        f"{market}'s automation rate moved **{signed(d_rate)} points** week on week, within its normal range. "
        "No AI review was triggered this week. Switch to **Poland** in the sidebar to see a full review."
    )

# ---------- KPIs ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Automation rate · week {cur_w}", f"{cur['automation_rate']:.1f}%", f"{d_rate:+.1f} pts vs week {prev_w}",
          help="Share of chats the AI agent resolved with no human.")
k2.metric("Re-contact within 7 days", f"{cur['recontact_7d']:.1f}%",
          f"{cur['recontact_7d'] - prev['recontact_7d']:+.1f} pts", delta_color="inverse",
          help="'Resolved' chats where the customer came back within 7 days.")
k3.metric("CSAT on AI chats (1–5)", f"{cur['csat']:.2f}", f"{cur['csat'] - prev['csat']:+.2f}",
          help="Post-chat survey score.")
if has_review:
    k4.metric("Chats the AI reviewed", f"{reviewed:,}",
              f"plus {int(bridge.loc[bridge['kind'] == 'Success factor', 'evidence'].sum()):,} successful",
              delta_color="off", help="Each labelled with a failure mode or a success factor.")
else:
    k4.metric("Contacts this week", f"{int(cur['contacts']):,}")

st.divider()

# ---------- Bridge ----------
if has_review:
    st.subheader(f"What moved the automation rate: week {prev_w} to week {cur_w}")
    st.caption(
        "Each bar is one driver the AI found in reviewed chats, sized in percentage points. "
        "Red = fault to fix · green = success to reuse · grey = mix shift, not a quality problem. Hover for the AI's finding."
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
        f"<b>{d}</b><br>{k} · {lab}" + (f" · {int(e):,} chats" if e else "") + f"<br><br>{'<br>'.join(textwrap.wrap(f, 60))}"
        for d, k, lab, e, f in zip(b["driver"], b["kind"], label, b["evidence"], b["finding"])
    ]
    fig = go.Figure(go.Bar(
        x=b["short"], y=b["height"], base=b["base"],
        marker_color=[KIND_COLOR.get(k, GREY) for k in b["kind"]],
        text=label, textposition="outside", cliponaxis=False,
        hovertext=hover, hoverinfo="text",
    ))
    # connector lines between bars
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
    st.plotly_chart(fig, use_container_width=True)
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
    st.plotly_chart(tf, use_container_width=True)
    st.caption("Only Poland broke from its trend, so this is local, not a model-wide regression.")
with c2:
    st.markdown(f"**{'Poland' if has_review else market} by service line, week {prev_w} vs {cur_w}**")
    if has_review:
        t = lines.rename(columns={
            "vertical": "Service line", "share_w40": "Share wk 40 (%)", "share_w41": "Share wk 41 (%)",
            "rate_w40": "Rate wk 40 (%)", "rate_w41": "Rate wk 41 (%)", "change_pts": "Change (pts)",
        })
        st.dataframe(
            t.style.format({"Rate wk 40 (%)": "{:.1f}", "Rate wk 41 (%)": "{:.1f}", "Change (pts)": "{:+.1f}"})
            .map(lambda v: f"color: {RED if v < 0 else GREEN}; font-weight: 600", subset=["Change (pts)"]),
            hide_index=True, use_container_width=True,
        )
        st.caption("Payments and Subscriptions carry the drop; Cards improved.")
    else:
        st.info("Service-line detail is only pulled when a market triggers a review.")

# ---------- Findings ----------
if has_review:
    st.subheader("What the AI found, and who fixes it")
    st.caption("Sorted by impact. Chats = reviewed conversations showing the pattern. "
               "A human owner confirms each finding before the fix goes into the sprint.")
    f = bridge[~bridge["kind"].isin(["Start", "End"])].copy()
    f["order"] = (f["kind"] == "Success factor").astype(int)
    f = f.sort_values(["order", "impact_pts"])
    f["Impact (pts)"] = f["impact_pts"]
    f["Chats"] = f["evidence"].where(f["evidence"] > 0)
    view = f[["driver", "kind", "Impact (pts)", "Chats", "finding", "fix", "owner", "status"]].rename(columns={
        "driver": "Driver", "kind": "Type", "finding": "What the AI found", "fix": "Fix",
        "owner": "Owner", "status": "Status",
    })
    st.dataframe(
        view.style.format({"Impact (pts)": "{:+.1f}", "Chats": "{:,.0f}"}, na_rep="—")
        .map(lambda v: f"color: {GREEN if v > 0 else RED}; font-weight: 600", subset=["Impact (pts)"]),
        hide_index=True, use_container_width=True,
        column_config={"What the AI found": st.column_config.TextColumn(width="large"),
                       "Fix": st.column_config.TextColumn(width="medium")},
    )

    # ---------- Conversations ----------
    st.subheader("Sample of chats the AI reviewed")
    st.caption("The evidence behind each finding. Filter by the AI's label or search any word.")
    modes = list(chats["failure_mode"].unique())
    fc1, fc2 = st.columns([3, 2])
    with fc1:
        pick = st.multiselect("AI label", modes, default=modes,
                              format_func=lambda x: f"{MODE_ICON.get(x, '⚪')} {x}")
    with fc2:
        q = st.text_input("Search chats", placeholder="e.g. refund, charged twice")
    cv = chats[chats["failure_mode"].isin(pick)]
    if q:
        mask = cv.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)
        cv = cv[mask]
    cv = cv.assign(failure_mode=cv["failure_mode"].map(lambda x: f"{MODE_ICON.get(x, '⚪')} {x}"))
    st.dataframe(
        cv.rename(columns={"conv_id": "Chat", "vertical": "Service line", "contact_reason": "Reason",
                           "failure_mode": "AI label", "outcome": "Outcome", "ai_note": "AI note"}),
        hide_index=True, use_container_width=True,
        column_config={"AI note": st.column_config.TextColumn(width="large")},
    )
    st.caption(f"Showing {len(cv)} of {len(chats)} sample chats.")

# ---------- Method ----------
st.divider()
st.subheader("How the review works")
steps = [
    ("Confirm the drop is real", "Rule out tracking changes, volume swings and seasonality before acting."),
    ("Find where it happened", "Slice by market, service line, language, contact reason and release."),
    ("AI reviews the chats", "Each failed chat is labelled: knowledge gap, classification error or logic fault. Successful chats are sampled too."),
    ("Size each driver", "Turn the labels into the bridge, so the team works on the biggest driver first."),
    ("Assign, fix, verify", "A named owner confirms the finding, the fix goes into the sprint, and the metric is tracked daily until it recovers."),
]
cols = st.columns(len(steps))
for i, (col, (title, body)) in enumerate(zip(cols, steps), start=1):
    col.markdown(f"**Step {i} · {title}**")
    col.caption(body)

st.divider()
st.caption(
    "Sample data written for this demo: the markets, chats and figures are illustrative and contain "
    "no real company or customer data. Built by Abel Louis to show how he would run a weekly quality "
    "review for an AI support agent."
)
