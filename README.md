# CSAT Bridge - Copilot

A Streamlit demo of a weekly quality review for a customer-support AI agent.

It follows one story: in week 41 the agent's automation rate in one market drops 8 points. An AI review of the unresolved support conversations finds three fixable faults (a knowledge gap, a classification error and a logic fault), a volume-mix effect, and one success factor worth reusing. The dashboard sizes each cause in a bridge chart, shows where it happened, and hands every fix to a named owner.

**All data is illustrative sample data.** Markets, support conversations and figures are invented; no real company or customer data is used.

## What to try

1. Hover the bars in the bridge chart to read the AI's finding for each driver.
2. Switch the market with the buttons at the top: only Poland breaks from its trend.
3. Filter the reviewed support conversations by AI label, or search for "charged twice".

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Files

| File | What it holds |
| --- | --- |
| `app.py` | The Streamlit app |
| `weekly_metrics.csv` | Weekly automation rate, re-contact rate, CSAT and contacts by market |
| `bridge.csv` | Drivers of the week-on-week change, with the AI's finding, owner, fix and status |
| `verticals.csv` | Contact share and automation rate by service line |
| `conversations.csv` | Sample reviewed support conversations with the AI's label and note |

Built by Abel Louis.
