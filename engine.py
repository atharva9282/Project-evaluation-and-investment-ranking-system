"""Explainable financial and multi-criteria evaluation engine."""
DEFAULT_WEIGHTS = {
    "Financial Viability": 25,
    "Strategic Alignment": 20,
    "Technical Feasibility": 15,
    "Expected Impact": 15,
    "Risk Assessment": 15,
    "Implementation Feasibility": 10,
}


def clamp(value, low=0.0, high=100.0):
    return max(low, min(high, float(value)))


def npv(rate, cashflows):
    return sum(cf / ((1 + rate) ** year) for year, cf in enumerate(cashflows))


def irr(cashflows):
    """IRR by bisection; returns None when a reliable root is not bracketed."""
    low, high = -0.99, 10.0
    f_low, f_high = npv(low, cashflows), npv(high, cashflows)
    if f_low == 0:
        return low * 100
    if f_low * f_high > 0:
        return None
    for _ in range(250):
        mid = (low + high) / 2
        f_mid = npv(mid, cashflows)
        if abs(f_mid) < 1e-7:
            return mid * 100
        if f_low * f_mid <= 0:
            high = mid
        else:
            low, f_low = mid, f_mid
    return ((low + high) / 2) * 100


def evaluate_project(project, weights=None, discount_rate=0.08):
    weights = weights or DEFAULT_WEIGHTS
    if sum(weights.values()) != 100:
        raise ValueError("Evaluation weights must total 100%.")
    investment = float(project["investment"])
    revenue = float(project["annual_revenue"])
    cost = float(project["annual_cost"])
    years = int(project["years"])
    if investment <= 0 or revenue < 0 or cost < 0 or years < 1:
        raise ValueError("Investment must be positive; revenue/cost non-negative; duration at least one year.")

    net_cashflow = revenue - cost
    cashflows = [-investment] + [net_cashflow] * years
    discounted_benefits = sum(revenue / ((1 + discount_rate) ** y) for y in range(1, years + 1))
    discounted_costs = investment + sum(cost / ((1 + discount_rate) ** y) for y in range(1, years + 1))
    project_npv = npv(discount_rate, cashflows)
    project_roi = ((net_cashflow * years - investment) / investment) * 100
    bcr = discounted_benefits / discounted_costs if discounted_costs else 0
    payback = investment / net_cashflow if net_cashflow > 0 else None
    project_irr = irr(cashflows)

    financial_score = (
        0.50 * clamp(50 + 50 * project_npv / investment)
        + 0.25 * clamp(50 + project_roi / 2)
        + 0.25 * clamp(bcr * 50)
    )
    risk_exposure = int(project["risk_probability"]) * int(project["risk_impact"])
    risk_score = risk_exposure / 25 * 100
    timeline = int(project["timeline"])
    implementation_score = clamp(100 - max(0, timeline - 12) * 2.5, 20, 100)

    criteria = {
        "Financial Viability": round(financial_score, 2),
        "Strategic Alignment": clamp(project["strategic"]),
        "Technical Feasibility": clamp(project["technical"]),
        "Expected Impact": clamp(project["impact"]),
        "Risk Assessment": round(100 - risk_score, 2),
        "Implementation Feasibility": implementation_score,
    }
    score = sum(criteria[name] * weights[name] / 100 for name in weights)
    return {
        "npv": round(project_npv, 2),
        "irr": round(project_irr, 2) if project_irr is not None else None,
        "roi": round(project_roi, 2),
        "bcr": round(bcr, 3),
        "payback": round(payback, 2) if payback is not None else None,
        "risk_score": round(risk_score, 2),
        "criteria": criteria,
        "score": round(score, 2),
    }


def rank_projects(projects):
    ranked = sorted(projects, key=lambda p: (p["score"], p["npv"]), reverse=True)
    for index, project in enumerate(ranked, start=1):
        project["rank"] = index
    return ranked


def optimize_portfolio(projects, budget):
    """0/1 knapsack DP with conservative ₹1,000 units, increasing granularity for large budgets."""
    budget = float(budget)
    unit = max(1000, int((budget / 50000) + 999) // 1000 * 1000)
    capacity = int(budget // unit)
    states = {0: (0.0, [])}
    for project in projects:
        cost_units = int((float(project["investment"]) + unit - 1) // unit)
        if cost_units > capacity:
            continue
        updated = dict(states)
        for used, (value, chosen) in states.items():
            new_used = used + cost_units
            candidate = (value + float(project["score"]), chosen + [project])
            if new_used <= capacity and candidate[0] > updated.get(new_used, (-1, []))[0]:
                updated[new_used] = candidate
        states = updated
    used, (score, chosen) = max(states.items(), key=lambda item: item[1][0])
    total_investment = sum(float(p["investment"]) for p in chosen)
    return {
        "projects": chosen,
        "investment": total_investment,
        "score": score,
        "utilization": total_investment / budget * 100 if budget else 0,
        "note": f"Optimization uses conservative budget units of ₹{unit:,.0f}; this may omit combinations that fit within the budget by a small margin."
    }
