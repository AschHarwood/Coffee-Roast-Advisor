# Prompt for deep-research app: find public roast-log training data (copy below the line)

---

I'm building open-source software that learns roasting behavior from Artisan
roast logs (`.alog` files — Python-dict-literal text files produced by the free
Artisan Roaster Scope software). I need you to find and compile publicly
available roast logs on the internet that can be downloaded and used as
training data. Deliverable is a manifest of download links with metadata, not
analysis.

## What to find, in priority order

1. **Artisan `.alog` files** from:
   - **Fluid-bed roasters**: Fresh Roast SR800 / SR540 / SR500 (highest value)
   - **Yoshan gas drum roasters** (YS-series, 1–2kg) and other small gas drums:
     Huky 500, Mill City / North 500g–1kg, Santoker, Bideli, Dongyi, Probat-style
     clones, Kaleido (note heat type — some are electric)
   - Any other machine IF the machine is identified by the uploader
2. **Artisan CSV exports** (secondary — Artisan can export its data as CSV;
   these lose some fields but keep the curves and events)
3. Bulk collections (someone's committed roast-log archive) are worth far more
   than single files.

## Where to look

- **GitHub / GitLab code search**: `.alog` files committed to repos (search by
  extension and by content markers like `roastUUID`, `timeindex`, `temp2`,
  `artisan_os`). Many home roasters version-control their roast logs. Also the
  Artisan project's own repository test files.
- **Forums with attachments**: Homeroasters.org, Home-Barista.com,
  CoffeeSnobs, r/roasting (Reddit posts often link Google Drive / Dropbox /
  GitHub), Artisan's GitHub Discussions and issue tracker (users attach logs
  when reporting bugs — machine usually named in the report).
- **Blogs/personal sites** of home roasters who publish their profiles.
- artisan.plus is a private service — do not attempt; Roast World hosts Aillio
  Bullet data in a different format — note it as a lead but it is out of scope.

## Manifest format (strict)

A table (CSV or markdown) with one row per file or collection:

| url | filename(s) | n_files | machine (as stated) | heat type | batch size | probe/config notes | source context | license/consent note |

- "machine (as stated)": only what the uploader actually says — never guess.
  Unlabeled files are still useful; mark machine as `unknown`.
- "source context": one line — bug report, personal archive, tutorial, etc.
- "license/consent note": repo license if any; for forum attachments note
  "publicly posted, no explicit license". Flag anything that looks private or
  accidentally exposed — we will exclude it.
- Include direct download URLs where possible (raw.githubusercontent.com etc.).

## Verification

Spot-check a sample of each collection: a real `.alog` is a plain-text Python
dict starting with keys like `recording_version` / `version` and containing
`timex`, `temp2`, `timeindex`, `roastUUID`. Reject HTML pages saved as .alog,
empty templates, or Artisan *settings* files (`.aset`). Report the total count
of verified files by machine class at the top of the manifest.

Also report, briefly: any communities or individuals who maintain large
personal archives and might respond to a polite request to share (names/links
only — no outreach).
