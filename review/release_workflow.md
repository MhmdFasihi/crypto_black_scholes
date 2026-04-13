# Release Workflow: GitHub + PyPI

Date: 2026-04-12

Audience: senior developer / release maintainer

## Purpose

This document describes the actual release workflow used by the repository at `v0.9.0` to:

- update GitHub
- create a versioned GitHub release
- publish the package to PyPI
- verify the result

It is intentionally operational rather than aspirational. It reflects the current repository wiring in `.github/workflows/publish.yml`.

## Current Automation Model

The repository has one publish workflow:

- file: `.github/workflows/publish.yml`
- triggers:
  - `push` to `main`
  - `release` with type `published`
  - manual `workflow_dispatch`

The jobs behave as follows.

### On push to `main`

Jobs:

- `test`
- `publish-testpypi`

Behavior:

- checks out the repo
- sets up Python 3.11
- installs package and `pytest`
- runs the test suite
- builds the package
- publishes to TestPyPI only if the repo secret `TEST_PYPI_API_TOKEN` is configured

Important:

- a push to `main` does not publish to production PyPI
- it may publish to TestPyPI

### On published GitHub release

Jobs:

- `test`
- `publish-pypi`

Behavior:

- checks out the repo
- sets up Python 3.11
- rebuilds the package
- publishes to PyPI using the repo secret `PYPI_API_TOKEN`

Important:

- production PyPI publication is release-driven, not tag-push-only
- the GitHub release event is the production deployment event

## Credentials And Secrets

### Local developer machine

Required:

- `gh` authenticated locally
- Python build toolchain available in the virtual environment

Recommended local checks:

- `gh auth status`
- `.venv/bin/python -m pip show build twine setuptools wheel`

### GitHub Actions secrets

Expected repo secrets:

- `PYPI_API_TOKEN`
- optional `TEST_PYPI_API_TOKEN`

These are consumed by the GitHub Actions workflow and should be the primary mechanism for automated publication.

### `.pypirc`

Use case:

- manual fallback only
- not the primary automated path

Rationale:

- automated publishing should use GitHub Actions secrets
- local `.pypirc` is useful if the workflow is unavailable or a manual emergency upload is required

## Files That Must Be Updated For A New Release

At minimum:

- `pyproject.toml`
- `crypto_bs/__init__.py`
- `CHANGELOG.md`

Usually also:

- `README.md`
- docs under `docs/`
- tests if API or behavior changed
- any versioned strings in helpers such as client user-agent values

## Standard Release Procedure

This is the normal developer release path.

### 1. Implement the change

Make the intended code, test, and documentation updates.

Keep the release scope explicit. Do not mix unrelated local changes into the release commit.

### 2. Bump the version

Update:

- `pyproject.toml`
- `crypto_bs/__init__.py`

If there are version strings in user-agent headers or docs, update those too.

### 3. Update the changelog

Add a new top section to `CHANGELOG.md`:

- version header
- date
- added / changed / fixed notes
- compare link at the bottom if you maintain those links

The changelog top section is also the easiest source for GitHub release notes.

### 4. Run local validation

Recommended command sequence:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m build --sdist --wheel --no-isolation --outdir /tmp/crypto_bs_dist_<version>
.venv/bin/python -m twine check /tmp/crypto_bs_dist_<version>/*
```

What this verifies:

- test suite passes
- sdist builds
- wheel builds
- package metadata / long description passes `twine check`

### 5. Confirm GitHub auth locally

```bash
gh auth status
```

This is required for:

- creating the GitHub release
- inspecting workflow runs

### 6. Stage only the intended release files

Example pattern:

```bash
git add pyproject.toml crypto_bs/__init__.py CHANGELOG.md README.md docs/ tests/
```

Do not blindly stage unrelated working-tree changes.

### 7. Commit the release

Example:

```bash
git commit -m "Release vX.Y.Z with <short scope>"
```

The release commit should correspond to one coherent publishable state.

### 8. Create the annotated tag

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

Use annotated tags, not lightweight tags.

### 9. Push branch and tag

```bash
git push origin main --follow-tags
```

This updates GitHub and triggers the push workflow.

Expected result:

- push workflow runs tests
- optional TestPyPI publish may run

### 10. Create the GitHub release

Generate release notes from the new changelog section if desired:

```bash
sed -n '/## \[X.Y.Z\]/,/## \[PREV\]/p' CHANGELOG.md | sed '$d' > /tmp/crypto_bs_vX.Y.Z_release_notes.md
```

Create the release:

```bash
gh release create vX.Y.Z \
  --title "Release vX.Y.Z" \
  --notes-file /tmp/crypto_bs_vX.Y.Z_release_notes.md
```

This is the event that triggers the production PyPI publish job.

### 11. Verify the GitHub Actions runs

List recent runs:

```bash
gh run list --workflow publish.yml --limit 10
```

Watch the release run:

```bash
gh run watch <release_run_id> --exit-status
```

Useful inspection:

```bash
gh run view <run_id>
gh run view <run_id> --log
gh release view vX.Y.Z
```

Expected outcomes:

- push run is `success`
- release run is `success`
- `Publish to PyPI` job is `success`

### 12. Verify public PyPI propagation

PyPI can lag slightly after a successful upload. Check the live index:

```bash
.venv/bin/python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('https://pypi.org/pypi/crypto_bs/json')); print(data['info']['version'])"
```

Expected:

- the returned version matches the release version

If not, wait briefly and retry before assuming the upload failed.

## Manual Fallback Publish

Use this only if GitHub Actions publishing is unavailable or broken and a manual release is explicitly required.

Preconditions:

- local artifacts already built
- local `.pypirc` configured correctly or token supplied another secure way

Command:

```bash
.venv/bin/python -m twine upload /tmp/crypto_bs_dist_<version>/*
```

Warnings:

- do not use manual upload and GitHub release upload simultaneously without understanding whether the version already exists
- PyPI versions are immutable once accepted

## Verification Checklist

Use this checklist for every release:

- version bumped in `pyproject.toml`
- version bumped in `crypto_bs/__init__.py`
- changelog updated
- docs/README updated if needed
- tests pass locally
- build succeeds locally
- `twine check` passes locally
- commit created
- annotated tag created
- `main` and tag pushed
- GitHub release created
- push workflow successful
- release workflow successful
- PyPI index shows new version

## Common Failure Modes

### 1. GitHub release created before version bump commit is pushed

Symptom:

- release workflow publishes the wrong code or wrong package version

Prevention:

- always push `main` and tag first
- create the GitHub release after the release commit is on GitHub

### 2. `gh auth status` is valid locally but unavailable in a sandboxed environment

Symptom:

- local automation layer reports auth failure even though `gh` works outside the sandbox

Prevention:

- rerun the command in the real host environment if your tooling distinguishes sandboxed vs non-sandboxed execution

### 3. Local build fails because the venv packaging toolchain is broken

Symptom:

- `python -m build` cannot import `setuptools.build_meta`

Recovery:

```bash
.venv/bin/python -m pip install --force-reinstall setuptools wheel build twine
```

Then rebuild.

### 4. Release workflow says success but PyPI JSON still shows the previous version

Symptom:

- immediate API read returns old version

Most likely cause:

- propagation delay

Recovery:

- wait a few seconds
- query the project JSON again
- inspect Actions logs if it still does not update

### 5. TestPyPI job is skipped

Symptom:

- push workflow shows `Publish to TestPyPI` skipped

Cause:

- `TEST_PYPI_API_TOKEN` is not configured

This is expected behavior in the current workflow and is not a release failure.

## Security Notes

- never commit API tokens
- keep PyPI tokens in GitHub Actions secrets for the normal release path
- keep `gh` credentials in the system keychain, not in the repository
- use `.pypirc` only for manual fallback, not as the primary automation mechanism

## Recommended Improvements Beyond Current State

These are not required to operate the current release workflow, but they would improve it.

### 1. Move from password token upload to Trusted Publishing

The current workflow uses `PYPI_API_TOKEN`. GitHub Actions logs already indicate PyPI Trusted Publishing is available.

Benefit:

- no long-lived PyPI token in GitHub secrets
- simpler and more secure publish model

### 2. Add a release helper script or Make target

Example candidates:

- `make release VERSION=0.10.0`
- `scripts/release.sh`

Benefit:

- less manual repetition
- fewer missed steps

### 3. Add a post-release smoke check

Example:

- install the just-published wheel into a clean temp venv
- import `crypto_bs`
- print `__version__`

Benefit:

- confirms actual installability, not only upload success

### 4. Add coverage reporting to CI

Current workflow only runs tests. It does not publish a coverage report.

Benefit:

- helps track readiness for a future `1.0.0`

## Recommended Canonical Release Sequence

If you want one compact reference, use this:

```bash
# 1. update version + changelog + docs

# 2. validate locally
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest tests -q -p no:cacheprovider
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m build --sdist --wheel --no-isolation --outdir /tmp/crypto_bs_dist_X.Y.Z
.venv/bin/python -m twine check /tmp/crypto_bs_dist_X.Y.Z/*

# 3. auth check
gh auth status

# 4. commit + tag
git add <release files>
git commit -m "Release vX.Y.Z with <scope>"
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# 5. push
git push origin main --follow-tags

# 6. create GitHub release
gh release create vX.Y.Z --title "Release vX.Y.Z" --notes-file /tmp/crypto_bs_vX.Y.Z_release_notes.md

# 7. verify workflows
gh run list --workflow publish.yml --limit 10
gh run watch <release_run_id> --exit-status

# 8. verify live PyPI
.venv/bin/python -c "import json, urllib.request; data=json.load(urllib.request.urlopen('https://pypi.org/pypi/crypto_bs/json')); print(data['info']['version'])"
```

That is the current production release workflow for this repository.
