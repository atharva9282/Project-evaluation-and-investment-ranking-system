package org.peirs.api;

import org.peirs.model.*;
import org.peirs.repo.*;
import org.peirs.service.*;
import org.springframework.web.bind.annotation.*;
import org.springframework.http.*;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.*;
import java.math.*;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import java.nio.charset.StandardCharsets;
import org.springframework.beans.factory.annotation.Value;

@RestController
@RequestMapping("/api")
public class ApiController {
    private final UserRepository users;
    private final ProjectRepository projects;
    private final CriterionRepository criteria;
    private final EvaluationRepository evaluations;
    private final EvaluationScoreRepository evaluationScores;
    private final RiskRepository risks;
    private final PasswordEncoder passwords;
    @Value("${app.jwt-secret}")
    String secret;

    public ApiController(UserRepository u, ProjectRepository p, CriterionRepository c, EvaluationRepository e,
            EvaluationScoreRepository es, RiskRepository r, PasswordEncoder pw) {
        users = u;
        projects = p;
        criteria = c;
        evaluations = e;
        evaluationScores = es;
        risks = r;
        passwords = pw;
    }

    public record Login(String email, String password) {
    }

    public record Register(@NotBlank String name, @Email String email, @Size(min = 8) String password) {
    }

    public record EvalRequest(Long evaluatorId, Map<String, Double> scores, String comments) {
    }

    public record OptimizationRequest(double budget, String strategy) {
    }

    public record Weights(Map<String, Double> weights) {
    }

    @PostMapping("/auth/login")
    public Map<String, Object> login(@RequestBody Login x) {
        User u = users.findByEmail(x.email()).orElseThrow(() -> new RuntimeException("Invalid credentials"));
        if (!passwords.matches(x.password(), u.passwordHash))
            throw new RuntimeException("Invalid credentials");
        String token = Jwts.builder().subject(u.email).claim("role", u.role)
                .signWith(Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8))).compact();
        return Map.of("token", token, "user", Map.of("id", u.id, "name", u.name, "email", u.email, "role", u.role));
    }

    @PostMapping("/auth/register")
    public Map<String, Object> register(@Valid @RequestBody Register x) {
        User u = users.save(new User(x.name(), x.email(), passwords.encode(x.password()), "PROJECT_OWNER"));
        return Map.of("id", u.id, "name", u.name, "email", u.email, "role", u.role);
    }

    @GetMapping("/auth/me")
    public Map<String, Object> me(org.springframework.security.core.Authentication auth) {
        User u = users.findByEmail(auth.getName()).orElseThrow();
        return Map.of("id", u.id, "name", u.name, "email", u.email, "role", u.role);
    }

    @GetMapping("/projects")
    public List<Project> list(@RequestParam(required = false) String status, @RequestParam(required = false) String q) {
        List<Project> all = status == null ? projects.findAll() : projects.findByStatus(status);
        return q == null ? all
                : all.stream().filter(p -> p.title.toLowerCase().contains(q.toLowerCase())
                        || p.projectCode.toLowerCase().contains(q.toLowerCase())).toList();
    }

    @PostMapping("/projects")
    public Project create(@RequestBody Project p) {
        p.id = null;
        p.projectCode = "PEI-" + UUID.randomUUID().toString().substring(0, 8).toUpperCase();
        if (p.status == null)
            p.status = "DRAFT";
        return projects.save(p);
    }

    @GetMapping("/projects/{id}")
    public Project get(@PathVariable Long id) {
        return projects.findById(id).orElseThrow();
    }

    @PutMapping("/projects/{id}")
    public Project update(@PathVariable Long id, @RequestBody Project p) {
        Project old = get(id);
        if (!old.status.equals("DRAFT"))
            throw new IllegalStateException("Only draft proposals can be edited");
        p.id = id;
        p.projectCode = old.projectCode;
        p.owner = old.owner;
        return projects.save(p);
    }

    @PostMapping("/projects/{id}/submit")
    public Project submit(@PathVariable Long id) {
        Project p = get(id);
        p.status = "SUBMITTED";
        return projects.save(p);
    }

    @GetMapping("/projects/{id}/financials")
    public Map<String, Object> financial(@PathVariable Long id,
            @RequestParam(defaultValue = "0.08") double discountRate) {
        Project p = get(id);
        return FinancialEngine.calculate(p.investment.doubleValue(), p.annualRevenue.doubleValue(),
                p.annualCost.doubleValue(), p.lifespanYears, discountRate);
    }

    @GetMapping("/projects/{id}/risks")
    public Map<String, Object> risk(@PathVariable Long id) {
        var rs = risks.findByProjectId(id);
        double avg = rs.stream().mapToInt(x -> x.probability * x.impact).average().orElse(0);
        return Map.of("risks", rs, "exposure", avg, "severity", avg >= 16 ? "HIGH" : avg >= 9 ? "MEDIUM" : "LOW");
    }

    @PostMapping("/projects/{id}/risks")
    public ProjectRisk addRisk(@PathVariable Long id, @RequestBody ProjectRisk r) {
        r.id = null;
        r.project = get(id);
        return risks.save(r);
    }

    @PostMapping("/projects/{id}/evaluations")
    @Transactional
    public Evaluation evaluate(@PathVariable Long id, @RequestBody EvalRequest x) {
        Project p = get(id);
        User u = users.findById(x.evaluatorId()).orElseThrow();
        var cs = criteria.findByEnabledTrue();
        double sum = cs.stream().mapToDouble(c -> c.weight.doubleValue()).sum();
        if (Math.abs(sum - 100) > 0.001)
            throw new IllegalStateException("Enabled criterion weights must total 100%");
        double score = 0;
        for (Criterion c : cs) {
            Double v = x.scores().get(c.name);
            if (v == null || v < 0 || v > 100)
                throw new IllegalArgumentException("Provide 0–100 score for " + c.name);
            score += v * c.weight.doubleValue() / 100;
        }
        double exposure = risks.findByProjectId(id).stream().mapToInt(r -> r.probability * r.impact).average()
                .orElse(0);
        double riskScore = Math.min(100, exposure / 25 * 100);
        score = Math.max(0, score - riskScore * 0.15);
        Evaluation e = new Evaluation();
        e.project = p;
        e.evaluator = u;
        e.overallScore = BigDecimal.valueOf(Math.round(score * 100) / 100.0);
        e.financialScore = BigDecimal.valueOf(x.scores().getOrDefault("Financial Viability", 0.0));
        e.riskScore = BigDecimal.valueOf(riskScore);
        e.comments = x.comments();
        e = evaluations.save(e);
        for (Criterion c : cs)
            evaluationScores.save(new EvaluationScore(e, c, x.scores().get(c.name)));
        p.status = "EVALUATED";
        projects.save(p);
        return e;
    }

    @GetMapping("/evaluations")
    public List<Evaluation> evals() {
        return evaluations.findAll();
    }

    @GetMapping("/rankings")
    public List<Map<String, Object>> rankings() {
        List<Map<String, Object>> out = new ArrayList<>();
        for (Project p : projects.findAll()) {
            List<Evaluation> es = evaluations.findByProjectId(p.id);
            if (es.isEmpty())
                continue;
            double score = es.stream().mapToDouble(e -> e.overallScore.doubleValue()).average().orElse(0);
            double risk = es.stream().mapToDouble(e -> e.riskScore.doubleValue()).average().orElse(0);
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("id", p.id);
            row.put("projectCode", p.projectCode);
            row.put("title", p.title);
            row.put("category", p.category);
            row.put("investment", p.investment);
            row.put("score", score);
            row.put("risk", risk);
            row.put("financialScore", es.stream().mapToDouble(e -> e.financialScore.doubleValue()).average().orElse(0));
            row.put("roi", FinancialEngine.calculate(p.investment.doubleValue(), p.annualRevenue.doubleValue(),
                    p.annualCost.doubleValue(), p.lifespanYears, .08).get("roi"));
            row.put("recommendation", score >= 80 ? "HIGH PRIORITY"
                    : score >= 65 ? "RECOMMENDED" : score >= 50 ? "CONDITIONAL" : "NOT RECOMMENDED");
            row.put("explanation", "Aggregated evaluator score adjusted for project risk.");
            out.add(row);
        }
        out.sort((a, b) -> Double.compare(((Number) b.get("score")).doubleValue(),
                ((Number) a.get("score")).doubleValue()));
        return out;
    }

    @PostMapping("/optimization")
    public Map<String, Object> optimize(@RequestBody OptimizationRequest x) {
        List<OptimizationEngine.Item> items = rankings().stream().map(r -> {
            Project p = get(((Number) r.get("id")).longValue());
            return new OptimizationEngine.Item(p.id, p.title, p.investment.intValue(),
                    ((Number) r.get("score")).doubleValue(), p.annualRevenue.doubleValue() - p.annualCost.doubleValue(),
                    ((Number) r.get("risk")).doubleValue());
        }).toList();
        return OptimizationEngine.optimize(items, (int) x.budget(), x.strategy() == null ? "SCORE" : x.strategy());
    }

    @GetMapping("/analytics")
    public Map<String, Object> analytics() {
        var ps = projects.findAll();
        long eval = ps.stream().filter(p -> p.status.equals("EVALUATED")).count(),
                approved = ps.stream().filter(p -> p.status.equals("APPROVED") || p.status.equals("FUNDED")).count(),
                rejected = ps.stream().filter(p -> p.status.equals("REJECTED")).count();
        double investment = ps.stream().mapToDouble(p -> p.investment.doubleValue()).sum();
        double avg = rankings().stream().mapToDouble(x -> ((Number) x.get("score")).doubleValue()).average().orElse(0);
        return Map.of("totalProjects", ps.size(), "underEvaluation",
                ps.stream().filter(p -> p.status.equals("UNDER_REVIEW") || p.status.equals("EVALUATION_IN_PROGRESS"))
                        .count(),
                "evaluated", eval, "approved", approved, "rejected", rejected, "proposedInvestment", investment,
                "averageScore", avg, "highRiskProjects",
                risks.findAll().stream().map(r -> r.project.id).distinct().count(), "byCategory",
                ps.stream()
                        .collect(java.util.stream.Collectors.groupingBy(p -> p.category,
                                java.util.stream.Collectors.counting())),
                "byStatus", ps.stream().collect(
                        java.util.stream.Collectors.groupingBy(p -> p.status, java.util.stream.Collectors.counting())));
    }

    @GetMapping("/settings/criteria")
    public List<Criterion> getCriteria() {
        return criteria.findAll();
    }

    @PutMapping("/settings/criteria")
    public List<Criterion> setCriteria(@RequestBody List<Criterion> values) {
        double sum = values.stream().filter(c -> c.enabled).mapToDouble(c -> c.weight.doubleValue()).sum();
        if (Math.abs(sum - 100) > .001)
            throw new IllegalArgumentException("Enabled weights must total exactly 100%");
        return criteria.saveAll(values);
    }
}
