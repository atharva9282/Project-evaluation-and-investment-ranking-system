# Project Evaluation & Investment Ranking System (PEIRS)

A lightweight Python application that automatically evaluates project proposals, ranks them and recommends a portfolio under a fixed investment budget.

## Stack

- **Python** — evaluation and optimization logic
- **Streamlit** — complete web interface
- **SQLite** — local persistent database
- **Pandas + Plotly** — tables, charts and dashboard

No separate frontend, backend API, Docker, or database server is required.

## Run locally

Python 3.10 or newer is recommended.

```bash
git clone https://github.com/atharva9282/Project-evaluation-and-investment-ranking-system.git
cd Project-evaluation-and-investment-ranking-system

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit (normally http://localhost:8501).

## Workflow

1. Submit a project with investment, revenue, operating cost, duration, strategic alignment, technical feasibility, expected impact, timeline and risk estimates.
2. PEIRS automatically calculates NPV, IRR (when a root is available), ROI, benefit-cost ratio and payback period.
3. A weighted multi-criteria model produces a score out of 100.
4. The Rankings page orders projects by score, using NPV as a tie-breaker.
5. The Budget Optimizer uses a 0/1 knapsack dynamic program to recommend a combination within the available budget.
6. Adjust criterion weights in Evaluation Criteria. New evaluations use the updated weights; historical results remain unchanged.

## Default criteria weights

| Criterion | Weight |
|---|---:|
| Financial Viability | 25% |
| Strategic Alignment | 20% |
| Technical Feasibility | 15% |
| Expected Impact | 15% |
| Risk Assessment | 15% |
| Implementation Feasibility | 10% |
| **Total** | **100%** |

## Methodology and limitations

The model is deterministic and explainable, not a trained AI/ML model. It evaluates the assumptions entered by the proposal submitter; it does not independently verify revenue, costs, risk or impact claims.

- NPV discounts annual net cash flows at an assumed 8% rate.
- ROI uses total undiscounted net cash flows over the project duration.
- BCR compares discounted benefits with the initial investment plus discounted operating costs.
- IRR is calculated using a bisection method and is shown as unavailable when a reliable root is not bracketed.
- Risk exposure is estimated from the user-entered probability × impact on 1–5 scales.
- Implementation feasibility is a transparent timeline-based proxy.
- Budget optimization uses conservative rounded budget units; the UI reports the granularity used.

The output is a decision-support recommendation, not a final investment approval. Authorized decision-makers should review assumptions, supporting evidence, legal requirements and strategic constraints before committing funds.

## Data

The SQLite database is created automatically as `peirs.db` in the project directory. It is ignored by Git so local project records are not committed.
