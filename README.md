# Dumile Feni

Archive site for Dumile Feni (1942 - 1991) and the Dumile Feni Foundation, maintained by South African History Online. A Hugo static site on the same stack as the Franco Frescura archive.

## Layout

- `legacy-site/` - the 2005 static Foundation site, kept as the source of record.
- `scripts/migrate_legacy.py` - rebuilds `hugo-site/content` and `hugo-site/static/images` from `legacy-site/`. It holds the full legacy-to-new URL mapping. Re-running it overwrites manual edits to content, so change the script (or stop using it) once editorial work starts.
- `hugo-site/` - the site. Theme: `themes/dumile-ink`.
- `scripts/check_links.py` - verifies internal links and images in a build.

## Develop

```bash
docker compose -f docker-compose.dev.yml up     # new site on :1314, legacy site on :8889
```

Build once:

```bash
docker run --rm -v "$(pwd)/hugo-site:/project" ghcr.io/gohugoio/hugo:v0.170.1 build --minify
python3 scripts/check_links.py hugo-site/public
```

## Content model

Pages use JSON front matter. Galleries (`"type": "gallery"`) carry a `works` list of `image`, `title`, `year`, `medium`, `dimensions`; `"variant": "scans"` is for documents and press cuttings.

## Design

The look follows the 2005 site: its hand-lettered wordmark, circular sketch icons, the ochre study in the margin and burnt-red links. Headings use Reenie Beanie (SIL Open Font License, self-hosted in `hugo-site/static/fonts`).

## Rights

Images of the works are copyrighted. Contact SAHO for copyright details.
