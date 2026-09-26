# docs/ — the alunan.app website and project records

This folder holds two unrelated things:

- **The GitHub Pages site**: `index.html`, `CNAME`, `.nojekyll`, and `assets/`
  when added. Only these files are published.
- **Project records**: `decisions/`, `validation/`, and notes such as
  `workspace-relocation.md`. They stay on GitHub and are not part of the website.

The site follows Bunyi's Pages setup, reduced to what Alunan needs before its
first release. The published page is static HTML with inline CSS and requires no
JavaScript.

## Publishing

**Settings -> Pages -> Build and deployment -> Source: GitHub Actions.**
`.github/workflows/pages.yml` tests the builder, assembles `_site` with
`tools/build_site.py`, and deploys it from `main`:

- Changes on `main` to the public site files, the builder, or the workflow
  trigger a rebuild.
- **Actions -> Website -> Run workflow**, on `main`, redeploys on demand.
- Pull requests test and build the artifact; they never deploy it.

Only the deploy job has Pages write permission. Bunyi's release-version
rendering, release-refresh dispatch, and README badges are omitted because
Alunan has no releases. Add them (with tests) when the first installers ship,
following the Releases section of [`AGENTS.md`](../AGENTS.md).

## Custom domain

Configured on 2026-09-26. Repository Pages settings use GitHub Actions as the
source, the custom domain `alunan.app`, and enforced HTTPS; the `github-pages`
environment deploys only from `main`. With Actions deployments the repository
setting is authoritative; `CNAME` keeps the builder and settings in step.

Cloudflare DNS for alunan.app, all records DNS-only (not proxied) so GitHub can
issue and renew its certificate: apex `A` records to `185.199.108.153`,
`185.199.109.153`, `185.199.110.153`, `185.199.111.153`; apex `AAAA` records to
`2606:50c0:8000::153` through `2606:50c0:8003::153`; `www` `CNAME` to
`shaztechio.github.io`; and the `_github-pages-challenge-shaztechio` TXT record
that keeps alunan.app verified for the shaztechio organization. Do not proxy
these records or add a wildcard record.

## Local preview

```sh
python3 -m unittest discover -s tools -p 'test_build_site.py' -v
python3 tools/build_site.py --output .phase0/site-preview
```

Open `.phase0/site-preview/index.html` in a browser.

## Keeping it honest

The page describes planned behavior from [`spec/FEATURES.md`](../spec/FEATURES.md)
and the current phase from [`spec/IMPLEMENTATION-PLAN.md`](../spec/IMPLEMENTATION-PLAN.md).
Update its Features, Platforms, and Status sections when those change. Do not
advertise downloads, hardware support, or platform availability before they are
released and measured.

## Analytics

`index.html` loads [PostHog](https://posthog.com) to count visits to this site,
using Alunan's own PostHog project (added 2026-09-26 at the owner's request).
**The apps do not:** FEATURES.md APP-004 rules out telemetry in the MVP, so the
snippet stays in `docs/` and nowhere else. The `phc_` value is a public,
write-only project key meant for client-side HTML; it is not Bunyi's key and
not a personal API key.

Events and the PostHog script go through the managed reverse proxy
`t.shaztech.io`, as on bunyi.app; `ui_host` points PostHog's own links back at
its US region. The snippet is PostHog's standard one. Bunyi's page also sets
`disable_surveys: true` and `capture_performance: false`, which it measured as
saving about 40 KB per visit for its project; they are not applied here until
measured for this project. Nothing else on the page depends on the script, so
the site renders the same when it is blocked.

## Link previews

There is no `og:image` yet; add an absolute `https://alunan.app/assets/...`
card once an app icon exists.
