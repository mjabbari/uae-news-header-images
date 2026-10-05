# UAE News – header images

Daily list of landscape photographs of the seven emirates, fetched from Unsplash by a scheduled
GitHub Actions job and published as `images.json`. Used by the UAE News iOS app for its Today header.

Photos are hotlinked from Unsplash and remain the property of their photographers; each entry
carries the photographer credit and a link, per the Unsplash API guidelines. No API key is stored
in this repository; the job reads it from the `UNSPLASH_ACCESS_KEY` secret.


## Curation (since 5 Oct 2026)

Header photos are hand-picked. `curation/collect_candidates.py` (workflow "Collect curation candidates",
triggered by editing `curation/request.txt`) gathers a wide Unsplash pool into `curation/candidates.json`.
The chosen photos live in `curation/curated.json`; the daily job only republishes that set, rotates its
starting point, and tells Unsplash once per photo that it is in use (`curation/tracked.json`).
