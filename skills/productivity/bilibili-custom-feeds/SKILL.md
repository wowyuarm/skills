---
name: bilibili-custom-feeds
description: Build and tune a personal, rule-authored Bilibili feed — a Tampermonkey userscript running in your own logged-in browser, driven by a plain config you edit.
disable-model-invocation: true
---

# Bilibili Custom Feeds

Give one user their own Bilibili recommendation feeds: they write the rules, the script obeys. The deliverable is a Tampermonkey userscript that runs inside their logged-in browser and renders extra feeds from a config block they can edit.

This is a personalization-by-rules method, not a recommender-model method. The user's own strongest signals — what they coined, favorited, and finished watching — are the anchors. Do not replace that with a black-box resemblance score; the whole point is that the person can read and change the rule.

## The one architectural decision

**Always deliver a userscript, never a standalone script or a backend.**

A standalone caller has two problems that a userscript does not have at all:
- It needs the user's login cookie, which you must obtain, store, and keep fresh.
- It trips Bilibili risk control much sooner: a plain non-browser client gets HTTP 412 or a risk-control `code` on burst-prone endpoints (e.g. `space/wbi/arc/search`) unless carefully paced, and those failures masquerade as "no data".

Inside the user's own browser, both vanish: the session is already there, and requests come from the real page origin with the real cookies. CORS permits it — `api.bilibili.com` answers `Origin: https://www.bilibili.com` with `access-control-allow-origin: https://www.bilibili.com` and credentials allowed.

Keep a throwaway Python caller only for one-off diagnostics (see `scripts/bili_dist.py`), never as the long-term surface.

## Method

1. **Diagnose the gap first, if the user will share a cookie.** Pull their real recommendation feed and their actual interests, and quantify the overlap. This tells you whether the complaint is "algorithm is bad" (low overlap) or "I want a different shape" (topic mismatch). See `references/api-notes.md` for endpoints and caps.
2. **Choose seeds from the user's own actions, ranked by how costly the action was.** Coin (costs money) > favorite > like > finished-watching. Do not use raw "watched" from history — most items are opened and abandoned; only `progress/duration >= 0.85` (or `is_finish`) means real approval.
3. **Expand each seed through `archive/related`** — the platform's own "similar videos" graph, anchored on things the user already approved. Interleave buckets so no single seed dominates.
4. **Rank by interaction density, not view count.** `coinRate*100 + favRate*12 + likeRate*3`, and drop items under a view floor (about 20000) because small samples make the rate meaningless. Raw views reward big accounts; the whole point is to surface scarce approval.
5. **Weight completion of long videos higher, when the user asks for it.** A seed's weight rises with its duration: `w = 1 + log2(max(dur,60)/60)`, capped at 4 (3 min → 1, 40 min → 2.8, 2 h → 3.9). Apply it twice: weighted sampling of anchors, and a multiplier on the final rank.
6. **When the user asks to build from the accounts they follow, read the follow activity feed, not each account in turn.** The follow list is the user's own hand-made endorsement of who to trust, and it is the one strong signal that does not rely on interaction statistics at all. But do not fetch each followed account's uploads: dozens of consecutive per-account requests trip risk control within a dozen calls, and a blocked call returns an empty result that looks exactly like "this account posted nothing" — a silent wrong answer. Use the video-typed dynamic feed instead: one paginated request covers every account followed.
7. **Build a two-layer feed when the user wants "go wide, then go deep".** Layer one keeps only the long videos already coming from followed accounts. Layer two takes those long videos as anchors and walks `archive/related` outward — where the authors are usually accounts the user does *not* yet follow, so this layer is the one that actually surfaces something new. Do not sort layer one by a ratio it cannot compute: the per-account uploads endpoint returns only plays, danmaku, and comment counts — no coin or favorite — so a density score over danmaku+comment per view, boosted by duration, is the honest ranking there.
8. **When the user wants out of their filter bubble, build the escape from their own history, not a fixed list.** The watch-history response carries `tag_name` (partition) and `author_name` per item; count them into a taste profile, then a "discovery" feed keeps only items whose partition and UP are *not* in that profile. This is evidence-based: it excludes what this user actually over-consumes, and it adapts as their habits change. Do not hardcode "the algorithm pushes X, so block X". Show the derived profile at the bottom of the discovery feed so the rule is not a black box.
9. **Expose the recipe as a data block at the top of the file** — a `FEEDS` array the user edits and reloads. No rebuild, no asking you.

## Writing the recipe

Each feed is an object: `sources`, `filters`, `sort`, `limit`. Source types are `following`, `followedUps`, `expandFollowed`, `search`, `ranking`, `upRecent`, `expand`, `related`. Sort modes are `newest`, `hot`, `quality`, `density`.

- **Prefer naming UPs (`upRecent`) over keyword `search`.** Keyword search returns whatever matches the string at high volume — a topic word pulls in exam-prep and course videos. A concrete UP list is far more precise and needs no guesswork about vocabulary.
- **Filter globally, not per-feed, for platform noise.** Add promo words like the incentive-programme tag to a global block list; they appear across all feeds.
- **A feed with a hard duration floor** (`minDuration` in seconds) is how "long videos only" is expressed.
- **The discovery feed needs a coverage floor and a count threshold.** Only partitions seen more than `TNAME_MIN_SAMPLE` times (about 8) count as "habitually watched", and a view floor (`minView`) keeps the escape from surfacing obscure junk. Category names differ between endpoints — the history `tag_name` and the ranking `tname` are not the same vocabulary (e.g. history says `电子竞技`, ranking says `游戏`), so match by containment, not equality.
- **Do not write a feed whose only source is a list the user has not filled in yet.** A `upRecent` feed with an empty `ups` array renders empty; detect that case and show a hint telling them where to fill it in.
- **Give the user a small "always check these" list (`PINNED_UPS`) separate from the random draw.** A draw over the follow list is what keeps request volume low, but the user usually has two or three accounts they always want covered. Keep that list explicit at the top of the file, accept either a name or a mid, skip silently on a name that resolves to nothing, and never cache it — a fallback list cached for hours would freeze the feed onto those few accounts after the user logs in.
- **A blocked response is not an empty response.** The per-account uploads endpoint answers with a non-zero `code` and an empty list under risk control. Check `code` and treat the risk-control codes as a stop signal (abort the remaining accounts), or the feed will quietly report "nothing long from anyone" when it was actually throttled.

## Failure modes to design against

These are the ones that actually bite, all seen in real use:

- **Dense request bursts cause intermittent fetch failures.** Pulling seeds and expanding many anchors fires dozens of requests; without retry, some fail and the seed pool silently shrinks by half (observed: favorites 130→75, finished 14→0 on a bad run). Put every request behind one shared function with backoff retry, and treat "some step failed" as a flag to re-fetch soon rather than to cache as complete.
- **Seen-marking makes feeds look empty over a day.** Marking rendered items as seen is what makes a feed feel fresh, but a small feed (the core "similar to what you coined" feed) will bottom out after a few visits and only recover the next day. This is intended; say so plainly instead of letting the user think it is broken.
- **A response field can be named differently from what you expect.** History gives `tag_name`/`author_name`, and a build that reads `tag`/`author` gets empty counters and a discovery feed that filters nothing. Verify field names against a live response before trusting a data-model assumption.
- **Async renders race when the user switches feeds.** The first feed's fetch can take 20+ seconds; if they click another tab meanwhile, the first feed's result lands last and overwrites the second. Guard every render with a monotonic token and drop a stale result — do not just make the test wait, or the real app still races.
- **A derived-profile filter must ensure its profile is loaded, and load it once.** If the discovery feed is the first tab opened, the taste profile has not been built yet, so nothing is excluded and the feed silently behaves like a plain ranking. Await the seed/profile load before filtering, and dedupe that load with an in-flight promise so two feeds opening at once do not each run the full crawl.

Caching is the counterweight: cache seeds for ~6 h and each seed's related list for ~6 h. The first load is slow (the full seed crawl); every later load is near-instant, and cached anchors stop re-firing requests — which is also what keeps the rate limiter calm. Give the user a "reroll" control that drops both caches to draw a fresh batch.

## What constrains every design

- **The coin list caps at 3 items, always.** This is Bilibili's limit, not a bug and not fixable. Say so up front; the practical remedy is to tell the user to favorite/coin good videos to thicken the signal. The like list caps around 20; watch history reaches 1000+ and is the real well.
- **Do not over-promise a new-video feed from seeds.** Anchoring on old approvals yields old-adjacent videos. A separate "today" feed from follows is the honest place for new content; seeds are for quality.
- **Only ranking dimension `rid=0` is reliably reachable; some other dimension ids return error `-352` (risk control).** `rid=3`, `36` also returned data in testing, but treat per-dimension ranking as unreliable and prefer sampling the full ranking plus filtering when a broad discovery pool is wanted.

## Assets and scripts

- `assets/bili-custom-feeds.user.js` — a **generic template**, not any one person's config. It ships with example feeds (`投币同款` / `长片` / `深挖` / `出圈` / `今天` / `指定UP`), an empty `PINNED_UPS` list, and neutral keywords the user replaces; every source type and both ranking modes are exercised by that set. Keep it that way: never commit a copy carrying a real person's feeds, UP names, account ids, or filters — this repo is published, and a personal config is not a template.
- `scripts/browser-test.mjs` — drive headless Chrome + CDP to inject the userscript against a real session and confirm a feed renders. Takes a feed index; `BILI_SESSDATA_FILE` must point at a SESSDATA file; needs `google-chrome` and node >= 22. Exits 0 only if the userscript injected, the panel booted, and the target feed settled with at least one card; a settled-but-empty grid exits 1 — empty is indistinguishable from blocked, so it is a failure until eyeballed and overridden with `BCF_ALLOW_EMPTY=1`. It waits for the opening feed to settle before switching tabs — otherwise the slower first feed lands last and overwrites the grid, which once looked like a broken feed.
- `scripts/bili_dist.py` — one-off diagnostic: pull a real recommendation feed and print the distribution (UP frequency, duration, age, follow ratio, topic tags). Needs a cookie file.
- `references/api-notes.md` — verified endpoints, signing, capabilities, and hard caps. Read before touching the data layer.

## Install and verify

1. In Tampermonkey, create a new script, paste `assets/bili-custom-feeds.user.js`, save.
2. Open `https://www.bilibili.com/` logged in and click the floating button: the panel must open and the first feed must render cards.
3. Verify every feed index with `node scripts/browser-test.mjs <feedIndex>`. Exit 0 means the feed rendered; an empty grid plus blocked console signatures is a fetch failure — fix it, do not dismiss it.

Done means: every feed renders cards (or a verified-empty note via `BCF_ALLOW_EMPTY=1`), and the console shows no risk-control blocks.
