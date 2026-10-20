# Demo copy rules (read once, follow exactly)

You write one site file per lead: `/home/claude/demos/sites/<slug>.js`, a JS object literal wrapped in `( ... )`.
Reference example (format and tone only): `/home/claude/demos/sites/heritage-gardens.js` — but do NOT copy its `photos`, `wall` photo cells or `services[].photo`; use `ownerPhotos` instead (the build script places photos).

## Source data
Apify dataset `<datasetId of the latest Apify run>`. For each lead call `get-dataset-items` with `offset=<k>`, `limit=1`,
`fields="title,placeId,phone,totalScore,reviewsCount,reviewsDistribution,categoryName,categories,city,neighborhood,description,reviewsTags,images,reviews"`,
`omit="reviews.name,reviews.reviewerId,reviews.reviewerUrl,reviews.reviewerPhotoUrl,reviews.reviewUrl"`.
Check the returned `placeId` matches the lead. Use ONLY this data plus the lead row you were given (owner first name, town).

## The one rule that matters
Never state a fact about the business that is not in the source data. No insurance, years trading, "free quotes",
response times, prices, guarantees, qualifications, coverage areas or team size unless the business's own listing says it.
If data is thin, write less. Empty arrays are fine: the section is hidden.

## Fields
- `slug`: lowercase, hyphens, from the business name (e.g. `white-hall-tree-services`).
- `business`: exact listing title, tidied capitalisation only (e.g. "ACACIA TREE SURGEONS . Liss." → "Acacia Tree Surgeons").
- `shortName`: business name without "Ltd"; if longer than 18 characters, the distinctive part (e.g. "Banstead Tree Works").
- `firstName`: owner first name from the lead row; "" if the row has none or two names.
- `town`: from the lead row. `phone`: UK format "07xxx xxxxxx". `phoneLink`: "+447…".
- `rating`: totalScore as text with one decimal ("5.0"). `reviewCount`: reviewsCount.
- `googleUrl`: `https://www.google.com/maps/search/?api=1&query=<url-encoded title>&query_place_id=<placeId>`.
- `proofExtra`: 1–2 short strings, e.g. ["{town}", "Tree surgery and hedges"]. Neighbourhood only if in the data. Never a street address.
- `headline`: two lines, each ≤13 characters, a plain action phrase that fits their work (e.g. ["Trees down.", "Garden clear."]).
- `heroLine`: ≤80 chars, "<their services> around <town>."
- `servicesIntro`, `howIntro`: one sentence each, grounded in reviews.
- `services`: 3–6 items `{name, fact, fig, unit}` — only services evidenced in reviews, tags or categories. `fact` ≤90 chars and specific
  (from reviews); `fig` one word ≤8 chars; `unit` ≤24 chars.
- `steps`: 0–3 items `{name, text}` — only what reviews actually describe (e.g. quick visit, clear quote, tidy finish). Else [].
- `wall`: 5–9 fact cells `{big, cap}`: `big` ≤7 chars, `cap` ≤32 chars. Rating ("5.0" / "on Google"); review count
  ("N" / "five-star reviews" only if reviewsDistribution shows every review is 5 stars, else "Google reviews"); then words customers really use.
- `reviews`: 1–3 items `{text, source: "Google review", when: "Mon YYYY"}` — PARAPHRASED (no verbatim copying, ≤160 chars), no names of
  reviewers, keep the concrete detail. First = the most specific. 4–5 star reviews only.
- `reviewsNote`: "Reviews paraphrased from <business>'s Google reviews (<rating> from <reviewCount>)."
- `areas`: 6–10 real towns/villages within ~8 miles of `town`. `areasIntro`: "Based in <town>. Each ring on the map is one mile."
- `areaMap`: `{centre: [lat, lng] of town centre, label: town, places: {"Name": [lat, lng], ...}}` — same names as `areas`, 4 decimals.
  Only places you are confident about; drop any you are unsure of.
- `faq`: 0–3 items `{tab, q, a}` grounded in reviews (e.g. clear-up, how pricing came across). Law FAQs are added automatically.
- `ownerPhotos`: up to 9 `images[].imageUrl` whose `authorName` equals the business title (case-insensitive). Never customer photos, never streetview.
- `title`: "<business> — <short service phrase>, <town> (demo)". `desc`: ≤140 chars.
- Do NOT set: mode, photos, photoCredits, checker, text, quoteHeadline, demoNotice (the build adds them).

## Style
Plain British English, short sentences, no hype words (unleash, elevate, seamless, top-notch, second to none).

## Output
Write the files. Reply with at most 3 lines: slugs written, and any lead skipped with the reason.
