# Runtime Contract

This document defines the minimum runtime assumptions used by the hidden autograding checks for the `2793` continuous assessment repository.

## Scope

These checks are an objective baseline only. They do not replace manual grading of:

- architecture reasoning
- documentation quality
- trade-off judgment
- technical defense
- integrity review

## Required root files

The repository must contain:

- `README.md`
- `requirements.txt`
- `.env.example`

By the end of `F1`, the repository must also contain:

- `manage.py`

## Required install path

Your repository must install successfully with:

```bash
pip install -r requirements.txt
```

## Required Django bootstrap path

By the end of `F1`, the repository must support:

```bash
python manage.py check
python manage.py migrate --noinput
```

The hidden checks assume `manage.py` sets `DJANGO_SETTINGS_MODULE` correctly for local execution.

## Required environment behavior

Your project must run with a local `.env` created from `.env.example`.

The hidden checks do not require production credentials. They expect the project to work with a local SQLite or similarly lightweight development configuration.

## Branch-specific grading

The hidden workflow only grades these assessment branches:

- `f1/mvp`
- `f2/compliance-retrofit`
- `summative/release-hardening`

All assessment Pull Requests must target `main`.
