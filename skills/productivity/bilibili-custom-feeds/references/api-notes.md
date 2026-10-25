# Bilibili API notes (verified)

Everything here was confirmed against the live API from a logged-in browser origin. Endpoints flagged **throttle-prone** sit behind risk control: they answer any client while paced, but under a burst they return HTTP 412 or a JSON body with a risk-control `code` and empty data — a plain non-browser client hits that wall far sooner. Details under [Rate limiting](#rate-limiting).

## Contents

- [Signing (WBI)](#signing-wbi)
- [Endpoints](#endpoints)
- [Hard caps and unreachable data](#hard-caps-and-unreachable-data)
- [Transport, auth, CORS](#transport-auth-cors)
- [Rate limiting](#rate-limiting)
- [Response shapes gotchas](#response-shapes-gotchas)

## Signing (WBI)

Some endpoints require a signed query. The scheme:

1. `GET /x/web-interface/nav` → `data.wbi_img.img_url`, `data.wbi_img.sub_url`. Take the filename stem of each.
2. Concatenate `img + sub`. Permute that 64-char string through the fixed 64-entry table (below). Take the **first 32** characters — that is the `mixin_key`.
3. Build the query: all params including `wts = unix_seconds`, keys sorted ascending, each `k` and `v` url-encoded, joined with `&`.
4. `w_rid = md5(query_string + mixin_key)`.
5. Request `...?<query_string>&w_rid=<w_rid>`.

The image keys rotate daily, so fetch them per session rather than caching for long.

```
46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,
14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,
56,59,6,63,57,62,11,36,20,34,44,52
```

A pure-JS md5 inlined in the userscript produces byte-identical output to `node:crypto` on the vectors tested, and the JS and Python signers produce the same `w_rid` for identical params. Sign with `encodeURIComponent` on both keys and values.

## Endpoints

| Purpose | Endpoint | Notes |
| --- | --- | --- |
| Identity + WBI keys | `GET /x/web-interface/nav` | returns `mid`, `uname`, `level_info`, `wbi_img` |
| Homepage feed | `GET /x/web-interface/wbi/index/top/feed/rcmd?web_location=1430650` | `data.item[]` with `bvid/title/owner/duration/pubdate/is_followed/rcmd_reason/stat`; WBI-signed |
| Watch history | `GET /x/web-interface/history/cursor` | WBI-signed; params `max`, `view_at`, `business=''`, `ps`; paginate via `data.cursor.max` / `.view_at`; richest signal, 1000+ items; per item `tag_name` (partition) and `author_name` (UP) — note these names, not `tag`/`author` |
| Coined videos | `GET /x/space/coin/video?vmid=<mid>&pn=1&ps=30` | **hard cap 3**, see below |
| Liked videos | `GET /x/space/like/video?vmid=<mid>&pn=&ps=` | `data.list`, ~20 cap |
| Favorite folders | `GET /x/v3/fav/folder/created/list-all?up_mid=<mid>` | `data.list[]` with folder `id`, `title`, `media_count` |
| Folder contents | `GET /x/v3/fav/resource/list?media_id=<id>&pn=&ps=20&platform=web` | `data.medias[]`; keep `type === 2` (video); `data.has_more` |
| Related videos | `GET /x/web-interface/archive/related?bvid=<bv>` | `data[]`; the expansion graph; carries full `stat` |
| Follow activity feed | `GET /x/polymer/web-dynamic/v1/feed/all?type=video&page=` | one paginated call covers *all* follows with their latest uploads; `data.items[].modules.module_dynamic.major.archive` (`bvid/title/duration_text/pubdate/stat.play`) + `module_author.name/mid`; needs login; ~20/page |
| Per-UP uploads | `GET /x/space/wbi/arc/search?mid=&ps=&pn=&order=pubdate` | WBI-signed; `data.list.vlist[]`; **throttle-prone** (see Rate limiting); carries `play`/`video_review`(danmaku)/`comment` only — **no coin or favorite**, so it cannot feed an interaction-density score |
| Follow list | `GET /x/relation/followings?vmid=<mid>&pn=&ps=50&order=desc&order_type=attention` | needs login; used to draw a sample of accounts rather than to query each one |
| Keyword search | `GET /x/web-interface/wbi/search/type?keyword=&search_type=video` | WBI-signed; precise only with a narrow keyword |
| Ranking by partition | `GET /x/web-interface/ranking/v2?rid=<rid>` | `rid=0` full site, `rid=3` music, `rid=36` 社科·法律·心理; some dimension ids return `-352` (risk control) — treat per-dimension ranking as best-effort; items carry `tname` |
| Video tags | `GET /x/tag/archive/tags?bvid=<bv>` | real topic labels — use these instead of guessing from the title |

## Hard caps and unreachable data

- **Coined videos: 3, always.** Independent of `pn`/`ps`. This is a platform limit. Do not design a feed whose quality depends on a large coin pool; lean on favorites + finished history instead, and tell the user to coin/favorite to thicken the signal.
- **Liked videos: about 20.**
- **Unreachable (404/400):** danmaku, comments, and search-history endpoints.
- **`popular/series/one`** (weekly must-watch) returns code `-352` (risk control) — do not rely on it.

## Transport, auth, CORS

- The recommendation endpoints return data without login, but personalization lives in `SESSDATA`: unauthenticated, `is_followed` is always 0 and content is generic.
- From a page on `https://www.bilibili.com`, `api.bilibili.com` returns `Access-Control-Allow-Origin: https://www.bilibili.com` with `Access-Control-Allow-Credentials: true`. A userscript on that origin can therefore call these APIs with the browser's own cookies. Use `fetch(url, { credentials: 'include' })`.
- No backend, no cookie handling, and no separate login needed. This is the whole reason for the userscript architecture.

## Rate limiting

- Bilibili risk control throttles with HTTP 412 when a client requests too fast; a plain non-browser client trips it far sooner than the browser origin does. Pace requests around 500 ms apart.
- From inside the browser, bursts are tolerated far better but still fail intermittently: several consecutive calls can throw a plain `TypeError: Failed to fetch` with no HTTP status. Treat every request as fallible — one shared wrapper with backoff retry, and do not cache a partial result as if it were complete.
- **`space/wbi/arc/search` is the touchiest endpoint.** A dozen consecutive calls in the browser returns an HTML intercept page instead of JSON (first character `<`), and other times a JSON body with a non-zero `code` (`-352` / `-412` / `-509`) and an empty `vlist`. Both mean "throttled", not "no uploads". Detect the HTML case and give up immediately rather than retrying into a deeper block; detect the `code` case and stop the whole run. This is why the long-video feed reads the follow activity feed instead of querying accounts one at a time.
- `space/wbi/arc/search` works **without login** from a signed (WBI) anonymous request; only the follow list, favorites, and watch history require the session. The bottleneck on the per-account path is risk control, not authentication.

## Response shapes gotchas

- `/x/web-interface/nav` returns `code: -101` when not logged in — check it before trusting `data`.
- Cover URLs may arrive protocol-relative (`//i0.hdslb.com/...`); prefix `https:`.
- `vlist[].length` in per-UP search is a `"mm:ss"` string, not seconds — parse it.
- Watch history stores `progress` and `duration` in seconds; completion is `progress/duration >= 0.85` or the `is_finish` flag. There is no "watched" boolean worth trusting — most entries are barely started.
