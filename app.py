import streamlit as st
import pandas as pd
import plotly.express as px

from database import init_db, add_project, get_projects, get_project, save_weights, get_weights, load_demo_data
from engine import evaluate_project, rank_projects, optimize_portfolio, DEFAULT_WEIGHTS

st.set_page_config(page_title="PEIRS | Investment Intelligence", page_icon="📊", layout="wide")
init_db()

st.markdown("""
<style>
/* PEIRS visual system: high-contrast light canvas with clear card hierarchy */
:root { color-scheme: light; }
.stApp { background: #f3f6fb; color: #172033; }
[data-testid="stHeader"] { background: rgba(243,246,251,.92); }
.block-container { max-width: 1500px; padding: 2rem 2.4rem 3rem; }
h1, h2, h3, h4, p, label, [data-testid="stMarkdownContainer"] { color: #172033; }
h1 { font-weight: 800; letter-spacing: -0.035em; }
h2, h3 { font-weight: 750; letter-spacing: -0.02em; }
[data-testid="stSidebar"] { background: #101b33; }
[data-testid="stSidebar"] * { color: #edf3ff !important; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #b9c7df !important; }
[data-testid="stMetric"] {
  background: #ffffff; border: 1px solid #e3e9f2; border-radius: 16px;
  padding: 20px 22px; box-shadow: 0 5px 18px rgba(24,39,75,.055);
}
[data-testid="stMetricLabel"] p { color: #5d6b82 !important; font-size: .88rem; font-weight: 650; }
[data-testid="stMetricValue"] { color: #14213d !important; font-weight: 800; }
[data-testid="stMetricDelta"] { color: #16845b !important; }
div[data-testid="stForm"], [data-testid="stExpander"] {
  background: #ffffff; border: 1px solid #e3e9f2; border-radius: 16px;
  padding: 18px; box-shadow: 0 4px 16px rgba(24,39,75,.04);
}
.stTextInput input, .stNumberInput input, .stTextArea textarea,
[data-baseweb="select"] > div {
  background: #ffffff !important; color: #172033 !important;
  border-color: #cbd5e1 !important; border-radius: 10px !important;
}
.stSlider [data-baseweb="slider"] { padding-top: .4rem; }
.stButton > button, [data-testid="stFormSubmitButton"] button {
  border-radius: 10px; font-weight: 700; min-height: 2.8rem;
  border: 1px solid #d8e0ed; transition: transform .15s ease, box-shadow .15s ease;
}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
  background: #3157d5; border-color: #3157d5; color: #ffffff;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(49,87,213,.18); }
[data-testid="stDataFrame"], [data-testid="stTable"] {
  background: #ffffff; border: 1px solid #e3e9f2; border-radius: 14px; overflow: hidden;
}
[data-testid="stAlert"] { border-radius: 12px; }
hr { border-color: #e1e7f0; }
small, .stCaption { color: #66758d !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:linear-gradient(115deg,#14264b 0%,#244b9b 58%,#3478c9 100%);
            padding:26px 30px;border-radius:20px;margin-bottom:22px;
            box-shadow:0 12px 28px rgba(30,64,125,.16);">
  <div style="color:#bcd4ff;font-size:.78rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase;">
    Investment intelligence workspace
  </div>
  <div style="color:#ffffff;font-size:2rem;font-weight:850;letter-spacing:-.04em;margin-top:5px;">
    Project Evaluation &amp; Investment Ranking System
  </div>
  <div style="color:#e2ecff;font-size:1rem;margin-top:7px;">
    Automated, explainable project screening and portfolio prioritization
  </div>
</div>
""", unsafe_allow_html=True)

pages = ["Dashboard", "Submit Project", "Rankings", "Budget Optimizer", "Evaluation Criteria"]
page = st.sidebar.radio("Navigation", pages)
st.sidebar.divider()
st.sidebar.caption("PEIRS · Python Edition")
if st.sidebar.button("Load sample projects", use_container_width=True):
    load_demo_data()
    st.sidebar.success("Sample projects loaded.")
    st.rerun()

projects = get_projects()
evaluated = rank_projects(projects)

if page == "Dashboard":
    st.subheader("Investment overview")
    total = len(evaluated)
    investment = sum(p["investment"] for p in evaluated)
    avg_score = sum(p["score"] for p in evaluated) / total if total else 0
    viable = sum(p["npv"] > 0 for p in evaluated)
    a, b, c, d = st.columns(4)
    a.metric("Projects evaluated", total)
    b.metric("Proposed investment", f"₹{investment:,.0f}")
    c.metric("Average score", f"{avg_score:.1f}/100")
    d.metric("Positive NPV projects", viable)
    st.divider()
    if evaluated:
        left, right = st.columns([1.5, 1])
        with left:
            st.markdown("#### Top-ranked projects")
            df = pd.DataFrame(evaluated[:8])[["rank", "name", "sector", "score", "investment"]]
            st.dataframe(df, hide_index=True, use_container_width=True,
                         column_config={"score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f")})
        with right:
            st.markdown("#### Score distribution")
            chart = pd.DataFrame(evaluated)
            st.plotly_chart(px.histogram(chart, x="score", nbins=10, title="Project scores"), use_container_width=True)
        st.markdown("#### Financial attractiveness")
        chart = pd.DataFrame(evaluated)
        st.plotly_chart(px.scatter(chart, x="investment", y="npv", size="score", color="sector",
                                   hover_name="name", title="Investment vs. NPV"), use_container_width=True)
    else:
        st.info("No projects yet. Submit a proposal or load sample projects to explore the system.")

elif page == "Submit Project":
    st.subheader("Submit a project proposal")
    st.write("On submission, PEIRS calculates financial metrics, criterion scores, the overall score and the project rank automatically.")
    with st.form("project_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Project name *")
            owner = st.text_input("Department / project owner")
            sector = st.selectbox("Sector", ["Technology", "Healthcare", "Education", "Infrastructure", "Energy", "Agriculture", "Other"])
            investment = st.number_input("Initial investment (₹) *", min_value=1.0, value=1000000.0, step=100000.0)
            annual_revenue = st.number_input("Expected annual revenue / benefit (₹)", min_value=0.0, value=500000.0, step=50000.0)
            annual_cost = st.number_input("Expected annual operating cost (₹)", min_value=0.0, value=200000.0, step=25000.0)
        with col2:
            years = st.number_input("Project duration (years)", min_value=1, max_value=30, value=5)
            strategic = st.slider("Strategic alignment", 0, 100, 75, help="How strongly does the project support organizational goals?")
            technical = st.slider("Technical feasibility", 0, 100, 75)
            impact = st.slider("Expected impact", 0, 100, 70)
            timeline = st.number_input("Implementation timeline (months)", min_value=1, max_value=120, value=12)
            probability = st.slider("Risk probability (1 = low, 5 = high)", 1, 5, 2)
            severity = st.slider("Risk impact (1 = low, 5 = high)", 1, 5, 3)
        notes = st.text_area("Proposal summary / assumptions")
        submitted = st.form_submit_button("Submit & evaluate automatically", type="primary", use_container_width=True)
    if submitted:
        if not name.strip():
            st.error("Project name is required.")
        elif annual_revenue + annual_cost <= 0:
            st.error("Enter a revenue/benefit or operating cost estimate.")
        else:
            payload = {
                "name": name.strip(), "owner": owner.strip(), "sector": sector,
                "investment": investment, "annual_revenue": annual_revenue,
                "annual_cost": annual_cost, "years": int(years),
                "strategic": strategic, "technical": technical, "impact": impact,
                "timeline": int(timeline), "risk_probability": probability,
                "risk_impact": severity, "notes": notes.strip()
            }
            result = evaluate_project(payload, get_weights())
            add_project(payload, result)
            st.success(f"'{name}' evaluated successfully. Overall score: {result['score']:.2f}/100.")
            st.json({k: result[k] for k in ["npv", "irr", "roi", "bcr", "payback", "risk_score", "score"]})
            st.info("The project is now included in the live rankings. Evaluation is a decision-support estimate, not an investment approval.")

elif page == "Rankings":
    st.subheader("Automated project rankings")
    if evaluated:
        df = pd.DataFrame(evaluated)
        st.dataframe(df[["rank", "name", "owner", "sector", "score", "npv", "roi", "risk_score", "investment"]],
                     hide_index=True, use_container_width=True,
                     column_config={"score": st.column_config.ProgressColumn("Overall score", min_value=0, max_value=100, format="%.2f"),
                                    "investment": st.column_config.NumberColumn("Investment (₹)", format="₹%.0f"),
                                    "npv": st.column_config.NumberColumn("NPV (₹)", format="₹%.0f"),
                                    "roi": st.column_config.NumberColumn("ROI", format="%.1f%%")})
        choice = st.selectbox("View evaluation breakdown", [p["name"] for p in evaluated])
        selected = next(p for p in evaluated if p["name"] == choice)
        st.markdown(f"#### {selected['name']} · Rank #{selected['rank']}")
        st.metric("Weighted evaluation score", f"{selected['score']:.2f}/100")
        st.bar_chart(pd.DataFrame({"Criterion": list(selected["criteria"].keys()), "Score": list(selected["criteria"].values())}).set_index("Criterion"))
        st.write(f"**Financials:** NPV ₹{selected['npv']:,.0f} · ROI {selected['roi']:.1f}% · BCR {selected['bcr']:.2f} · Payback {selected['payback']}")
    else:
        st.info("Submit or load projects to generate rankings.")

elif page == "Budget Optimizer":
    st.subheader("Budget-constrained investment selection")
    if evaluated:
        budget = st.number_input("Available investment budget (₹)", min_value=1.0,
                                 value=float(max(1000000, sum(p["investment"] for p in evaluated) * 0.5)), step=100000.0)
        if st.button("Optimize portfolio", type="primary"):
            result = optimize_portfolio(evaluated, budget)
            selected_count = len(result["projects"])
            m1, m2, m3 = st.columns(3)
            m1.metric("Selected investment", f"₹{result['investment']:,.0f}")
            m2.metric("Projects selected", selected_count)
            m3.metric("Investment-weighted portfolio score", f"{result['portfolio_score']:.1f}/100")
            remaining = budget - result["investment"]
            st.progress(min(result["utilization"] / 100, 1.0), text=f"Budget utilized · {result['utilization']:.1f}%")
            st.caption(f"Unallocated budget: ₹{remaining:,.0f}")
            if result["projects"]:
                st.markdown("#### Recommended project portfolio")
                portfolio_df = pd.DataFrame(result["projects"])[["rank", "name", "sector", "investment", "score", "npv"]]
                st.dataframe(portfolio_df, hide_index=True, use_container_width=True,
                             column_config={
                                 "investment": st.column_config.NumberColumn("Investment (₹)", format="₹%.0f"),
                                 "score": st.column_config.ProgressColumn("Project score", min_value=0, max_value=100, format="%.1f"),
                                 "npv": st.column_config.NumberColumn("NPV (₹)", format="₹%.0f")
                             })
                st.success("Recommended portfolio calculated. Final selection remains subject to authorized review.")
            else:
                st.warning("No project fits within the available budget.")
            st.caption(result["note"])
    else:
        st.info("Add evaluated projects before optimizing a portfolio.")

elif page == "Evaluation Criteria":
    st.subheader("Evaluation criteria and weights")
    st.write("Weights must total exactly 100%. Changes apply to new evaluations; existing project scores are not silently rewritten.")
    weights = get_weights()
    with st.form("weights_form"):
        updated = {}
        cols = st.columns(2)
        for i, (criterion, weight) in enumerate(weights.items()):
            with cols[i % 2]:
                updated[criterion] = st.number_input(criterion, min_value=0, max_value=100, value=int(weight), step=1)
        total_weight = sum(updated.values())
        st.caption(f"Total weight: {total_weight}%")
        save = st.form_submit_button("Save criteria weights", type="primary")
    if save:
        if total_weight != 100:
            st.error("Criteria weights must total exactly 100%.")
        else:
            save_weights(updated)
            st.success("Criteria weights saved.")
    st.divider()
    st.markdown("**Scoring approach**")
    st.markdown("""
    - Financial viability: NPV, ROI and benefit-cost ratio.
    - Strategic alignment, technical feasibility and expected impact: proposal inputs scored on a 0–100 scale.
    - Risk assessment: probability × impact, converted into a risk-resilience score.
    - Implementation feasibility: a transparent timeline-based proxy.
    - Overall score: weighted sum of the criterion scores.
    """)
    st.caption("This is a deterministic, explainable model. It does not claim to use a trained AI/ML model or independently verify proposal assumptions.")
