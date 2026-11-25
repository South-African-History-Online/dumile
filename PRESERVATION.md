# Preservation record

## Subject

Zwelidumile Jeremiah Mgxaji Mslaba "Dumile" Feni (1942 - 1991), South African artist, who worked in Johannesburg until 1968 and then in exile in London and the United States. The site also records the Dumile Feni Foundation, established in 2004.

## Original site

- Published at `https://www.sahistory.org.za/dumile/` by South African History Online.
- First version: a static, frame-based site launched on 28 January 2005 alongside the retrospective at the Johannesburg Art Gallery.
- Later version: a Drupal 7 site at the same address (that codebase is kept in a separate private archive). Drupal 7 reached end of life and the site was not maintained.

## Decision

In November 2026 the site was rebuilt as a static Hugo archive, on the same stack as the Franco Frescura archive, to be served at a subdomain of sahistory.org.za.

| Option | Effort | Ongoing maintenance | Longevity | Outcome |
| --- | --- | --- | --- | --- |
| Migrate to Drupal 11 | High | Security updates for a site that never changes | Tied to Drupal release cycles | Rejected |
| Static archive (Hugo) | Low | A Hugo version bump now and then | Plain HTML, hostable anywhere | Chosen |
| Retire | None | None | Content lost from the web | Rejected |

## Scope of what is preserved

- `legacy-site/` is the complete 2005 static site (pages and images), unmodified apart from removing editor leftovers (`Thumbs.db`, FrontPage folders, Flash files) and blanking the 2005 email addresses and phone numbers of staff and contacts.
- `hugo-site/` is generated from it by `scripts/migrate_legacy.py`: biographies, chronology, the 2005 retrospective and Artist in Exile galleries, press cuttings 1966 - 2002, catalogues, articles and the 1989 grant proposal.

## Known limits

- Images are the 2005 web versions (about 400 pixels at most). Higher-resolution originals are not in this repository.
- Content that existed only in the Drupal 7 database is not included. Wayback Machine captures of `sahistory.org.za/dumile/node/*` exist and have not yet been compared against this archive.
- The 2005 contact details were replaced with a link to SAHO.
- Accessibility: the new templates use semantic landmarks, alt text, visible focus and a keyboard-operable lightbox. A formal WCAG 2.1 audit has not been done.

## Backups

- This repository (content, images and the legacy copy).
- SAHO's own backups of the 2018 web server, which hold the original static and Drupal 7 trees.
- The Internet Archive's captures of `sahistory.org.za/dumile/`.

## Earlier codebase

This repository's history starts with the 2026 rebuild. The Drupal 7 codebase that served the site before it is kept in a separate private archive repository at South African History Online and is not part of this one.

## Rights

Images of the works are copyrighted. Contact SAHO for copyright details.
