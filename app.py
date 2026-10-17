"""CSAT Copilot: weekly support-quality review of an AI support agent, carried out by AI.

Illustrative demo built by Abel Louis. All markets, conversations and figures are
invented sample data; no real company or customer data is used.
"""

import html
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
MARKET_COLOR = {"Poland": "#2F5BEA", "Estonia": "#E8871E", "Portugal": "#139A9A", "Germany": "#7B4FC9", "Spain": "#A6762B"}
ISO3 = {"Poland": "POL", "Estonia": "EST", "Portugal": "PRT", "Germany": "DEU", "Spain": "ESP"}
ISO2 = {"Poland": "PL", "Estonia": "EE", "Portugal": "PT", "Germany": "DE", "Spain": "ES"}
CENTROID = {"Poland": (52.1, 19.4), "Estonia": (58.7, 25.6), "Portugal": (39.7, -8.0), "Germany": (51.1, 10.4), "Spain": (40.3, -3.7)}

TABLE_CSS = """
<style>
.ct-hint { font-size: 0.85rem; opacity: 0.75; margin: 0 0 6px 0; }
.ct-wrap {
  overflow: scroll; border: 1px solid rgba(128,128,128,0.35); border-radius: 8px;
  scrollbar-width: auto; scrollbar-color: #8A94A3 rgba(128,128,128,0.15);
}
.ct-wrap::-webkit-scrollbar { width: 14px; height: 14px; }
.ct-wrap::-webkit-scrollbar-track { background: rgba(128,128,128,0.15); }
.ct-wrap::-webkit-scrollbar-thumb { background: #8A94A3; border-radius: 7px; border: 3px solid transparent; background-clip: content-box; }
.ct-wrap::-webkit-scrollbar-corner { background: rgba(128,128,128,0.15); }
.ct-table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
.ct-table th {
  position: sticky; top: 0; z-index: 1; text-align: left; font-weight: 600; white-space: nowrap;
  padding: 10px 12px; background: #F0F2F6; color: #31333F; border-bottom: 1px solid rgba(128,128,128,0.35);
}
.ct-table td { padding: 9px 12px; vertical-align: top; line-height: 1.45; border-bottom: 1px solid rgba(128,128,128,0.2); }
.ct-table td.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
.ct-table tr.ok td { background: rgba(46,158,106,0.08); }
@media (prefers-color-scheme: dark) { .ct-table th { background: #262730; color: #FAFAFA; } }
div[data-testid="stTextInput"] div[data-baseweb="input"] { border: 1px solid #B8BEC8 !important; border-radius: 6px; }
</style>
"""


@st.cache_data
def load():
    weekly = pd.read_csv(DATA / "weekly_metrics.csv")
    bridge = pd.read_csv(DATA / "bridge.csv")
    lines = pd.read_csv(DATA / "verticals.csv")
    convs = pd.read_csv(DATA / "conversations.csv")
    return weekly, bridge, lines, convs


def signed(v, dp=1):
    if round(v, dp) == 0:
        return f"{0:.{dp}f}"
    return f"{v:+.{dp}f}".replace("-", "−")


def stretch(fn, *args, **kwargs):
    """Full-width element on both newer (width="stretch") and older Streamlit versions."""
    try:
        return fn(*args, width="stretch", **kwargs)
    except Exception:
        return fn(*args, use_container_width=True, **kwargs)


def choose_one(label, options, default):
    """Segmented buttons where available, horizontal radio buttons otherwise."""
    if st.session_state.get("market") not in options:
        st.session_state["market"] = default
    if hasattr(st, "segmented_control"):
        pick = st.segmented_control(label, options, key="market")
        return pick or default
    return st.radio(label, options, horizontal=True, key="market")


def switch_market(chart_key, traces):
    """Chart click callback: make the clicked line or country the selected market."""
    state = st.session_state.get(chart_key)
    try:
        points = state["selection"]["points"]
    except (KeyError, TypeError):
        return
    by_iso = {v: k for k, v in ISO3.items()}
    for p in points:
        mk = by_iso.get(p.get("location"))
        n = p.get("curve_number")
        if mk is None and n is not None and n < len(traces):
            mk = traces[n]
        if mk is None and n == len(traces):
            i = p.get("point_index", p.get("point_number"))
            if i is not None and i < len(traces):
                mk = traces[i]
        if mk in traces:
            st.session_state["market"] = mk
            return


def choose_many(label, options, key):
    """Toggle pills where available, a multiselect otherwise."""
    fmt = lambda x: f"{MODE_ICON.get(x, '⚪')} {x}"
    if hasattr(st, "pills"):
        pick = st.pills(label, options, selection_mode="multi", default=options, format_func=fmt, key=key)
        return list(pick) if pick else list(options)
    return st.multiselect(label, options, default=options, format_func=fmt, key=key)


def scroll_table(columns, rows, height, min_width, row_class=None):
    """HTML table in a box whose horizontal and vertical scrollbars are always visible.

    columns: list of (header, min_width_px, is_number); rows: list of lists of (text, inline_style).
    """
    head = "".join(
        f'<th style="min-width:{w}px" class="{"num" if n else ""}">{html.escape(h)}</th>' for h, w, n in columns
    )
    body = []
    for i, row in enumerate(rows):
        cls = row_class[i] if row_class else ""
        cells = "".join(
            f'<td class="{"num" if columns[j][2] else ""}" style="{style}">{html.escape(str(text))}</td>'
            for j, (text, style) in enumerate(row)
        )
        body.append(f'<tr class="{cls}">{cells}</tr>')
    st.markdown(
        f'<div class="ct-wrap" style="max-height:{height}px">'
        f'<table class="ct-table" style="min-width:{min_width}px"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


weekly, bridge_all, lines_all, convs_all = load()
st.markdown(TABLE_CSS, unsafe_allow_html=True)

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
        "spot a metric change, let AI review the unresolved support conversations, size each cause, and hand "
        "every fix to a named owner. Every market gets its own review; Poland shows a sharp drop, the others "
        "show how faults and successes can cancel out behind a flat number. All data is invented. Built by Abel Louis."
    )

m = weekly[weekly["market"] == market].set_index("week")
cur, prev = m.loc[cur_w], m.loc[prev_w]
bridge = bridge_all[bridge_all["market"] == market].sort_values("step")
lines = lines_all[lines_all["market"] == market]
convs = convs_all[convs_all["market"] == market]

d_rate = cur["automation_rate"] - prev["automation_rate"]
faults = bridge[bridge["kind"].isin(FAULTS)]
top = faults.sort_values("impact_pts").iloc[0]
win = bridge[bridge["kind"] == "Success factor"].sort_values("impact_pts", ascending=False).iloc[0]
reviewed = int(faults["evidence"].sum())
resolved_sampled = int(bridge.loc[bridge["kind"] == "Success factor", "evidence"].sum())
if d_rate <= -1:
    lead = (f"{market}'s automation rate fell **{signed(d_rate)} points** week on week. "
            f"AI reviewed **{reviewed:,} unresolved support conversations** and traced most of the drop to "
            f"{len(faults)} fixable faults; the largest is **{top['driver']}** ({signed(top['impact_pts'])} pts).")
else:
    lead = (f"{market}'s automation rate moved **{signed(d_rate)} points** week on week, within its normal range. "
            f"AI still reviewed **{reviewed:,} unresolved support conversations** and found {len(faults)} fixable faults "
            f"costing **{signed(faults['impact_pts'].sum())} pts** in total; the largest is **{top['driver']}** "
            f"({signed(top['impact_pts'])} pts). A flat number can hide problems that a success is offsetting.")
st.markdown(lead + f" One change worked and should be reused: **{win['driver']}** ({signed(win['impact_pts'])} pts).")

# ---------- KPIs ----------
k1, k2, k3, k4 = st.columns(4)
k1.metric(f"Automation rate · Week {cur_w}", f"{cur['automation_rate']:.1f}%", f"{d_rate:+.1f} pts vs Week {prev_w}",
          help="Share of support conversations the AI agent resolved with no human.")
k2.metric("Re-contact within 7 days", f"{cur['recontact_7d']:.1f}%",
          f"{cur['recontact_7d'] - prev['recontact_7d']:+.1f} pts", delta_color="inverse",
          help="'Resolved' conversations where the customer came back within 7 days.")
k3.metric("CSAT on AI-handled conversations (1–5)", f"{cur['csat']:.2f}", f"{cur['csat'] - prev['csat']:+.2f}",
          help="Post-conversation survey score.")
k4.metric("Conversations reviewed by AI", f"{reviewed:,}", f"plus {resolved_sampled:,} resolved ones",
          delta_color="off", help="Each labelled with a failure mode or a success factor.")

st.divider()

# ---------- Bridge ----------
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
            x=[f"W{w}" for w in s["week"]], y=s["automation_rate"], mode="lines+markers", name=mk,
            line=dict(color=MARKET_COLOR.get(mk, GREY), width=4 if hot else 2), marker=dict(size=9 if hot else 7),
            opacity=1 if hot else 0.7, hovertemplate=f"{mk}: %{{y:.1f}}%<extra></extra>",
        ))
    tf.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), hovermode="closest",
                     yaxis=dict(ticksuffix="%", gridcolor="rgba(128,128,128,0.15)"),
                     legend=dict(orientation="h", y=-0.15))
    tkey = f"trend_{market}"
    stretch(st.plotly_chart, tf, key=tkey, on_select=lambda k=tkey: switch_market(k, markets), selection_mode="points")
    st.caption("Click a point on any line to switch market. Only Poland broke from its trend this week; the other markets held steady.")
with c2:
    st.markdown(f"**Week {cur_w} automation rate on the map**")
    latest = weekly[weekly["week"] == cur_w].set_index("market")
    before = weekly[weekly["week"] == prev_w].set_index("market")
    mp = go.Figure()
    for mk in markets:
        hot = mk == market
        rate = latest.loc[mk, "automation_rate"]
        chg = rate - before.loc[mk, "automation_rate"]
        colour = MARKET_COLOR.get(mk, GREY)
        mp.add_trace(go.Choropleth(
            locations=[ISO3[mk]], z=[1], colorscale=[[0, colour], [1, colour]], showscale=False,
            marker_line_color="#31333F" if hot else "white", marker_line_width=3 if hot else 0.8, name=mk,
            hovertemplate=f"<b>{mk}</b><br>Week {cur_w}: {rate:.1f}% ({signed(chg)} pts)<extra></extra>",
        ))
    mp.add_trace(go.Scattergeo(
        lat=[CENTROID[mk][0] for mk in markets], lon=[CENTROID[mk][1] for mk in markets],
        text=[f"{ISO2[mk]} {latest.loc[mk, 'automation_rate']:.1f}%" for mk in markets], mode="text",
        textfont=dict(size=12, color="#1F2430"), hoverinfo="skip", showlegend=False,
    ))
    mp.update_geos(scope="europe", projection_type="mercator", lonaxis_range=[-12, 30], lataxis_range=[35, 61],
                   showcountries=True, countrycolor="rgba(128,128,128,0.5)", showland=True,
                   landcolor="rgba(128,128,128,0.12)", bgcolor="rgba(0,0,0,0)", showframe=False)
    mp.update_layout(height=360, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
    mkey = f"map_{market}"
    stretch(st.plotly_chart, mp, key=mkey, on_select=lambda k=mkey: switch_market(k, markets), selection_mode="points")
    st.caption("Colours match the line chart; the selected market has a dark outline. Click a country to switch market.")

st.markdown(f"**{market} by service line, Week {prev_w} vs Week {cur_w}**")
t = lines.drop(columns=["market"]).rename(columns={
    "vertical": "Service line", "share_w40": "Share wk 40 (%)", "share_w41": "Share wk 41 (%)",
    "rate_w40": "Rate wk 40 (%)", "rate_w41": "Rate wk 41 (%)", "change_pts": "Change (pts)",
})
stretch(st.dataframe,
    t.style.format({"Rate wk 40 (%)": "{:.1f}", "Rate wk 41 (%)": "{:.1f}", "Change (pts)": "{:+.1f}"})
    .map(lambda v: f"color: {RED if v < 0 else GREEN}; font-weight: 600", subset=["Change (pts)"]),
    hide_index=True,
)
worst = lines.sort_values("change_pts").iloc[0]
best = lines.sort_values("change_pts").iloc[-1]
st.caption(f"Biggest fall: {worst['vertical']} ({signed(worst['change_pts'])} pts). "
           f"Biggest gain: {best['vertical']} ({signed(best['change_pts'])} pts).")

# ---------- Findings ----------
st.subheader("What AI found, and who fixes it")
st.caption("Sorted by impact. Conversations = reviewed support conversations showing the pattern. "
           "A human owner confirms each finding before the fix goes into the sprint.")
f = bridge[~bridge["kind"].isin(["Start", "End"])].copy()
f["order"] = (f["kind"] == "Success factor").astype(int)
f = f.sort_values(["order", "impact_pts"])
rows, classes = [], []
for _, r in f.iterrows():
    v = r["impact_pts"]
    colour = GREEN if v > 0 and r["kind"] == "Success factor" else (GREY if r["kind"] == "Volume mix" else RED)
    rows.append([
        (r["driver"], "font-weight:600"),
        (r["kind"], ""),
        (f"{signed(v)} pts", f"color:{colour};font-weight:600"),
        (f"{int(r['evidence']):,}" if r["evidence"] else "—", ""),
        (r["finding"], ""),
        (r["fix"], ""),
        (r["owner"], ""),
        (r["status"], "white-space:nowrap"),
    ])
    classes.append("ok" if r["kind"] == "Success factor" else "")
scroll_table(
    [("Driver", 220, False), ("Type", 150, False), ("Impact", 90, True), ("Conversations", 120, True),
     ("What AI found", 380, False), ("Fix", 300, False), ("Owner", 170, False), ("Status", 110, False)],
    rows, height=340, min_width=1500, row_class=classes,
)

# ---------- Conversations ----------
st.subheader("Sample of support conversations reviewed by AI")
st.caption("The evidence behind each finding. Filter by the AI's label or search any word.")
modes = list(convs["failure_mode"].unique())
try:
    fc1, fc2 = st.columns([3, 2], vertical_alignment="bottom")
except TypeError:
    fc1, fc2 = st.columns([3, 2])
with fc1:
    pick = choose_many("Filter by AI label", modes, key=f"labels_{market}")
with fc2:
    q = st.text_input("Search conversations", placeholder="e.g. refund, card, limit", key=f"search_{market}")
cv = convs[convs["failure_mode"].isin(pick)]
if q:
    mask = cv.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)
    cv = cv[mask]
outcome_colour = {"Resolved": GREEN, "Escalated": "#B7791F", "Re-contact": RED}
scroll_table(
    [("Thread ID", 100, False), ("Service line", 130, False), ("Contact reason", 160, False),
     ("AI label", 190, False), ("Outcome", 110, False), ("AI note", 420, False)],
    [[(r["conv_id"], "white-space:nowrap"), (r["vertical"], ""), (r["contact_reason"], ""),
      (f"{MODE_ICON.get(r['failure_mode'], '⚪')} {r['failure_mode']}", "white-space:nowrap"),
      (r["outcome"], f"color:{outcome_colour.get(r['outcome'], GREY)};font-weight:600;white-space:nowrap"),
      (r["ai_note"], "")] for _, r in cv.iterrows()],
    height=380, min_width=1150,
)
st.caption(f"Showing {len(cv)} of {len(convs)} sample support conversations for {market}.")

# ---------- Method ----------
st.divider()
st.subheader("How the review works")
steps = [
    ("Confirm the change is real", "Rule out tracking changes, volume swings and seasonality before acting."),
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
