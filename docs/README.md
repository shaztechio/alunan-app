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
Alunan has no releases. Add them (with tests) when the first installers ship.

## Custom domain

`CNAME` claims **alunan.app**. It takes effect once DNS points at GitHub Pages:
apex `A` records to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`,
`185.199.111.153` (plus the `AAAA` equivalents `2606:50c0:8000::153`,
`2606:50c0:8001::153`, `2606:50c0:8002::153`, `2606:50c0:8003::153`), and a `www`
`CNAME` to `shaztechio.github.io`. Verify the domain under the organization's
Pages settings to prevent takeover, then enable **Enforce HTTPS** once the
certificate is issued. Until DNS resolves, the site is at
`https://shaztechio.github.io/alunan-app/`.

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

No analytics are included. Bunyi's PostHog project key belongs to Bunyi; add a
separate Alunan project only by explicit decision, and never in the app itself.
There is no `og:image` yet; add an absolute `https://alunan.app/assets/...`
card once an app icon exists.
