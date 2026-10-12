#!/usr/bin/env python3
"""B站首页个性化推荐流抓取 + 分布统计。

用途：拿到某个用户的 SESSDATA 后，抓他首页个性化推荐、出分布，量化"他想要的推荐"
与"B站给的推荐"之间的差距。这是诊断脚本，长期方案是 assets/ 里的油猴脚本。

用法：
    python3 bili_dist.py <cookie_file> [--pages N] [--out dist.md]

cookie_file 格式（一行一个）：
    SESSDATA=xxxx
    buvid3=xxxx
（DedeUserID 可选；bili_jct 不需要——本脚本只读。）
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
    # encoding='utf-8-sig' 自动吃掉 Windows 记事本可能写的 BOM
    with open(path, encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip().lstrip('\ufeff')   # 双保险
            if not line or line.startswith('#'):
                continue
            raw_lines.append(line)
            if '=' in line:
                k, v = line.split('=', 1)
                jar[k.strip()] = v.strip()

    # 容错：如果整份文件既没有键名又不是空，就把它当成"只贴了 SESSDATA 的值"。
    # B站 SESSDATA 的特征：含 %2C 分隔、通常 100+ 字符。
    if 'SESSDATA' not in jar:
        cands = [l for l in raw_lines if not l.startswith(('{', '['))]
        if len(cands) == 1 and len(cands[0]) > 40 and '%2C' in cands[0]:
            jar['SESSDATA'] = cands[0]
        else:
            sys.exit('cookie 文件里认不出 SESSDATA（键值对或裸值都不匹配）')

    # 没有 buvid3 时自动去要一个（缺它容易 412）
    if 'buvid3' not in jar:
        try:
            spi = get('https://api.bilibili.com/x/frontend/finger/spi',
                      '; '.join(f'{k}={v}' for k, v in jar.items()))
            b3 = (spi.get('data') or {}).get('b_3')
            if b3:
                jar['buvid3'] = b3
                print('  （已自动补 buvid3）', file=sys.stderr)
        except Exception as e:
            print(f'  取 buvid3 失败（继续尝试）: {e}', file=sys.stderr)

    return '; '.join(f'{k}={v}' for k, v in jar.items()), jar


def get(url, cookie):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Referer': 'https://www.bilibili.com/',
        'Cookie': cookie,
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)


def wbi_sign(params, cookie):
    """B站 WBI 签名。keys 从 nav 取，全局缓存一次即可。"""
    nav = get('https://api.bilibili.com/x/web-interface/nav', cookie)
    img = nav['data']['wbi_img']['img_url'].split('/')[-1].split('.')[0]
    sub = nav['data']['wbi_img']['sub_url'].split('/')[-1].split('.')[0]
    raw = img + sub
    mixin_key = ''.join(raw[i] for i in MIXIN)[:32]
    p = dict(params)
    p['wts'] = int(time.time())
    q = urllib.parse.urlencode(sorted(p.items()))
    p['w_rid'] = hashlib.md5((q + mixin_key).encode()).hexdigest()
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
        print(f'  page {page}: {len(batch)} 条，{new} 条新', file=sys.stderr)
        if new == 0:
            break
        time.sleep(1.5)   # 温和，别触发风控
    return items


def fetch_tags(bvid, cookie):
    """取单个视频的标签（话题分类的真来源）。失败返回 []。"""
    try:
        d = get(f'https://api.bilibili.com/x/tag/archive/tags?bvid={bvid}', cookie)
        if d.get('code') == 0:
            return [t['tag_name'] for t in (d.get('data') or [])]
    except Exception as e:
        print(f'  tags {bvid} 失败: {e}', file=sys.stderr)
    return []


def enrich(items, cookie, limit=None):
    """给每条视频补标签。默认全量；limit 用于快速试跑。"""
    target = items if limit is None else items[:limit]
    for i, it in enumerate(target, 1):
        it['_tags'] = fetch_tags(it.get('bvid'), cookie)
        if i % 10 == 0:
            print(f'  标签 {i}/{len(target)}', file=sys.stderr)
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
    if days < 1: return '<1天'
    if days < 7: return '1-7天'
    if days < 30: return '1-4周'
    if days < 365: return '1-12月'
    return '>1年'


def report(items):
    up = collections.Counter(it['owner']['name'] for it in items)
    dur = collections.Counter(bucketed(it.get('duration', 0)) for it in items)
    age = collections.Counter(age_bucket(it.get('pubdate', 0)) for it in items)
    followed = sum(1 for it in items if it.get('is_followed'))
    reasons = collections.Counter(
        (it.get('rcmd_reason') or {}).get('content', '无理由') if isinstance(it.get('rcmd_reason'), dict)
        else '无理由' for it in items)
    # B站官方分区标签常在 business_info / av_feature，不稳；主题靠标题词频粗看
    L = []
    L.append(f'# B站首页推荐分布（{len(items)} 条）\n')
    L.append(f'## 关注 vs 陌生\n- 已关注 UP：{followed} 条（{followed*100//max(len(items),1)}%）')
    L.append(f'- 陌生 UP：{len(items)-followed} 条\n')
    L.append('## 时长分布')
    for k in ['<1min','1-5min','5-10min','10-30min','30-60min','>60min']:
        if dur[k]: L.append(f'- {k}: {dur[k]}')
    L.append('\n## 新旧分布')
    for k in ['<1天','1-7天','1-4周','1-12月','>1年']:
        if age[k]: L.append(f'- {k}: {age[k]}')
    L.append('\n## 出现最多的 UP（top15）')
    for name, c in up.most_common(15):
        L.append(f'- {c}× {name}')
    L.append(f'\n（共 {len(up)} 个不同 UP，{(up.most_common(1)[0][1] if up else 0)} 条最高频）')
    # 标签分布（若已 enrich）
    tagc = collections.Counter(t for it in items for t in (it.get('_tags') or []))
    if tagc:
        L.append('\n## 话题标签（top 25）——比标题更能看出推荐在押什么题')
        for t, c in tagc.most_common(25):
            L.append(f'- {c}× {t}')
    L.append('\n## 推荐理由分布')
    for k, c in reasons.most_common(10):
        L.append(f'- {c}× {k}')
    return '\n'.join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cookie_file')
    ap.add_argument('--pages', type=int, default=5)
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-tags', action='store_true', help='跳过标签抓取（快，但分布粗）')
    a = ap.parse_args()
    cookie, _ = load_cookie(a.cookie_file)
    print('抓取中……', file=sys.stderr)
    items = fetch_feed(cookie, a.pages)
    if not items:
        sys.exit('没抓到内容（检查 cookie 是否有效/是否过期）')
    if not a.no_tags:
        print('补标签中……', file=sys.stderr)
        enrich(items, cookie)
    # 存原始，方便后面细看
    raw_path = (a.out or 'dist') + '.raw.json'
    with open(raw_path, 'w') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    text = report(items)
    if a.out:
        with open(a.out, 'w') as f:
            f.write(text)
    print(text)
    print(f'\n原始数据: {raw_path}', file=sys.stderr)


if __name__ == '__main__':
    main()
