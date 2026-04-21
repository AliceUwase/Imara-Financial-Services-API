# Publish to ALU-BSE

The local template repository is ready to publish. If the current GitHub account does not have `CreateRepository` permission in `ALU-BSE`, use an account or token that does.

## Target repository

- Organization: `ALU-BSE`
- Repository: `advanced-python-imara-template`
- Visibility: `private`
- Template repository: `enabled`

## Publish commands

Run these from the repository root:

```bash
gh repo create ALU-BSE/advanced-python-imara-template \
  --private \
  --source=. \
  --remote=origin \
  --push \
  --description "Starter template for the ALU BSE Advanced Python cumulative assessment sequence."
```

Then enable template mode:

```bash
gh repo edit ALU-BSE/advanced-python-imara-template --template
```

## Suggested follow-up checks

- confirm the repository is private
- confirm template mode is enabled
- confirm `main` is the default branch
- confirm GitHub Classroom can see the template
- confirm students will receive repos named `advanced-python-imara-<github-username>`

