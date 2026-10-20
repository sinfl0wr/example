# Demo factory

Personal demo sites for tree-surgeon leads. Each demo is built from the lead's public Google Maps listing.

```
python3 check.py sites/*.js        # flags risky claims, length limits, map/phone issues
python3 build.py sites/<slug>.js   # writes ../<slug>/index.html (+ img/) at the repo root
node batch.mjs <outdir> <slug>...  # browser check (needs a local server on :8765 serving the repo root)
```

Pipeline:
1. Apify `compass/crawler-google-places` with `startUrls` = the leads' Maps links, or `searchStringsArray` = `place_id:<id>`. Turn on `scrapeImageAuthors`. Leave reviewer personal data out.
2. Copy: Sonnet subagents write `sites/<slug>.js` per RULES.md, about 10 leads per agent.
3. Check: `check.py`, then Haiku subagents compare every claim with the source. Fix what they flag.
4. Build, run the browser check, then commit and push. Cloudflare Pages deploys the repo root.

Rules:
- Never invent facts.
- Use only the business's own photos.
- Paraphrase reviews and never name the reviewers.
- Every page carries the demo notice and noindex.
- Service-area businesses (no public address) get "Working around <town>", never "Based in".
- `sites/_hold/` holds leads whose location is unclear. Do not build them until the location is confirmed.
