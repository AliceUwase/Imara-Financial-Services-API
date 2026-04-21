# Imara Financial Services Assessment Shell

This repository is the starter shell for the `2793` Advanced Python assessment sequence. It is intentionally **not** a runnable Django project on day one. You will create your personal repository from GitHub Classroom once in `F1` and continue using that same repository through `F2` and the Summative.

## What this repository provides

- repo hygiene and workflow structure
- the Imara assessment continuity model
- documentation templates for assessed artifacts:
  - `ADR.md`
  - `DECISION_LOG.md`
  - `BUG_REPORT.md`
- a Pull Request template that supports grading, trade-off reasoning, and AI disclosure
- a lightweight CI workflow for repo hygiene only
- public autograding contracts that define the minimum objective checks for each stage

## What you must create yourself in F1

This is part of the learning design. In `F1`, you are expected to bootstrap the application yourself, including:

- the Django project itself
- `manage.py`
- the project configuration package
- installed apps and URL routing
- Django REST Framework setup
- async worker wiring when you implement alerts
- your initial models, serializers, views, and endpoints

## What this repository does not provide

- a prebuilt Django project
- working starter endpoints
- ready-made app modules
- hidden grading tests
- pre-written assessed reasoning
- a solved async or deployment setup

## Repository model for the full module

You accept the GitHub Classroom invitation once in `F1`. After that:

- you keep the same repository through all three assessments
- `main` is the stable branch
- you create a new working branch for each assessment
- you submit the Pull Request URL in Canvas, not the repository URL

### Branch model

| Assessment | Working branch | PR target |
|---|---|---|
| F1 | `f1/mvp` | `main` |
| F2 | `f2/compliance-retrofit` | `main` |
| Summative | `summative/release-hardening` | `main` |

### Recommended student repository naming

`advanced-python-imara-<github-username>`

## Assessment journey

### F1: MVP - Merchant API, Async Alerts, and Performance Foundations

You will use this repo shell to build the first real application increment, including:

- bootstrapping the Django project and configuration
- merchant registration/profile API work
- financing request creation
- lender-facing request listing
- validation and typed implementation
- one async alert flow
- one performance-minded feature such as pagination or caching
- `ADR.md`

### F2: Compliance Retrofit - Auth, RBAC, Privacy, and Auditability

You continue from the same repository and add:

- stronger authentication
- RBAC and access boundaries
- privacy and auditability controls
- updated docs
- `DECISION_LOG.md`

### Summative: Release Hardening - Debug, Test, Deploy, and Defend

You continue from the same repository and harden it through:

- targeted bug fixing
- stronger automated tests
- deployment/runtime configuration
- release-readiness documentation
- `BUG_REPORT.md`

## Local setup

### 1. Clone your GitHub Classroom repository

```bash
git clone <your-classroom-repo-url>
cd advanced-python-imara-<github-username>
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Update values in `.env` as needed for your local setup.

### 5. Bootstrap your Django project and apps

You are expected to create the Django project and the initial application structure yourself during `F1`.

### 6. Install and configure the project components you choose

At minimum, your implementation should introduce:

- a Django project package
- `manage.py`
- DRF-enabled API configuration
- at least the app boundaries needed for your chosen solution
- routing and settings that allow the system to run

### 7. Run the application and worker you build

Once your project exists, document your own run commands in the README.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes | Django application secret |
| `DEBUG` | Yes | Local debug mode |
| `ALLOWED_HOSTS` | Yes | Comma-separated allowed hosts |
| `CELERY_BROKER_URL` | No | Queue broker connection for async alerts |
| `CELERY_RESULT_BACKEND` | No | Async task result backend |

## Minimum repo shape by the end of F1

By the end of `F1`, a grader should be able to see a repository that now contains:

- a Django project created by you
- application modules that support your API design
- environment setup instructions in the README
- `ADR.md`
- API code and documentation or schema evidence
- evidence of async alert handling
- one performance-minded improvement

## Assessed artifact locations

Place these in the repository root when each stage requires them:

- `ADR.md`
- `DECISION_LOG.md`
- `BUG_REPORT.md`

Use the templates in `docs/templates/` as starting points. Replace the prompts with your own decisions and evidence.

## Autograding contract

GitHub Classroom autograding checks only the minimum objective baseline for each stage. Read these before you start work:

- [Runtime Contract](docs/autograding/RUN_CONTRACT.md)
- [F1 Contract](docs/autograding/F1_CONTRACT.md)
- [F2 Contract](docs/autograding/F2_CONTRACT.md)
- [Summative Contract](docs/autograding/SUMMATIVE_CONTRACT.md)

These contracts do not tell you how to design the project. They define the minimum public interface the hidden checks rely on.

## Pull Request workflow

For every assessment:

1. Branch from the current `main`.
2. Complete the work for that stage.
3. Open a Pull Request back into `main`.
4. Submit the Pull Request URL in Canvas.

## AI-use disclosure expectations

Limited AI support is allowed only within course rules. If you use AI, disclose it clearly in your PR and README annex:

- what tool you used
- what you asked it to help with
- what you changed before accepting the output
- what you can explain independently

Do not submit code or reasoning you cannot defend in the technical defense process.

## Integrity and continuity signals

This repo structure is also part of the authorship and integrity model. Over time, graders should be able to see:

- commit history that grows across the trimester
- earlier artifacts still present and improved
- trade-off reasoning that evolves with the codebase
- PR discussion and evidence tied to each assessment stage
