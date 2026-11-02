# Publishing this project to GitHub

The project is prepared for a standalone public repository. The connected GitHub workspace available during preparation did not expose a repository-creation or repository-visibility action, and the only repository currently accessible to it is the private `brain-academy-fee-manager` project. This project should **not** be placed in that unrelated repository.

## 1. Create an empty public repository

On GitHub, create a repository under `iSufyanAshraf` named `wildlife-observation-qc`.

- Description: `Local-first quality checks for wildlife occurrence and camera-trap survey data.`
- Visibility: **Public**
- Do not initialise it with a README, license, or `.gitignore`; this project already contains those files.

## 2. Push this folder

From a terminal opened in this extracted project folder:

```bash
git init -b main
git add .
git commit -m "Initial release: wildlife survey data quality checker"
git remote add origin https://github.com/iSufyanAshraf/wildlife-observation-qc.git
git push -u origin main
```

Authenticate with GitHub when Git requests credentials. Do not place a personal access token in this repository or in a command that may be saved in shell history.

## 3. Verify the public release

After the push:

1. Open the repository's **Actions** tab and confirm the CI workflow completes successfully.
2. Confirm the repository is public and that the README, LICENSE, tests, sample files, and CI workflow are visible.
3. Add the topics `wildlife`, `biodiversity`, `darwin-core`, `camera-trap`, `conservation`, `data-quality`, and `python`.
4. Keep the repository description and README accurate; do not claim usage, stars, downloads, institutional endorsement, or production adoption that has not occurred.
5. Tag a release only after reviewing the published code and passing CI.

## 4. Build real maintainer evidence

A new repository does not become an established open-source project merely because it is public. Build an actual user base, respond to issues, review contributions, publish versioned releases, and document real deployments or downstream use (with permission). Keep a transparent changelog and use the project's CI to protect quality.

Do not submit the Codex for Open Source application by claiming existing community adoption or a long-standing maintainer role unless those claims are true. See the program's current criteria before applying.
