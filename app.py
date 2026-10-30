import streamlit as st
import pandas as pd
import plotly.express as px

from database import init_db, add_project, get_projects, get_project, save_weights, get_weights, load_demo_data
from engine import evaluate_project, rank_projects, optimize_portfolio, DEFAULT_WEIGHTS

st.set_page_config(page_title="PEIRS | Investment Intelligence", page_icon="📊", layout="wide")
init_db()

st.markdown("""
<style>
.block-container {padding-top: 1.8rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background: #f5f7fb; padding: 16px; border-radius: 12px;}
div[data-testid="stForm"] {border: 1px solid #e5e7eb; padding: 20px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("Project Evaluation & Investment Ranking System")
st.caption("Automated, explainable project screening and portfolio prioritization")

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
            st.metric("Selected investment", f"₹{result['investment']:,.0f}")
            st.metric("Combined evaluation score", f"{result['score']:.2f}")
            st.write(f"Budget utilization: {result['utilization']:.1f}%")
            if result["projects"]:
                st.dataframe(pd.DataFrame(result["projects"])[["name", "investment", "score", "npv"]], hide_index=True, use_container_width=True)
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
