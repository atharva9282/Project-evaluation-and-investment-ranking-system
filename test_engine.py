import unittest
from engine import DEFAULT_WEIGHTS, evaluate_project, irr, optimize_portfolio, rank_projects


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.project = {
            "investment": 100000, "annual_revenue": 50000, "annual_cost": 10000,
            "years": 5, "strategic": 80, "technical": 75, "impact": 90,
            "timeline": 12, "risk_probability": 2, "risk_impact": 3,
        }

    def test_financial_metrics_and_score(self):
        result = evaluate_project(self.project)
        self.assertGreater(result["npv"], 0)
        self.assertGreater(result["score"], 0)
        self.assertLessEqual(result["score"], 100)
        self.assertEqual(result["risk_score"], 24.0)

    def test_irr(self):
        self.assertAlmostEqual(irr([-100, 60, 60]), 13.0662, places=2)

    def test_weights_must_total_100_and_include_all_criteria(self):
        with self.assertRaises(ValueError):
            evaluate_project(self.project, {"Only criterion": 100})
        with self.assertRaises(ValueError):
            evaluate_project(self.project, {**DEFAULT_WEIGHTS, "Extra": 0})

    def test_ranking(self):
        rows = [{"name": "A", "score": 70, "npv": 10}, {"name": "B", "score": 90, "npv": 5}]
        self.assertEqual(rank_projects(rows)[0]["name"], "B")

    def test_budget_optimizer_respects_budget(self):
        rows = [
            {"name": "A", "investment": 50000, "score": 80, "npv": 1000},
            {"name": "B", "investment": 40000, "score": 70, "npv": 900},
            {"name": "C", "investment": 90000, "score": 95, "npv": 1200},
        ]
        result = optimize_portfolio(rows, 100000)
        self.assertLessEqual(result["investment"], 100000)
        self.assertTrue(result["projects"])

    def test_optimizer_rejects_non_positive_budget(self):
        with self.assertRaises(ValueError):
            optimize_portfolio([], 0)


if __name__ == "__main__":
    unittest.main()
