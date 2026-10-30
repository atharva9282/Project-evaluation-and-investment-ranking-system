package org.peirs.service;

import org.peirs.model.*;
import org.peirs.repo.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.*;

@Service
public class AutomaticEvaluationService {
    private final UserRepository users;
    private final CriterionRepository criteria;
    private final EvaluationRepository evaluations;
    private final EvaluationScoreRepository evaluationScores;
    private final RiskRepository risks;

    public AutomaticEvaluationService(UserRepository users, CriterionRepository criteria,
            EvaluationRepository evaluations, EvaluationScoreRepository evaluationScores, RiskRepository risks) {
        this.users = users;
        this.criteria = criteria;
        this.evaluations = evaluations;
        this.evaluationScores = evaluationScores;
        this.risks = risks;
    }

    @Transactional
    public Evaluation evaluate(Project project) {
        if (project.investment == null || project.investment.signum() <= 0
                || project.annualRevenue == null || project.annualRevenue.signum() < 0
                || project.annualCost == null || project.annualCost.signum() < 0
                || project.lifespanYears == null || project.lifespanYears < 1) {
            throw new IllegalArgumentException("Provide a positive investment, non-negative revenue/cost and a valid lifespan before submitting");
        }

        List<Criterion> enabled = criteria.findByEnabledTrue();
        if (enabled.isEmpty()) throw new IllegalStateException("Enable at least one evaluation criterion");
        double totalWeight = enabled.stream().mapToDouble(c -> c.weight.doubleValue()).sum();
        if (Math.abs(totalWeight - 100.0) > 0.001) {
            throw new IllegalStateException("Enabled criterion weights must total 100% before automatic evaluation");
        }

        Map<String, Object> financials = FinancialEngine.calculate(
                project.investment.doubleValue(), project.annualRevenue.doubleValue(),
                project.annualCost.doubleValue(), project.lifespanYears, 0.08);
        double npv = ((Number) financials.get("npv")).doubleValue();
        double roi = ((Number) financials.get("roi")).doubleValue();
        double bcr = ((Number) financials.get("bcr")).doubleValue();
        double financialScore = clamp(
                0.50 * clamp(50 + 50 * npv / project.investment.doubleValue(), 0, 100)
                + 0.25 * clamp(roi, 0, 100)
                + 0.25 * clamp(bcr * 50, 0, 100), 0, 100);

        List<ProjectRisk> projectRisks = risks.findByProjectId(project.id);
        // No submitted risk register is treated as an unknown/moderate risk, not as zero risk.
        double exposure = projectRisks.isEmpty() ? 7.5
                : projectRisks.stream().mapToInt(r -> r.probability * r.impact).average().orElse(7.5);
        double riskScore = clamp(exposure * 4, 0, 100);
        double riskCriterionScore = 100 - riskScore;
        double strategicScore = clamp(valueOr(project.strategicImportance, 70), 0, 100);
        double technicalScore = clamp(valueOr(project.technicalFeasibility, 70), 0, 100);
        double impactScore = strategicScore;
        double implementationScore = project.timelineMonths == null ? 70
                : clamp(100 - Math.max(0, project.timelineMonths - 12) * 2, 20, 100);

        Map<String, Double> scores = new LinkedHashMap<>();
        for (Criterion criterion : enabled) {
            String name = criterion.name.toLowerCase(Locale.ROOT);
            double score;
            if (name.contains("financial")) score = financialScore;
            else if (name.contains("strategic")) score = strategicScore;
            else if (name.contains("technical")) score = technicalScore;
            else if (name.contains("impact")) score = impactScore;
            else if (name.contains("risk")) score = riskCriterionScore;
            else if (name.contains("implementation")) score = implementationScore;
            else score = 70.0;
            scores.put(criterion.name, clamp(score, 0, 100));
        }

        double overall = 0;
        for (Criterion criterion : enabled) {
            overall += scores.get(criterion.name) * criterion.weight.doubleValue() / 100.0;
        }

        User evaluator = users.findByEmail("evaluator@peirs.local")
                .orElseGet(() -> users.findAll().stream()
                        .filter(u -> "EVALUATOR".equalsIgnoreCase(u.role)).findFirst()
                        .orElseThrow(() -> new IllegalStateException("No system evaluator account is configured")));

        Evaluation evaluation = evaluations.findByProjectId(project.id).stream()
                .filter(e -> e.evaluator.id.equals(evaluator.id)).findFirst().orElseGet(Evaluation::new);
        if (evaluation.id != null) {
            Long existingEvaluationId = evaluation.id;
            evaluationScores.deleteAll(evaluationScores.findAll().stream()
                    .filter(s -> s.evaluation.id.equals(existingEvaluationId)).toList());
        }
        evaluation.project = project;
        evaluation.evaluator = evaluator;
        evaluation.overallScore = BigDecimal.valueOf(round(overall));
        evaluation.financialScore = BigDecimal.valueOf(round(financialScore));
        evaluation.riskScore = BigDecimal.valueOf(round(riskScore));
        evaluation.comments = "Automatically generated at submission. Financial score combines NPV, ROI and BCR; other scores use proposal attributes, timeline and recorded risk exposure. Review the criterion scores before making an investment decision.";
        evaluation = evaluations.save(evaluation);

        for (Criterion criterion : enabled) {
            evaluationScores.save(new EvaluationScore(evaluation, criterion, scores.get(criterion.name)));
        }
        project.status = "EVALUATED";
        return evaluation;
    }

    private static int valueOr(Integer value, int fallback) { return value == null ? fallback : value; }
    private static double clamp(double value, double min, double max) { return Math.max(min, Math.min(max, value)); }
    private static double round(double value) { return Math.round(value * 100.0) / 100.0; }
}
