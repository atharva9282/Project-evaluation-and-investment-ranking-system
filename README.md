# PEIRS — Project Evaluation and Investment Ranking System

PEIRS is a full-stack project portfolio evaluation application. It uses React/Vite for the user interface, Java 21/Spring Boot for the REST API, and PostgreSQL with Flyway migrations for persistence.

## Start the application

1. Copy `.env.example` to `.env` and change the JWT secret and demo passwords before deployment.
2. Run `docker compose up --build`.
3. Open http://localhost:5173. Swagger UI is at http://localhost:8080/swagger-ui.html.

The database is initialized by Flyway. Development demo accounts (password `ChangeMe123!`): `admin@peirs.local` (ADMIN), `evaluator@peirs.local` (EVALUATOR), `owner@peirs.local` (PROJECT_OWNER), `manager@peirs.local` (INVESTMENT_MANAGER). These credentials are development only.

For local development run PostgreSQL with `docker compose up db`, then start backend with `cd backend && mvn spring-boot:run` and frontend with `cd frontend && npm install && npm run dev`.

## Architecture

`frontend/` contains the React application. `backend/` contains the Spring Boot API, organized by domain and using controller/service/repository layers. Flyway migrations are in `backend/src/main/resources/db/migration`. All financial metrics, risk aggregation, weighted scores, ranking and 0/1 portfolio optimization are computed on the backend.

## API overview

All endpoints are rooted at `/api`. Authentication: `POST /auth/login`, `POST /auth/register`, `GET /auth/me`. Projects: `GET/POST /projects`, `GET/PUT /projects/{id}`, `POST /projects/{id}/submit`. Evaluation: `POST /projects/{id}/evaluations`, `GET /evaluations`. Ranking: `GET /rankings`. Portfolio: `POST /optimization`. Analytics: `GET /analytics`. Criteria and budgets: `GET/PUT /settings/criteria`, `GET/PUT /settings/budget`. OpenAPI is served at `/v3/api-docs`.

## Calculation notes

NPV discounts initial investment and annual net operating cash flows. IRR is solved numerically and is omitted when no valid rate is found. ROI is total net benefit divided by initial investment; payback uses cumulative annual net cash flow; BCR and profitability index use discounted inflows. Criterion weights are validated to total 100. Risk exposure is probability × impact and normalized to a 0–100 penalty before it reduces overall score. The portfolio uses 0/1 dynamic programming with score, expected return, or risk-adjusted return as the objective. Results include selection/exclusion reasoning.

## Security and production

JWT bearer authentication, BCrypt password storage and route-level role checks protect API operations. Set `JWT_SECRET` to a strong random value, change seeded demo credentials, use TLS, and configure production secrets outside source control before deployment.

## Current scope

The repository contains a runnable full-stack foundation and working core workflows for authentication, proposal CRUD, criteria-weighted evaluations, deterministic financial calculations, risk records, ranked results, dashboard aggregates and 0/1 allocation simulation. Seed data adds 12 proposals and four initial evaluations. PDF generation, document binary storage, project assignment administration, decision approval workflow, persisted allocation scenarios, notifications, full audit coverage, and the full integration/authorization/frontend test suite are not implemented yet. The report screen currently exports ranking data as CSV. Do not treat this build as production-ready until those workflows and a production security review are complete.
