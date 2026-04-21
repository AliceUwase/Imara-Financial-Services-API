# Instructor Setup Notes

This template is intended to be published as a **private template repository** under the `ALU-BSE` GitHub organization.

## Recommended repository settings

- Repository name: `advanced-python-imara-template`
- Visibility: `Private`
- Template repository: `Enabled`
- Default branch: `main`

## GitHub Classroom usage

Create **one GitHub Classroom assignment for F1 only** using this template. Students should create their repository once and continue using it through all assessed stages.

Recommended assignment title:

- `2793 Continuous Assessment Repository`

Recommended template settings:

- individual assignment
- private student repositories
- default branch only
- feedback pull requests enabled
- autograding run mode: every time a student submits

Recommended student repository naming pattern:

`advanced-python-imara-<github-username>`

## Student branch model

- `f1/mvp -> main`
- `f2/compliance-retrofit -> main`
- `summative/release-hardening -> main`

## Canvas submission model

Students submit:

- Pull Request URL for the current stage

Students do not submit:

- a fresh repository URL
- a ZIP file as the primary submission
- a new repository for later stages

## Suggested protection and review rules

If classroom or organization settings allow, prefer:

- no direct pushes to `main`
- Pull Request required for merges
- CI required before merge
- history preserved so repo continuity remains visible for integrity review

## Autograding dependencies

Before creating the GitHub Classroom assignment, make sure:

- the public contract docs in `docs/autograding/` are present
- `.github/workflows/classroom.yml` is on `main`
- the private companion repo `ALU-BSE/advanced-python-imara-autograde-private` exists
- student repositories receive the `AUTOGRADE_REPO_TOKEN` secret

Recommended protected workflow paths in Classroom:

- `.github/workflows/classroom.yml`
- `.github/workflows/ci.yml`

## Instructor-only assets

Do not add hidden autograder files, private grading keys, or staff-only answer artifacts into the student template repository. Keep those in:

- GitHub Classroom autograding configuration
- private instructor repos
- local grading workflows
