#!/usr/bin/env python3
"""Pull one Bilibili user's personalized homepage feed and print its distribution.

Purpose: given a SESSDATA, fetch the homepage recommendation feed and quantify
the gap between "what this user actually engages with" and "what Bilibili
recommends". Diagnostic tool only — the long-term deliverable is the userscript
in assets/.

Usage:
    python3 bili_dist.py <cookie_file> [--pages N] [--out dist.md] [--no-tags]

cookie_file format (one per line):
    SESSDATA=xxxx
    buvid3=xxxx
(DedeUserID optional; bili_jct not needed — this script only reads.)
"""
import sys, json, time, hashlib, urllib.parse, urllib.request, collections, argparse

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,
         14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,
         56,59,6,63,57,62,11,36,20,34,44,52]


def load_cookie(path):
    jar = {}
    raw_lines = []
    # utf-8-sig swallows the BOM Windows Notepad may write
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip().lstrip('\ufeff')   # second chance for a BOM
            if not line or line.startswith('#'):
                continue
            raw_lines.append(line)
            if '=' in line:
                k, v = line.split('=', 1)
                jar[k.strip()] = v.strip()

    # Fallback: no key names in the file → treat a single long line as a bare
    # SESSDATA value (they contain %2C separators and are usually 100+ chars).
    if 'SESSDATA' not in jar:
        cands = [l for l in raw_lines if not l.startswith(('{', '['))]
        if len(cands) == 1 and len(cands[0]) > 40 and '%2C' in cands[0]:
            jar['SESSDATA'] = cands[0]
        else:
            sys.exit('cannot find SESSDATA in the cookie file '
                     '(no key=value pair and no bare value matched)')

    # Without buvid3, ask for one (missing it invites 412)
    if 'buvid3' not in jar:
        try:
            spi = get('https://api.bilibili.com/x/frontend/finger/spi',
                      '; '.join(f'{k}={v}' for k, v in jar.items()))
            b3 = (spi.get('data') or {}).get('b_3')
            if b3:
                jar['buvid3'] = b3
                print('  (auto-fetched buvid3)', file=sys.stderr)
        except Exception as e:
            print(f'  buvid3 fetch failed (continuing): {e}', file=sys.stderr)

    return '; '.join(f'{k}={v}' for k, v in jar.items()), jar


def get(url, cookie):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Referer': 'https://www.bilibili.com/',
        'Cookie': cookie,
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


_mixin_key_cache = None


def wbi_sign(params, cookie):
    """Bilibili WBI signing. The mixin key comes from nav and is cached once
    per process — nav is fetched on the first signed call only."""
    global _mixin_key_cache
    if _mixin_key_cache is None:
        nav = get('https://api.bilibili.com/x/web-interface/nav', cookie)
        img = nav['data']['wbi_img']['img_url'].split('/')[-1].split('.')[0]
        sub = nav['data']['wbi_img']['sub_url'].split('/')[-1].split('.')[0]
        _mixin_key_cache = ''.join((img + sub)[i] for i in MIXIN)[:32]
    p = dict(params)
    p['wts'] = int(time.time())
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q + _mixin_key_cache).encode()).hexdigest()
    return urllib.parse.urlencode(sorted(p.items()))


def fetch_feed(cookie, pages=5):
    items, seen = [], set()
    for page in range(1, pages + 1):
        q = wbi_sign({'web_location': 1430650, 'fresh_type': 3,
                      'ps': 30, 'fresh_idx': page, 'fresh_idx_1h': page}, cookie)
        d = get('https://api.bilibili.com/x/web-interface/wbi/index/top/feed/rcmd?' + q, cookie)
        if d.get('code') != 0:
            print(f'  page {page}: code={d.get("code")} {d.get("message")}', file=sys.stderr)
            break
        batch = d['data']['item']
        new = 0
        for it in batch:
            bv = it.get('bvid')
            if bv and bv not in seen:
                seen.add(bv)
                items.append(it)
                new += 1
        print(f'  page {page}: {len(batch)} items, {new} new', file=sys.stderr)
        if new == 0:
            break
        time.sleep(1.5)   # stay gentle, avoid risk control
    return items


def fetch_tags(bvid, cookie):
    """Fetch one video's tags (the real topic signal). Returns [] on failure."""
    try:
        d = get(f'https://api.bilibili.com/x/tag/archive/tags?bvid={bvid}', cookie)
        if d.get('code') == 0:
            return [t['tag_name'] for t in (d.get('data') or [])]
    except Exception as e:
        print(f'  tags {bvid} failed: {e}', file=sys.stderr)
    return []


def enrich(items, cookie, limit=None):
    """Attach tags to each item. Defaults to all; limit is for quick trial runs."""
    target = items if limit is None else items[:limit]
    for i, it in enumerate(target, 1):
        it['_tags'] = fetch_tags(it.get('bvid'), cookie)
        if i % 10 == 0:
            print(f'  tags {i}/{len(target)}', file=sys.stderr)
        time.sleep(0.4)
    return items


def bucketed(seconds):
    m = seconds // 60
    if m < 1: return '<1min'
    if m < 5: return '1-5min'
    if m < 10: return '5-10min'
    if m < 30: return '10-30min'
    if m < 60: return '30-60min'
    return '>60min'


def age_bucket(ts):
    days = (time.time() - ts) / 86400
    if days < 1: return '<1d'
    if days < 7: return '1-7d'
    if days < 30: return '1-4w'
    if days < 365: return '1-12mo'
    return '>1y'


def report(items):
    up = collections.Counter(it['owner']['name'] for it in items)
    dur = collections.Counter(bucketed(it.get('duration', 0)) for it in items)
    age = collections.Counter(age_bucket(it.get('pubdate', 0)) for it in items)
    followed = sum(1 for it in items if it.get('is_followed'))
    reasons = collections.Counter(
        (it.get('rcmd_reason') or {}).get('content', 'none') if isinstance(it.get('rcmd_reason'), dict)
        else 'none' for it in items)
    # Official partition labels are unreliable across endpoints; the per-video
    # topic tags fetched by enrich() are the honest signal.
    L = []
    L.append(f'# Bilibili homepage feed distribution ({len(items)} items)\n')
    L.append('## Followed vs unfamiliar')
    L.append(f'- Followed UPs: {followed} ({followed*100//max(len(items),1)}%)')
    L.append(f'- Unfamiliar UPs: {len(items)-followed}\n')
    L.append('## Duration')
    for k in ['<1min','1-5min','5-10min','10-30min','30-60min','>60min']:
        if dur[k]: L.append(f'- {k}: {dur[k]}')
    L.append('\n## Age')
    for k in ['<1d','1-7d','1-4w','1-12mo','>1y']:
        if age[k]: L.append(f'- {k}: {age[k]}')
    L.append('\n## Most frequent UPs (top 15)')
    for name, c in up.most_common(15):
        L.append(f'- {c}x {name}')
    L.append(f'\n({len(up)} distinct UPs, top frequency {(up.most_common(1)[0][1] if up else 0)})')
    tagc = collections.Counter(t for it in items for t in (it.get('_tags') or []))
    if tagc:
        L.append('\n## Topic tags (top 25) — better than titles for seeing what the feed bets on')
        for t, c in tagc.most_common(25):
            L.append(f'- {c}x {t}')
    L.append('\n## Recommendation reasons')
    for k, c in reasons.most_common(10):
        L.append(f'- {c}x {k}')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cookie_file')
    ap.add_argument('--pages', type=int, default=5)
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-tags', action='store_true', help='skip tag fetching (fast, coarser distribution)')
    a = ap.parse_args()
    if a.pages < 1:
        ap.error('--pages must be >= 1')
    try:
        cookie, _ = load_cookie(a.cookie_file)
    except OSError as e:
        sys.exit(f'cannot read cookie file {a.cookie_file}: {e.strerror or e}')
    print('fetching feed…', file=sys.stderr)
    items = fetch_feed(cookie, a.pages)
    if not items:
        sys.exit('no items fetched (check whether the cookie is valid / expired)')
    if not a.no_tags:
        print('fetching tags…', file=sys.stderr)
        enrich(items, cookie)
    # keep the raw JSON around for later inspection
    raw_path = (a.out or 'dist') + '.raw.json'
    with open(raw_path, 'w') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    text = report(items)
    if a.out:
        with open(a.out, 'w') as f:
            f.write(text)
    print(text)
    print(f'\nraw data: {raw_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
