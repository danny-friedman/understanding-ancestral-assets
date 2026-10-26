# Understanding Ancestral assets

Public asset hosting for [Understanding Ancestral Recall](https://www.understandingancestral.com/): the original custom MTG font, backgrounds, banner, favicon, and shared PDF icon.

[GitHub Pages](https://danny-friedman.github.io/understanding-ancestral-assets/) publishes approved files from `main` using the **Validate and publish assets** workflow after validation passes. Repository Pages settings must use **GitHub Actions**; legacy branch publishing would bypass that gate. Assets keep their existing versioned URLs under `assets/v1/`, for example:

```text
https://danny-friedman.github.io/understanding-ancestral-assets/assets/v1/mtg.woff2
```

The theme source and backups are kept in a private repository. Article photos remain hosted by Blogger.

PR checks validate SHA-256 hashes, sizes, file signatures, safe filenames and the asset manifest. Tests confirm that damaged, unlisted and linked files are rejected. On `main`, the validated artifact is deployed, then actual published bytes, MIME types and font CORS are checked with one propagation retry. Failed validation prevents the deployment job. PRs never deploy.

Only `index.html`, `robots.txt`, `.nojekyll` and manifest-listed files under versioned `assets/vN/` directories enter the Pages bundle. Scripts, tests, workflow files and Git metadata are excluded. The existing font/background/banner/icon bytes are unchanged by this migration. Retain older version directories when adding replacements so old theme URLs continue to work.

Local checks use Python’s standard library:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/assets.py --stage build/site
python3 scripts/assets.py --verify-public
```

Use a fresh staging directory. Before merging an intentional asset change, `--verify-public` still compares against the previously published files; the production workflow runs that check after deployment. Public site/certificate/video monitoring and its private reports live in the separate private maintenance repository.
