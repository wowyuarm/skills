// ==UserScript==
// @name         Bili 自定义流
// @namespace    bili.custom.feeds
// @version      1.1
// @description  自己定义几条推荐流，而不是被算法喂。配方集中在顶部 FEEDS，改一行即可。
// @match        https://www.bilibili.com/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

/*
 * 空壳模板：逻辑齐全，配方留白，由使用者自己的行为当数据源。
 * 每个新装的人只需要填自己的 FEEDS，不用改逻辑。
 *
 * 用法
 *  - 右下角出现「自定义流」按钮，点开是一个面板，每条流一个标签页。
 *  - 想改规则 → 改本文件顶部的 FEEDS，保存，刷新页面即生效。
 *  - 首次点某条流要等十几秒（要抓种子），之后有缓存就快。「换一批」可换种子。
 *
 * 为什么做成面板而不是塞进首页
 *  - B站首页 DOM 改版频繁，硬塞进去很容易坏。面板自成一格，B站怎么改都不影响。
 *
 * 数据从哪来（都用浏览器自己的登录态，不经过任何第三方）
 *  - following      : 你关注 UP 的新投稿（动态流，一次请求覆盖全部关注）
 *  - followedUps    : 关注动态流里只要够长的（「长片」流用）
 *  - expandFollowed : 拿关注里的长片当锚，顺相关推荐往外扩（「深挖」流用）
 *  - search         : 关键词搜索（需要 WBI 签名）
 *  - ranking        : 排行榜（rid=0 全站；rids=[...] 可多分区混取）
 *  - upRecent       : 指定 UP 的最近投稿
 *  - expand         : 用你投币/收藏/点赞/看完过的视频当锚，顺着“相关推荐”往外扩
 *  - related        : 你指定 bvid 的“相关推荐”
 */

(function () {
  'use strict';

  // ═══════════════════════════ 配方：要改的就是这里 ═══════════════════════════
  // 目标：高质量的视频，尤其是"我投币的那类"。
  // 思路：把"我投过币 / 收藏过"的片子当种子，顺着它们的相关推荐往外扩——
  //       不靠 B站算法猜，靠我自己已经认可过的东西当锚。
  //
  // ── 先定两个跟人相关的开关（放在 FEEDS 之前，下面会引用到）──
  // PINNED_UPS：不管抽签抽到谁，这几个人「每轮必查」。
  //   「长片」和「指定UP」都从这里取人。想让谁优先级更高，把名字或 mid 加进来。
  //   填名字或 mid 都行；名字写错不会报错，只会被跳过（控制台会打印「找不到 UP」）。
  //   留空也能用：那时「长片」完全按关注动态流走，「指定UP」是空的（面板会给提示）。
  const PINNED_UPS = [
    // '某个UP的名字',    // 例：写名字
    // 123456,            // 例：写 mid
  ];
  // 「长片」流没登录时（动态流拿不到）退回「按人查投稿」，一次查几个人。
  // 别调太大：那个接口连打十几个就会被限流。每个人查过之后缓存 6 小时，
  // 所以只有第一次开这条流要等，之后基本是秒出。
  const FOLLOWED_SAMPLE = 12;

  const FEEDS = [
    {
      name: '投币同款',
      sources: [
        { type: 'expand', seeds: 'coins', perSeed: 3 },     // 我投币的（最硬的认可）
        { type: 'expand', seeds: 'favs', perSeed: 10 },     // 我收藏的
        { type: 'expand', seeds: 'watched', perSeed: 12 },  // 我看完的（历史里最富的信号）
      ],
      filters: { excludeKeywords: ['广告'], minDuration: 120, maxDuration: null,
                 excludeSeen: true, minView: 20000, maxAgeDays: 1825 },
      sort: 'quality',
      limit: 60,
    },
    {
      // 从「我关注的人」里挑长视频。
      // 依据：关注列表是我自己一份份点出来的，比算法更知道我认谁——脚本以前从没用过它。
      // 走关注动态流（一次请求覆盖全部关注），不按人挨个查——那样会被风控。
      name: '长片',
      sources: [
        { type: 'followedUps', pages: 3, minDur: 600 },
      ],
      filters: { excludeKeywords: [], minDuration: 600, maxDuration: null, excludeSeen: true },
      sort: 'density',                                  // 弹幕+评论密度 × 片长加成
      limit: 60,
    },
    {
      // 「横向拓展 + 再深挖」：拿上面那些关注 UP 的长视频当锚，顺着相关推荐
      // 找到同类内容，但作者多半是我还没关注的人。这一层才有新东西。
      name: '深挖',
      sources: [
        { type: 'expandFollowed', perSeed: 10, seedMinDur: 600 },
      ],
      filters: { excludeKeywords: ['广告'], minDuration: 300, maxDuration: null,
                 excludeSeen: true, minView: 10000, maxAgeDays: 1825 },
      sort: 'quality',                                  // 这里能拿到投币/收藏，用真质量分
      limit: 60,
    },
    {
      // 跳出茧房：从全站榜里只留「我平时不看的」分区和 UP，混着给你换口味。
      // 有依据：依据是你观看历史统计出的常看分区/常看 UP（看够 8 次才算常看）。
      // 想更狠就把 broadRids 打开（多取几个你几乎不碰的分区）。
      name: '出圈',
      sources: [
        { type: 'ranking', rid: 0 },
        // { type: 'ranking', rids: [1, 36, 119, 155, 160, 168, 188, 223, 234] },  // 冷门分区混取
      ],
      filters: { excludeKeywords: [], minDuration: 180, maxDuration: null, excludeSeen: true,
                 excludeMyTnames: true, excludeMyUps: true, minView: 50000 },
      sort: 'hot',
      limit: 40,
    },
    {
      name: '今天',
      sources: [
        { type: 'following' },
      ],
      filters: { excludeKeywords: [], minDuration: 0, maxDuration: null, excludeSeen: true },
      sort: 'newest',
      limit: 60,
    },
    {
      // 想盯哪个 UP，把名字填进去（比关键词搜索准，搜索会拉教辅/网课）。
      // 这里默认取上面 PINNED_UPS 里点名的那几个；也可以直接在 ups 里写。
      // 两边都空着这条流就是空的，面板会提示你填哪。
      name: '指定UP',
      sources: [
        { type: 'upRecent', ups: PINNED_UPS.slice(), pages: 1 },
      ],
      filters: { excludeKeywords: [], minDuration: 0, maxDuration: null, excludeSeen: true },
      sort: 'newest',
      limit: 60,
    },
  ];

  // 永远不出现的 UP 名（精确匹配）
  const GLOBAL_BLOCK_UP = [];
  // 永远不出现的关键词（命中标题或标签即丢）
  const GLOBAL_BLOCK_KW = ['激励计划', '带货', '旗舰店', '预售', '招商'];
  // 质量排序用：低于这个播放量的，互动率噪声太大，不参与质量排序的加权
  const QUALITY_MIN_VIEW = 20000;
  // 「出圈」用：观看历史里某个分区/UP 出现几次才算「我常看」
  const TNAME_MIN_SAMPLE = 8;
  // UP 名 → mid 的映射存这里，抽签时直接用，不用每次搜索
  const FOLLOW_KEY = 'bcf_follows';
  // ═══════════════════════════════════════════════════════════════════════════

  const UA_OK = /bilibili\.com/.test(location.hostname);
  if (!UA_OK) return;

  // ────────────────────────── 基础工具 ──────────────────────────
  const MIXIN = [46,47,18,2,53,8,23,32,15,50,10,31,58,3,45,35,27,43,5,49,33,9,42,19,29,28,
                 14,39,12,38,41,13,37,48,7,16,24,55,40,61,26,17,0,1,60,51,30,4,22,25,54,21,
                 56,59,6,63,57,62,11,36,20,34,44,52];
  let _wbiKey = null;

  async function wbiKeys() {
    if (_wbiKey) return _wbiKey;
    const r = await fetch('https://api.bilibili.com/x/web-interface/nav', { credentials: 'include' });
    const d = await r.json();
    const img = d.data.wbi_img.img_url.split('/').pop().split('.')[0];
    const sub = d.data.wbi_img.sub_url.split('/').pop().split('.')[0];
    _wbiKey = (img + sub).split('').map((_, i) => (img + sub)[MIXIN[i]]).slice(0, 32).join('');
    return _wbiKey;
  }

  // 统一出口：任何一次请求失败（限流/网络抖动）都退避重试，最多 3 次。
  // 之前踩的坑：请求发太密偶发 "Failed to fetch"，没有重试 ⇒ 种子少一半。
  //
  // 例外：拿到 HTML（B站的拦截页，不是 JSON）时立刻放弃，不重试。
  // 那是风控在说「你打太快了」——再重试只会越陷越深（实测：连打十几个 UP 就会这样）。
  async function fetchJson(url, tries) {
    tries = tries || 3;
    let lastErr;
    for (let i = 0; i < tries; i++) {
      try {
        const r = await fetch(url, { credentials: 'include' });
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const txt = await r.text();
        if (txt.charCodeAt(0) === 60) throw new Error('BLOCKED(html)');   // 60 = '<'
        return JSON.parse(txt);
      } catch (e) {
        lastErr = e;
        if (String(e.message) === 'BLOCKED(html)') break;                 // 风控，别硬撞
        if (i < tries - 1) await sleep(700 * (i + 1) + Math.random() * 500);  // 0.7s / 1.4s
      }
    }
    throw lastErr;
  }

  // 统一 code 检查：B站的失败经常不是抛异常，而是 HTTP 200 + code!=0 + 空 data。
  // 不查 code 就会把「被风控/没登录」当成「这里没内容」——静默出错最难查。
  function ensureOk(d, what) {
    if (d && d.code === 0) return d;
    const c = d ? d.code : 'no-json';
    const isRisk = c === -352 || c === -412 || c === -509;
    throw new Error((isRisk ? 'BLOCKED' : 'api') + '(code ' + c + ') ' + what + ' ' + ((d && d.message) || ''));
  }

  async function apiGet(url, params) {
    const u = new URL(url);
    if (params) for (const [k, v] of Object.entries(params)) u.searchParams.set(k, v);
    return fetchJson(u.toString());
  }

  async function wbiGet(path, params) {
    const key = await wbiKeys();
    const p = { ...params, wts: Math.floor(Date.now() / 1000) };
    const q = Object.keys(p).sort().map(k => `${encodeURIComponent(k)}=${encodeURIComponent(p[k])}`).join('&');
    const w_rid = md5(q + key);
    return fetchJson(`https://api.bilibili.com${path}?${q}&w_rid=${w_rid}`);
  }

  // 纯 JS md5（WBI 签名用）
  function md5(s) {
    function rl(n, c) { return (n << c) | (n >>> (32 - c)); }
    function au(x, y) { const l = (x & 0xffff) + (y & 0xffff); return (((x >> 16) + (y >> 16) + (l >> 16)) << 16) | (l & 0xffff); }
    function cmn(q, a, b, x, s, t) { return au(rl(au(au(a, q), au(x, t)), s), b); }
    function ff(a,b,c,d,x,s,t){return cmn((b&c)|((~b)&d),a,b,x,s,t);}
    function gg(a,b,c,d,x,s,t){return cmn((b&d)|(c&(~d)),a,b,x,s,t);}
    function hh(a,b,c,d,x,s,t){return cmn(b^c^d,a,b,x,s,t);}
    function ii(a,b,c,d,x,s,t){return cmn(c^(b|(~d)),a,b,x,s,t);}
    function tb(str){const n=[];for(let i=0;i<str.length*8;i+=8){n[i>>5]|=(str.charCodeAt(i/8)&0xff)<<(i%32);}return n;}
    function th(num){let str='';for(let i=0;i<num.length*32;i+=8){str+=String.fromCharCode((num[i>>5]>>>(i%32))&0xff);}return str;}
    function utf8(str){return unescape(encodeURIComponent(str));}
    const x = tb(utf8(s)), len = utf8(s).length * 8;
    x[len >> 5] |= 0x80 << (len % 32);
    x[(((len + 64) >>> 9) << 4) + 14] = len;
    let a=1732584193,b=-271733879,c=-1732584194,d=271733878;
    for(let i=0;i<x.length;i+=16){
      const oa=a,ob=b,oc=c,od=d;
      a=ff(a,b,c,d,x[i],7,-680876936);d=ff(d,a,b,c,x[i+1],12,-389564586);c=ff(c,d,a,b,x[i+2],17,606105819);b=ff(b,c,d,a,x[i+3],22,-1044525330);
      a=ff(a,b,c,d,x[i+4],7,-176418897);d=ff(d,a,b,c,x[i+5],12,1200080426);c=ff(c,d,a,b,x[i+6],17,-1473231341);b=ff(b,c,d,a,x[i+7],22,-45705983);
      a=ff(a,b,c,d,x[i+8],7,1770035416);d=ff(d,a,b,c,x[i+9],12,-1958414417);c=ff(c,d,a,b,x[i+10],17,-42063);b=ff(b,c,d,a,x[i+11],22,-1990404162);
      a=ff(a,b,c,d,x[i+12],7,1804603682);d=ff(d,a,b,c,x[i+13],12,-40341101);c=ff(c,d,a,b,x[i+14],17,-1502002290);b=ff(b,c,d,a,x[i+15],22,1236535329);
      a=gg(a,b,c,d,x[i+1],5,-165796510);d=gg(d,a,b,c,x[i+6],9,-1069501632);c=gg(c,d,a,b,x[i+11],14,643717713);b=gg(b,c,d,a,x[i],20,-373897302);
      a=gg(a,b,c,d,x[i+5],5,-701558691);d=gg(d,a,b,c,x[i+10],9,38016083);c=gg(c,d,a,b,x[i+15],14,-660478335);b=gg(b,c,d,a,x[i+4],20,-405537848);
      a=gg(a,b,c,d,x[i+9],5,568446438);d=gg(d,a,b,c,x[i+14],9,-1019803690);c=gg(c,d,a,b,x[i+3],14,-187363961);b=gg(b,c,d,a,x[i+8],20,1163531501);
      a=gg(a,b,c,d,x[i+13],5,-1444681467);d=gg(d,a,b,c,x[i+2],9,-51403784);c=gg(c,d,a,b,x[i+7],14,1735328473);b=gg(b,c,d,a,x[i+12],20,-1926607734);
      a=hh(a,b,c,d,x[i+5],4,-378558);d=hh(d,a,b,c,x[i+8],11,-2022574463);c=hh(c,d,a,b,x[i+11],16,1839030562);b=hh(b,c,d,a,x[i+14],23,-35309556);
      a=hh(a,b,c,d,x[i+1],4,-1530992060);d=hh(d,a,b,c,x[i+4],11,1272893353);c=hh(c,d,a,b,x[i+7],16,-155497632);b=hh(b,c,d,a,x[i+10],23,-1094730640);
      a=hh(a,b,c,d,x[i+13],4,681279174);d=hh(d,a,b,c,x[i],11,-358537222);c=hh(c,d,a,b,x[i+3],16,-722521979);b=hh(b,c,d,a,x[i+6],23,76029189);
      a=hh(a,b,c,d,x[i+9],4,-640364487);d=hh(d,a,b,c,x[i+12],11,-421815835);c=hh(c,d,a,b,x[i+15],16,530742520);b=hh(b,c,d,a,x[i+2],23,-995338651);
      a=ii(a,b,c,d,x[i],6,-198630844);d=ii(d,a,b,c,x[i+7],10,1126891415);c=ii(c,d,a,b,x[i+14],15,-1416354905);b=ii(b,c,d,a,x[i+5],21,-57434055);
      a=ii(a,b,c,d,x[i+12],6,1700485571);d=ii(d,a,b,c,x[i+3],10,-1894986606);c=ii(c,d,a,b,x[i+10],15,-1051523);b=ii(b,c,d,a,x[i+1],21,-2054922799);
      a=ii(a,b,c,d,x[i+8],6,1873313359);d=ii(d,a,b,c,x[i+15],10,-30611744);c=ii(c,d,a,b,x[i+6],15,-1560198380);b=ii(b,c,d,a,x[i+13],21,1309151649);
      a=ii(a,b,c,d,x[i+4],6,-145523070);d=ii(d,a,b,c,x[i+11],10,-1120210379);c=ii(c,d,a,b,x[i+2],15,718787259);b=ii(b,c,d,a,x[i+9],21,-343485551);
      a=au(a,oa);b=au(b,ob);c=au(c,oc);d=au(d,od);
    }
    return (th([a,b,c,d]).split('').map(c=>('0'+(c.charCodeAt(0)&0xff).toString(16)).slice(-2)).join(''));
  }

  // ────────────────────── 各来源 → 统一格式 ──────────────────────
  // 统一条目：{ bvid, title, up, upMid, dur(秒), pubdate(秒), view, pic, tname, _src }
  function norm(o) { return o; }

  // 关注动态流。一次请求就能翻到「我全部关注的人」的最新投稿（约 20 条一页），
  // 而不是按人一个个去查——这是所有数据里性价比最高的一条：
  // 那些 UP 是我自己一个个点出来的，这是我最直接的认可，而且它不怕风控。
  //
  // 注意：动态流要登录。它只返回「关注的人近期发的」，也就是新片；
  // 想挖某个 UP 的老片，用下面的 upRecent / followedUps。
  async function srcFollowing(src) {
    const out = [];
    const pages = (src && src.pages) || 3;
    for (let page = 1; page <= pages; page++) {
      const d = await apiGet('https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/all',
        { type: 'video', page });
      const items = (d.data && d.data.items) || [];
      for (const it of items) {
        const m = it.modules || {};
        const maj = (m.module_dynamic && m.module_dynamic.major) || {};
        const a = maj.archive;
        if (!a) continue;
        const au = m.module_author || {};
        out.push(norm({
          bvid: a.bvid, title: a.title, up: au.name, upMid: au.mid,
          dur: parseDur(a.duration_text), pubdate: a.pubdate || 0,
          view: parseInt(((a.stat && a.stat.play) || '0').replace(/[^\d]/g, '')) || 0,
          pic: a.cover, tname: '', _src: '关注:' + (au.name || ''),
        }));
      }
      if (items.length < 20) break;
      await sleep(700);
    }
    return out;
  }

  async function srcSearch(src) {
    const out = [];
    for (const kw of (src.keywords || [])) {
      const pages = src.pages || 1;
      for (let page = 1; page <= pages; page++) {
        const d = await wbiGet('/x/web-interface/wbi/search/type',
          { search_type: 'video', keyword: kw, page, page_size: 30 });
        const res = (d.data && d.data.result) || [];
        for (const r of res) {
          if (!r.bvid) continue;
          out.push(norm({
            bvid: r.bvid, title: strip(r.title), up: r.author, upMid: r.mid,
            dur: parseDur(r.duration), pubdate: r.pubdate || 0,
            view: r.play || 0, pic: r.pic ? (r.pic.startsWith('//') ? 'https:' + r.pic : r.pic) : '',
            tname: r.typename || '', _src: 'search:' + kw,
          }));
        }
        await sleep(500);
      }
    }
    return out;
  }

  async function srcRanking(src) {
    // rid 可以是单个，也可以是数组（多个分区混着取，用来“跳出茧房”）
    const rids = Array.isArray(src.rids) ? src.rids : [src.rid != null ? src.rid : 0];
    const out = [];
    for (const rid of rids) {
      try {
        const d = ensureOk(await apiGet('https://api.bilibili.com/x/web-interface/ranking/v2', { rid, type: 'all' }), 'ranking rid=' + rid);
        for (const v of ((d.data && d.data.list) || [])) {
          out.push(norm({
            bvid: v.bvid, title: v.title, up: v.owner && v.owner.name, upMid: v.owner && v.owner.mid,
            dur: v.duration, pubdate: v.pubdate || 0,
            view: (v.stat && v.stat.view) || 0, pic: v.pic, tname: v.tname || '',
            _src: 'rank:' + (v.tname || rid),
          }));
        }
      } catch (e) { console.warn('[bcf] ranking 失败 rid=' + rid, e); }
      if (rids.length > 1) await sleep(300);
    }
    return out;
  }

  // UP 名 → mid 缓存（localStorage，避免每次都搜索）。带 7 天过期——UP 改名/换号后不至于永远错下去。
  const MID_KEY = 'bcf_mids_v2';
  const MID_TTL = 7 * 86400e3;
  function midCache() { try { return JSON.parse(localStorage.getItem(MID_KEY) || '{}'); } catch { return {}; } }
  function saveMid(name, mid) {
    try { const c = midCache(); c[name] = { m: mid, t: Date.now() + MID_TTL }; localStorage.setItem(MID_KEY, JSON.stringify(c)); } catch {}
  }
  async function resolveMid(name) {
    if (/^\d+$/.test(name)) return +name;          // 直接写 mid 也行
    const c = midCache();
    const hit = c[name];
    if (hit && hit.t > Date.now()) return hit.m;
    const d = await wbiGet('/x/web-interface/wbi/search/type',
      { search_type: 'bili_user', keyword: name, page: 1, page_size: 10 });
    const res = (d.data && d.data.result) || [];
    const exact = res.find(u => u.uname === name) || res[0];
    if (!exact) return null;
    saveMid(name, exact.mid);
    return exact.mid;
  }

  // 抓某个 UP 的近期投稿。order 可选 pubdate（最新）或 click（最多播放）。
  // 注意：这个接口给的统计只有 play / video_review(弹幕) / comment，没有投币和收藏，
  // 所以走这里的条目不能直接用 qualityScore（它要 coin/fav）——见 densityScore。
  //
  // 这个接口是最容易被限流的一个：连打十几个 UP 就会返回一段 HTML 拦截页（不是 JSON），
  // 表现成「这条流突然空了」。所以每次结果都按 UP 缓存 6 小时——第二次开流几乎不发请求。
  const UPV_KEY = 'bcf_upv';
  function upvCache() { try { return JSON.parse(localStorage.getItem(UPV_KEY) || '{}'); } catch { return {}; } }
  function upvGet(mid) {
    const c = upvCache()[mid];
    return c && c.t > Date.now() ? c.list : null;
  }
  function upvPut(mid, list) {
    try {
      const c = upvCache();
      c[mid] = { t: Date.now() + 6 * 3600e3, list };
      const ks = Object.keys(c);
      if (ks.length > 200) ks.sort((a, b) => c[a].t - c[b].t).slice(0, ks.length - 200).forEach(k => delete c[k]);
      localStorage.setItem(UPV_KEY, JSON.stringify(c));
    } catch {}
  }
  async function fetchUpVideos(mid, ps, pn, order) {
    const fresh = upvGet(mid);
    if (fresh) return fresh;
    const d = await wbiGet('/x/space/wbi/arc/search', { mid, ps, pn, order: order || 'pubdate' });
    // 必须看 code：被风控时它返回 -352 和一个空的 data，不是抛异常。
    // 不看的话就会把「被拦了」当成「这个人最近没发长片」——静默出错最难查。
    ensureOk(d, 'up videos mid=' + mid);
    const vl = (((d.data || {}).list) || {}).vlist || [];
    if (vl.length) upvPut(mid, vl);           // 只有真拿到东西才缓存，别把失败也记进去
    return vl;
  }

  async function srcUpRecent(src) {
    const out = [];
    const pages = src.pages || 1;
    for (const name of (src.ups || [])) {
      const mid = await resolveMid(name);
      if (!mid) { console.warn('[bcf] 找不到 UP:', name); continue; }
      for (let pn = 1; pn <= pages; pn++) {
        try {
          const vl = await fetchUpVideos(mid, 30, pn, 'pubdate');
          for (const v of vl) {
            out.push(norm({
              bvid: v.bvid, title: v.title, up: v.author, upMid: mid,
              dur: parseDur(v.length), pubdate: v.created || 0,
              view: v.play || 0, danmaku: v.video_review || 0, comment: v.comment || 0,
              pic: v.pic ? (v.pic.startsWith('//') ? 'https:' + v.pic : v.pic) : '',
              tname: '', _src: 'up:' + name,
            }));
          }
        } catch (e) { console.warn('[bcf] upRecent 失败', name, e); }
        await sleep(700);
      }
    }
    return out;
  }

  // ── 我的关注列表 ──
  // 这是脚本里最有依据的一份数据：这些 UP 是我自己一个个点出来的关注。
  // 关注列表要登录才拿得到；拿到后缓存 7 天，之后抽签不必再取。
  function followCache() {
    try {
      const c = JSON.parse(localStorage.getItem(FOLLOW_KEY) || 'null');
      if (c && c.t && Date.now() < c.t && Array.isArray(c.list)) return c.list;
    } catch {}
    return null;
  }
  function saveFollows(list) {
    try {
      localStorage.setItem(FOLLOW_KEY, JSON.stringify({ t: Date.now() + 7 * 86400e3, list }));
    } catch {}
  }
  let _follows = null, _followsFlight = null;
  async function myFollows() {
    if (_follows) return _follows;
    if (_followsFlight) return _followsFlight;
    _followsFlight = (async () => {
      const cached = followCache();
      if (cached) return (_follows = cached);
      try {
        const uid = await myMid();
        const list = [];
        for (let pn = 1; pn <= 6; pn++) {                  // 关注多时 3 页就够；多留几页
          const d = ensureOk(await apiGet('https://api.bilibili.com/x/relation/followings',
            { vmid: uid, pn, ps: 50, order: 'desc', order_type: 'attention' }), 'followings');
          const l = ((d.data) || {}).list || [];
          for (const u of l) if (u.mid && u.uname) list.push({ mid: u.mid, uname: u.uname });
          if (l.length < 50) break;
          await sleep(600);
        }
        if (list.length) { saveFollows(list); _follows = list; }
        else console.warn('[bcf] 关注列表是空的（没登录？）——退回只查点名的那几个');
        return _follows;
      } catch (e) {
        // 没登录 / 接口变了 / 被限流：不要把异常抛到上面，那会让整条流空掉。
        console.warn('[bcf] 取关注列表失败，退回只查点名的那几个：', e.message || e);
        return null;
      }
    })();
    try { return await _followsFlight; } finally { _followsFlight = null; }
  }

  // 抽签：从关注里抽 n 个人，外加 PINNED_UPS 里点名的那几个（每轮必查）。
  // 为什么要抽而不是全查：关注列表挨个查就是每人一次请求，上百次连发 B站很快给 -352 风控。
  // 抽到的这把人存进 localStorage 记 6 小时，所以同一批不会每次刷新都变。
  const PICK_KEY = 'bcf_pick';
  function pickCache() {
    try { return JSON.parse(localStorage.getItem(PICK_KEY) || 'null'); } catch { return null; }
  }
  function savePick(list) {
    try { localStorage.setItem(PICK_KEY, JSON.stringify({ t: Date.now() + 6 * 3600e3, list })); } catch {}
  }
  async function sampledUps(n) {
    const cached = pickCache();
    let picks;
    if (cached && cached.t > Date.now() && Array.isArray(cached.list) && cached.list.length) {
      picks = cached.list;
    } else {
      const follows = await myFollows();
      const pool = (follows || []).slice();
      if (!pool.length) {
        // 没登录 / 关注拿不到：退回到只查点名的那几个，别让整条流空着。
        // 注意这里不写缓存——否则登录之后 6 小时内还是只查这几个人。
        picks = PINNED_UPS.map(u => ({ mid: u, uname: u }));
      } else {
        shuffle(pool);
        picks = pool.slice(0, n);
        savePick(picks);
      }
      console.log('[bcf] 本轮抽到', picks.length, '个 UP：', picks.map(p => p.uname || p.mid).join('、'));
    }
    // 钉住的那几个补进去（已在里面就不重复）。名字/ mid 都吃。
    const extra = PINNED_UPS.filter(p => !picks.some(x => x.mid === p || x.uname === p));
    return picks.map(p => p.mid).concat(extra);
  }

  // 「长片」：从关注动态流里只要够长的。
  // 为什么不用「按人查投稿」：全量关注挨个查要发上百次请求，B站立刻风控（实测 -352 / 拦截页）。
  // 动态流一次请求就覆盖全部关注，而且它是「最新投稿」，正好是这个流要的东西。
  // 动态流要登录；拿不到时（没登录）退回按人查点名的那几个——那条路慢但至少不是空的。
  async function srcFollowedUps(src) {
    const minDur = src.minDur || 600;
    const out = [];
    const raw = await srcFollowing({ pages: src.pages || 3 });
    for (const it of raw) {
      if ((it.dur || 0) >= minDur) out.push(it);
    }
    if (out.length) {
      console.log('[bcf] 长片：动态流拿到', raw.length, '条关注新片，其中 ≥' + Math.round(minDur / 60),
        '分钟的', out.length, '条');
      return out;
    }
    // 动态流是空的：多半是没登录。退回按人查点名的那几个。
    console.warn('[bcf] 长片：动态流没东西（没登录？），改查点名的那几个 UP');
    const ups = await sampledUps(FOLLOWED_SAMPLE);
    let got = 0, blocked = false;
    for (const midOrName of ups) {
      try {
        const mid = await resolveMid(midOrName);
        if (!mid) continue;
        const vl = await fetchUpVideos(mid, 30, 1, 'pubdate');
        got += vl.length;
        for (const v of vl) {
          const dur = parseDur(v.length);
          if (dur < minDur) continue;
          out.push(norm({
            bvid: v.bvid, title: v.title, up: v.author, upMid: mid,
            dur, pubdate: v.created || 0,
            view: v.play || 0, danmaku: v.video_review || 0, comment: v.comment || 0,
            pic: v.pic ? (v.pic.startsWith('//') ? 'https:' + v.pic : v.pic) : '',
            tname: '', _src: '关注:' + (v.author || ''),
          }));
        }
      } catch (e) {
        if (String(e.message).indexOf('BLOCKED') === 0) { blocked = true; break; }
        console.warn('[bcf] 长片：取投稿失败', mid, e.message || e);
      }
      await sleep(1400);
    }
    console.log('[bcf] 长片（按人查）：查了', ups.length, '人，拿到', got, '条投稿，够长的',
      out.length, '条', blocked ? '（被限流，提前收手）' : '');
    return out;
  }

  // 「深挖」：拿关注 UP 的长视频当锚，顺着「相关推荐」往外扩一层。
  // 这是「横向拓展再深入」里的第二层：相关推荐里的作者通常是我还没关注的人，
  // 所以这一层才真的能挖出新东西，而不只是把关注列表重排一遍。
  async function srcExpandFollowed(src) {
    // 锚 = 关注动态流里那些长片（一次请求拿到，不按人查）。
    // 挑长的当锚：长片的相关推荐也更可能是长片，这正是要挖的东西。
    let anchors = [];
    try {
      const raw = await srcFollowing({ pages: 2 });
      anchors = raw.filter(it => (it.dur || 0) >= (src.seedMinDur || 600))
        .map(it => ({ bvid: it.bvid, title: it.title, w: 1 }));
      console.log('[bcf] 深挖：动态流里挑到', anchors.length, '条长片当锚');
    } catch (e) { console.warn('[bcf] 深挖：动态流失败', e.message || e); }
    // 动态流拿不到（没登录）：退回用收藏/投币/看完当锚，至少这条流不是空的。
    let seeds = anchors;
    if (!seeds.length) {
      const s = await mySeeds();
      seeds = [...s.favs, ...s.coins, ...s.likes, ...s.watched];
      if (!seeds.length) { console.warn('[bcf] 深挖：关注和收藏都拿不到锚'); return []; }
    }
    const picks = weightedPick(seeds, src.perSeed || 10);
    const buckets = [];
    let fetched = 0;
    for (const seed of picks) {
      let bucket = relGet(seed.bvid);
      if (bucket) { buckets.push(bucket); continue; }
      bucket = [];
      try {
        const d = await apiGet('https://api.bilibili.com/x/web-interface/archive/related', { bvid: seed.bvid });
        for (const v of ((d.data) || [])) {
          const st = v.stat || {};
          bucket.push(norm({
            bvid: v.bvid, title: v.title, up: v.owner && v.owner.name, upMid: v.owner && v.owner.mid,
            dur: v.duration || 0, pubdate: v.pubdate || 0,
            view: st.view || 0, like: st.like || 0, coin: st.coin || 0, fav: st.favorite || 0,
            pic: v.pic, tname: v.tname || '', seedW: seed.w || 1,
            _src: '深挖:' + (seed.title || '').slice(0, 10),
          }));
        }
        relPut(seed.bvid, bucket);
      } catch (e) { console.warn('[bcf] 深挖失败', seed.bvid, e); }
      buckets.push(bucket);
      fetched++;
      await sleep(500);
    }
    if (fetched) console.log('[bcf] 深挖现抓', fetched, '个锚（其余走缓存）');
    const out = [];
    let more = true, idx = 0;
    while (more) {
      more = false;
      for (const b of buckets) if (idx < b.length) { out.push(b[idx]); more = true; }
      idx++;
    }
    return out;
  }

  // 种子缓存：存 localStorage，避免每次开页面都重抓一遍（慢 + 容易被限流）。
  // 一次抓全 → 存 6 小时；有请求失败 → 只存 10 分钟，稍后自己会重试补齐。
  const SEEDS_KEY = 'bcf_seeds_v3';
  function loadSeedsCache() {
    try {
      const c = JSON.parse(localStorage.getItem(SEEDS_KEY) || 'null');
      if (c && c.t && Date.now() < c.t && c.seeds) return c.seeds;
    } catch {}
    return null;
  }
  function saveSeedsCache(seeds, ok) {
    try {
      localStorage.setItem(SEEDS_KEY, JSON.stringify({
        t: Date.now() + (ok ? 6 * 3600e3 : 10 * 60e3), seeds,
      }));
    } catch {}
  }
  function dropSeedsCache() { try { localStorage.removeItem(SEEDS_KEY); } catch {} }

  // 拉"我自己的"种子视频（投币 / 收藏）。返回 [{bvid,title,tname}]
  let _mySeeds = null;
  let _seedsInFlight = null;                         // 并发去重：两条流同时要种子时只抓一次
  async function mySeeds(force) {
    if (_mySeeds) return _mySeeds;
    if (_seedsInFlight) return _seedsInFlight;
    if (force) dropSeedsCache();
    _seedsInFlight = _mySeedsLoad();
    try { return await _seedsInFlight; }
    finally { _seedsInFlight = null; }
  }
  async function _mySeedsLoad() {
    const cached = loadSeedsCache();
    if (cached) {
      _mySeeds = cached;
      console.log('[bcf] 种子走缓存：投币', cached.coins.length, '点赞', cached.likes.length,
        '收藏', cached.favs.length, '看完', cached.watched.length);
      return _mySeeds;
    }
    const seeds = { coins: [], likes: [], favs: [], watched: [], myTags: {}, myUps: {} };
    let fails = 0;                                    // 哪一步没抓全，就只短暂缓存
    const uid = await myMid();
    // 我投币的（B站上限 3 条，就这么多）—— 质量信号最强
    try {
      const d = ensureOk(await apiGet('https://api.bilibili.com/x/space/coin/video', { vmid: uid, pn: 1, ps: 30 }), 'coins');
      for (const v of ((d.data) || [])) seeds.coins.push({ bvid: v.bvid, title: v.title });
    } catch (e) { fails++; console.warn('[bcf] 取投币失败', e.message || e); }
    // 我点赞的（上限约 20 条）—— 次强信号
    try {
      for (let pn = 1; pn <= 2; pn++) {
        const d = ensureOk(await apiGet('https://api.bilibili.com/x/space/like/video', { vmid: uid, pn, ps: 30 }), 'likes');
        const lst = ((d.data) || {}).list || [];
        for (const v of lst) if (v.bvid) seeds.likes.push({ bvid: v.bvid, title: v.title });
        if (lst.length < 30) break;
        await sleep(400);
      }
    } catch (e) { fails++; console.warn('[bcf] 取点赞失败', e.message || e); }
    // 我收藏的（分页取，取前几页就够当种子）
    try {
      const fl = ensureOk(await apiGet('https://api.bilibili.com/x/v3/fav/folder/created/list-all', { up_mid: uid }), 'fav folders');
      const folders = ((fl.data) || {}).list || [];
      for (const f of folders) {
        for (let pn = 1; pn <= 2; pn++) {
          const d = ensureOk(await apiGet('https://api.bilibili.com/x/v3/fav/resource/list',
            { media_id: f.id, pn, ps: 20, platform: 'web' }), 'fav res ' + f.id);
          const medias = (((d.data) || {}).medias) || [];
          for (const m of medias) if (m.bvid && m.type === 2) seeds.favs.push({ bvid: m.bvid, title: m.title });
          if (!((d.data || {}).has_more)) break;
          await sleep(400);
        }
        await sleep(300);
        if (seeds.favs.length > 120) break;
      }
    } catch (e) { fails++; console.warn('[bcf] 取收藏失败', e.message || e); }
    // 我看完的（观看历史里 progress/duration >= 85%）—— 这是最富的一口井：
    // 历史能翻 1000+ 条，但"点开就走"的很多，只有"看完"才代表真认可。
    try {
      let maxv = 0, viewAt = 0;
      for (let i = 0; i < 12; i++) {                 // 12 页 × 30 ≈ 360 条，够抽种子
        const q = ensureOk(await wbiGet('/x/web-interface/history/cursor',
          { max: maxv, view_at: viewAt, business: '', ps: 30 }), 'history');
        const lst = ((q.data || {}).list) || [];
        if (!lst.length) break;
        for (const h of lst) {
          const d = h.duration || 0, p = h.progress || 0;
          const bv = (h.history || {}).bvid;
          if (!bv || !d) continue;
          // 顺带统计“我平时都在看哪些分区 / 哪些 UP” —— 这是「出圈」流的依据：
          // 只保留我平时不碰的分区，才能真的换口味，而不是又喂一遍同类。
          // 字段名注意：历史接口给的是 tag_name / author_name（不是 tag / author）。
          if (h.tag_name) seeds.myTags[h.tag_name] = (seeds.myTags[h.tag_name] || 0) + 1;
          if (h.author_name) seeds.myUps[h.author_name] = (seeds.myUps[h.author_name] || 0) + 1;
          const finished = p / d >= 0.85 || h.is_finish;
          if (finished) {
            // 权重随片长上升：看完 3 分钟 ≈ 1 分，看完 40 分钟 ≈ 3 分，看完 2 小时 ≈ 4 分。
            // 长视频看完是真金（要坐得住），B站首页算法恰恰不看这个。
            const w = 1 + Math.log2(Math.max(d, 60) / 60);
            seeds.watched.push({ bvid: bv, title: h.title || '', dur: d, w: Math.min(w, 4) });
          }
        }
        const cur = (q.data || {}).cursor || {};
        maxv = cur.max || 0; viewAt = cur.view_at || 0;
        if (!maxv) break;
        await sleep(500);
      }
    } catch (e) { fails++; console.warn('[bcf] 取观看历史失败', e.message || e); }
    _mySeeds = seeds;
    saveSeedsCache(seeds, fails === 0);
    console.log('[bcf] 种子：投币', seeds.coins.length, '点赞', seeds.likes.length,
      '收藏', seeds.favs.length, '看完', seeds.watched.length, fails ? `(有 ${fails} 项没抓全，10 分钟后重试)` : '(已缓存 6 小时)');
    return seeds;
  }

  let _myMid = null;
  async function myMid() {
    if (_myMid) return _myMid;
    const d = ensureOk(await apiGet('https://api.bilibili.com/x/web-interface/nav'), 'nav');
    if (!d.data || !d.data.mid) throw new Error('nav returned no mid (not logged in?)');
    _myMid = d.data.mid;
    return _myMid;
  }

  // 「相关推荐」结果缓存：同一个种子视频的结果存本地 6 小时。
  // 好处：① 再开这条流几乎瞬间出（不用再发一轮请求）② 少发请求 = 少被限流。
  // 种子是每次随机抽的 ⇒ 每次抽到不同种子时，命中不了的才现抓，抓过的都留下。
  const REL_KEY = 'bcf_related_v1';
  function relCache() { try { return JSON.parse(localStorage.getItem(REL_KEY) || '{}'); } catch { return {}; } }
  function relGet(bv) {
    const c = relCache()[bv];
    return c && c.t > Date.now() ? c.items : null;
  }
  function relPut(bv, items) {
    try {
      const c = relCache();
      c[bv] = { t: Date.now() + 6 * 3600e3, items };
      const ks = Object.keys(c);
      if (ks.length > 400) {                          // 太多就丢掉最早过期的那些
        ks.sort((a, b) => c[a].t - c[b].t).slice(0, ks.length - 400).forEach(k => delete c[k]);
      }
      localStorage.setItem(REL_KEY, JSON.stringify(c));
    } catch {}
  }
  function relClear() { try { localStorage.removeItem(REL_KEY); } catch {} }

  // expand：用种子视频的"相关推荐"往外扩（不靠 B站首页算法，靠我自己认可的锚）
  async function srcExpand(src) {
    const s = await mySeeds();
    let pool = src.seeds === 'favs' ? s.favs
      : src.seeds === 'coins' ? s.coins
      : src.seeds === 'likes' ? s.likes
      : src.seeds === 'watched' ? s.watched
      : src.seeds === 'all' ? [...s.coins, ...s.likes, ...s.favs, ...s.watched]
      : [];
    if (!pool.length) { console.warn('[bcf] expand 无种子:', src.seeds); return []; }
    // 带权抽样：种子的 w 越大（＝越长且看完了），越容易被选中当锚。
    // 没标 w 的（投币/收藏/点赞）给默认 1。
    const picks = weightedPick(pool, src.perSeed || 8);
    const buckets = [];
    let fetched = 0;
    for (const seed of picks) {
      let bucket = relGet(seed.bvid);
      if (bucket) { buckets.push(bucket); continue; }
      bucket = [];
      try {
        const d = await apiGet('https://api.bilibili.com/x/web-interface/archive/related', { bvid: seed.bvid });
        for (const v of ((d.data) || [])) {
          const st = v.stat || {};
          bucket.push(norm({
            bvid: v.bvid, title: v.title, up: v.owner && v.owner.name, upMid: v.owner && v.owner.mid,
            dur: v.duration || 0, pubdate: v.pubdate || 0,
            view: st.view || 0, like: st.like || 0, coin: st.coin || 0, fav: st.favorite || 0,
            pic: v.pic, tname: v.tname || '',
            seedW: seed.w || 1,                       // 种子权重，参与最终排序
            _src: 'exp:' + (seed.title || '').slice(0, 10),
          }));
        }
        relPut(seed.bvid, bucket);
      } catch (e) { console.warn('[bcf] expand 失败', seed.bvid, e); }
      buckets.push(bucket);
      fetched++;
      await sleep(500);
    }
    if (fetched) console.log('[bcf] expand 现抓', fetched, '个种子（其余走缓存）');
    // 交错：每个桶轮流取一条
    const out = [];
    let more = true, idx = 0;
    while (more) {
      more = false;
      for (const b of buckets) {
        if (idx < b.length) { out.push(b[idx]); more = true; }
      }
      idx++;
    }
    return out;
  }

  function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

  // 带权不放回抽样：w 越大越可能被选中。用于"看完的长视频"当种子时权重更高。
  function weightedPick(pool, k) {
    const a = pool.map(x => ({ x, w: Math.max(0.01, x.w || 1) }));
    const out = [];
    while (out.length < k && a.length) {
      const total = a.reduce((s, o) => s + o.w, 0);
      let r = Math.random() * total;
      let idx = 0;
      for (; idx < a.length; idx++) { r -= a[idx].w; if (r <= 0) break; }
      if (idx >= a.length) idx = a.length - 1;
      out.push(a[idx].x);
      a.splice(idx, 1);
    }
    return out;
  }

  async function srcRelated(src) {    const out = [];
    for (const bv of (src.bvids || [])) {
      const d = await apiGet('https://api.bilibili.com/x/web-interface/archive/related', { bvid: bv });
      for (const v of ((d.data) || [])) {
        out.push(norm({
          bvid: v.bvid, title: v.title, up: v.owner && v.owner.name, upMid: v.owner && v.owner.mid,
          dur: v.duration || 0, pubdate: v.pubdate || 0,
          view: (v.stat && v.stat.view) || 0, pic: v.pic, tname: v.tname || '', _src: 'related',
        }));
      }
      await sleep(500);
    }
    return out;
  }

  async function collect(feed) {
    const all = [];
    for (const s of feed.sources) {
      try {
        if (s.type === 'following') all.push(...await srcFollowing(s));
        else if (s.type === 'search') all.push(...await srcSearch(s));
        else if (s.type === 'ranking') all.push(...await srcRanking(s));
        else if (s.type === 'upRecent') all.push(...await srcUpRecent(s));
        else if (s.type === 'followedUps') all.push(...await srcFollowedUps(s));
        else if (s.type === 'expandFollowed') all.push(...await srcExpandFollowed(s));
        else if (s.type === 'expand') all.push(...await srcExpand(s));
        else if (s.type === 'related') all.push(...await srcRelated(s));
      } catch (e) { console.warn('[bcf] source failed', s, e); }
    }
    return all;
  }

  // ────────────────────────── 过滤 + 排序 ──────────────────────────
  const SEEN_KEY = 'bcf_seen';
  function seenSet() {
    try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || '[]')); } catch { return new Set(); }
  }
  function markSeen(bvids) {
    try {
      const s = seenSet();
      bvids.forEach(b => s.add(b));
      localStorage.setItem(SEEN_KEY, JSON.stringify([...s].slice(-3000)));
    } catch {}
  }

  // 我的口味画像：从观看历史统计出的「常看分区 / 常看 UP」。
  // 用来把「换个口味」做成有依据的：只保留我平时不碰的，而不是凭猜。
  function myTaste() {
    const s = _mySeeds || {};
    return { tags: s.myTags || {}, ups: s.myUps || {} };
  }
  // 这个 tname 是不是我平时常看的（出现过 TNAME_MIN_SAMPLE 次以上）
  function isMyTname(tname) {
    if (!tname) return false;
    const t = myTaste().tags;
    // 历史里的 tag 与排行里的 tname 不同源，用包含关系兜一层（如「电子竞技」vs「游戏」）
    for (const [k, v] of Object.entries(t)) {
      if ((k === tname || k.includes(tname) || tname.includes(k)) && v >= TNAME_MIN_SAMPLE) return true;
    }
    return false;
  }
  function isMyUp(up) {
    if (!up) return false;
    const u = myTaste().ups;
    return (u[up] || 0) >= TNAME_MIN_SAMPLE;
  }

  function applyFilters(items, f) {
    const seen = seenSet();
    const exKw = [...GLOBAL_BLOCK_KW, ...((f && f.excludeKeywords) || [])];
    const exUp = [...GLOBAL_BLOCK_UP, ...((f && f.excludeUps) || [])];
    const now = Date.now() / 1000;
    const seenSetLocal = new Set();
    return items.filter(it => {
      if (!it.bvid || !it.title) return false;
      const blob = (it.title + ' ' + (it.tname || '')).toLowerCase();
      for (const k of exKw) if (k && blob.includes(k.toLowerCase())) return false;
      for (const u of exUp) if (u && it.up === u) return false;
      // 「出圈」：只要我平时不看的（分区和 UP 都排掉熟悉的）
      if (f && f.excludeMyTnames && isMyTname(it.tname)) return false;
      if (f && f.excludeMyUps && isMyUp(it.up)) return false;
      if (f && f.minDuration && it.dur && it.dur < f.minDuration) return false;
      if (f && f.maxDuration && it.dur && it.dur > f.maxDuration) return false;
      if (f && f.minView && (it.view || 0) < f.minView) return false;
      if (f && f.maxAgeDays && it.pubdate && (now - it.pubdate) / 86400 > f.maxAgeDays) return false;
      if (f && f.excludeSeen && seen.has(it.bvid)) return false;
      if (seenSetLocal.has(it.bvid)) return false;   // 本流内去重
      seenSetLocal.add(it.bvid);
      return true;
    });
  }

  // 同一条流里，同一个 UP 最多留几条（防单个 UP 霸屏）
  function limitPerUp(items, max) {
    const c = {};
    const out = [];
    for (const it of items) {
      const k = it.up || '_';
      c[k] = (c[k] || 0) + 1;
      if (c[k] <= max) out.push(it);
    }
    return out;
  }

  // 质量分：看互动密度，不看绝对播放量（大号霸榜）。
  // 投币最贵（要花钱），权重最高；其次收藏、点赞。
  function qualityScore(it) {
    const v = it.view || 0;
    if (v < QUALITY_MIN_VIEW) return -1;             // 样本太小，不算
    const coinRate = (it.coin || 0) / v;
    const favRate = (it.fav || 0) / v;
    const likeRate = (it.like || 0) / v;
    const base = coinRate * 100 + favRate * 12 + likeRate * 3;
    // 来自"看完的长视频"这个锚的，按其权重(seedW)加成——长视频的质量信号更可信
    return base * (1 + 0.35 * ((it.seedW || 1) - 1));
  }

  // 密度分：给拿不到投币/收藏的那类条目用（关注 UP 的投稿只有弹幕和评论）。
  // 弹幕和评论都是「看完还想说两句」的行为，比播放量实在；再按片长加成——
  // 长片能把人留住的，本身就说明内容撑得住。
  function densityScore(it) {
    const v = it.view || 0;
    if (v < 5000) return -1;                         // 样本太小，噪声大
    const dmRate = (it.danmaku || 0) / v;
    const cmRate = (it.comment || 0) / v;
    const base = dmRate * 300 + cmRate * 200;
    // 10 分钟 ≈ 1 分，40 分钟 ≈ 1.6 分，2 小时 ≈ 2.3 分
    const durBoost = 1 + Math.log2(Math.max(it.dur || 60, 60) / 600) * 0.35;
    return base * Math.max(durBoost, 0.7);
  }

  function sortItems(items, mode) {
    const a = items.slice();
    if (mode === 'newest') a.sort((x, y) => (y.pubdate || 0) - (x.pubdate || 0));
    else if (mode === 'hot') a.sort((x, y) => (y.view || 0) - (x.view || 0));
    else if (mode === 'density') a.sort((x, y) => densityScore(y) - densityScore(x));
    else if (mode === 'quality') a.sort((x, y) => qualityScore(y) - qualityScore(x));
    return a;
  }

  // ────────────────────────── 小工具 ──────────────────────────
  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
  function strip(s) { return (s || '').replace(/<[^>]+>/g, ''); }
  function parseDur(t) {
    if (!t) return 0;
    if (typeof t === 'number') return t;
    const p = String(t).trim().split(':').map(Number);
    if (p.some(isNaN)) return 0;
    return p.reduce((a, n) => a * 60 + n, 0);
  }
  function fmtDur(s) {
    s = s || 0;
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60;
    return h ? `${h}:${String(m).padStart(2,'0')}:${String(ss).padStart(2,'0')}` : `${m}:${String(ss).padStart(2,'0')}`;
  }
  function fmtView(n) {
    n = n || 0;
    if (n >= 1e8) return (n / 1e8).toFixed(1) + '亿';
    if (n >= 1e4) return (n / 1e4).toFixed(1) + '万';
    return String(n);
  }
  function ago(ts) {
    if (!ts) return '';
    const d = Math.floor((Date.now() / 1000 - ts) / 86400);
    if (d <= 0) return '今天';
    if (d === 1) return '昨天';
    if (d < 30) return d + '天前';
    if (d < 365) return Math.floor(d / 30) + '个月前';
    return Math.floor(d / 365) + '年前';
  }

  // ────────────────────────── 界面 ──────────────────────────
  const css = `
    #bcf-fab{position:fixed;right:18px;bottom:18px;z-index:999999;background:#00a1d6;color:#fff;
      border:none;border-radius:22px;padding:10px 16px;font-size:13px;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.25)}
    #bcf-panel{position:fixed;inset:0;z-index:999999;background:#f6f7f8;display:none;overflow:auto}
    #bcf-panel.on{display:block}
    #bcf-head{position:sticky;top:0;background:#fff;border-bottom:1px solid #e5e7eb;padding:10px 16px;
      display:flex;align-items:center;gap:12px;flex-wrap:wrap;z-index:2}
    #bcf-head b{font-size:15px}
    .bcf-tab{padding:6px 14px;border-radius:16px;background:#eef1f4;cursor:pointer;font-size:13px;border:none}
    .bcf-tab.on{background:#00a1d6;color:#fff}
    .bcf-close{margin-left:auto;border:none;background:#eef1f4;border-radius:16px;padding:6px 14px;cursor:pointer;font-size:13px}
    #bcf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px;padding:16px}
    .bcf-card{background:#fff;border-radius:8px;overflow:hidden;text-decoration:none;color:inherit;display:block;
      box-shadow:0 1px 3px rgba(0,0,0,.08);transition:transform .1s}
    .bcf-card:hover{transform:translateY(-2px)}
    .bcf-cover{position:relative;aspect-ratio:16/9;background:#eee}
    .bcf-cover img{width:100%;height:100%;object-fit:cover;display:block}
    .bcf-dur{position:absolute;right:6px;bottom:6px;background:rgba(0,0,0,.7);color:#fff;font-size:11px;padding:1px 5px;border-radius:3px}
    .bcf-meta{padding:8px 10px 10px}
    .bcf-title{font-size:13px;line-height:1.4;max-height:2.8em;overflow:hidden;margin-bottom:6px;color:#18191c}
    .bcf-sub{font-size:12px;color:#9499a0;display:flex;justify-content:space-between;gap:8px}
    .bcf-empty{padding:40px;text-align:center;color:#9499a0;font-size:14px}
    .bcf-src{font-size:11px;color:#c9ccd0}
  `;

  function el(tag, attrs, kids) {
    const e = document.createElement(tag);
    if (attrs) for (const [k, v] of Object.entries(attrs)) {
      if (k === 'text') e.textContent = v; else e.setAttribute(k, v);
    }
    if (kids) for (const k of kids) e.appendChild(k);
    return e;
  }

  function buildUI() {
    const style = document.createElement('style'); style.textContent = css; document.head.appendChild(style);

    const fab = el('button', { id: 'bcf-fab', text: '自定义流' });
    const panel = el('div', { id: 'bcf-panel' });
    const head = el('div', { id: 'bcf-head' });
    const title = el('b', { text: '自定义流' });
    head.appendChild(title);
    const tabs = {};
    FEEDS.forEach((f, i) => {
      const t = el('button', { class: 'bcf-tab', text: f.name });
      t.onclick = () => showFeed(i);
      tabs[i] = t;
      head.appendChild(t);
    });
    const close = el('button', { class: 'bcf-close', text: '关闭' });
    close.onclick = () => panel.classList.remove('on');
    head.appendChild(close);
    // 「换一批」：丢掉全部缓存（种子 + 相关推荐），下次拉取全部重抓 ⇒ 换一批种子。
    const reroll = el('button', { class: 'bcf-close', text: '换一批' });
    reroll.title = '丢掉缓存，重抓种子和推荐（要等十几秒）';
    reroll.onclick = () => { dropSeedsCache(); relClear(); showFeed(cur < 0 ? 0 : cur); };
    head.appendChild(reroll);
    const grid = el('div', { id: 'bcf-grid' });
    panel.appendChild(head); panel.appendChild(grid);
    document.body.appendChild(fab); document.body.appendChild(panel);
    fab.onclick = () => { panel.classList.toggle('on'); if (panel.classList.contains('on') && !grid.dataset.built) showFeed(0); };

    let cur = -1;
    let renderToken = 0;                              // 每开一条流 +1；异步回来对不上就丢弃
    async function showFeed(i) {
      cur = i;
      const myToken = ++renderToken;
      Object.entries(tabs).forEach(([k, t]) => t.classList.toggle('on', +k === i));
      const f = FEEDS[i];
      grid.dataset.built = '1';
      grid.innerHTML = '';
      grid.appendChild(el('div', { class: 'bcf-empty', text: `正在拉取「${f.name}」……` }));
      // 「出圈」要靠观看历史算出的口味画像。若用户第一个点的是它，种子还没抓过，
      // 画像会是空的 ⇒ 过滤形同虚设。这里先确保种子到位。
      if ((f.filters || {}).excludeMyTnames) { try { await mySeeds(); } catch {} }
      const raw = await collect(f);
      if (myToken !== renderToken) return;            // 期间用户又切了别的流，别覆盖它
      let items = applyFilters(raw, f.filters);
      items = sortItems(items, f.sort);
      items = limitPerUp(items, f.maxPerUp || 2).slice(0, f.limit || 60);
      grid.innerHTML = '';
      if (!items.length) {
        const hint = (f.sources || []).some(s => s.type === 'upRecent' && !(s.ups || []).length)
          ? '「指定UP」还没填名字——改脚本顶部 FEEDS 里那条 ups 列表。'
          : '这条流现在没有内容（可能规则太严，或都看过了）。';
        grid.appendChild(el('div', { class: 'bcf-empty', text: hint }));
        return;
      }
      markSeen(items.map(x => x.bvid));
      for (const it of items) grid.appendChild(card(it));
      if ((f.filters || {}).excludeMyTnames) {
        const tags = myTaste().tags;
        const known = Object.entries(tags).sort((a, b) => b[1] - a[1]).slice(0, 6)
          .map(([k, v]) => `${k}(${v})`).join('、');
        const note = Object.keys(tags).length
          ? '「出圈」规则：只留你平时不看的分区。你常看的是：' + known
          : '「出圈」拿不到观看历史，没做过滤——多登录看几集再试。';
        grid.appendChild(el('div', { class: 'bcf-src', text: note }));
      }
    }

    function card(it) {
      const a = el('a', { class: 'bcf-card', href: `https://www.bilibili.com/video/${it.bvid}`, target: '_blank' });
      const cover = el('div', { class: 'bcf-cover' });
      if (it.pic) cover.appendChild(el('img', { src: it.pic, loading: 'lazy' }));
      cover.appendChild(el('span', { class: 'bcf-dur', text: fmtDur(it.dur) }));
      const meta = el('div', { class: 'bcf-meta' });
      meta.appendChild(el('div', { class: 'bcf-title', text: it.title }));
      const sub = el('div', { class: 'bcf-sub' });
      sub.appendChild(el('span', { text: it.up || '' }));
      sub.appendChild(el('span', { text: `${fmtView(it.view)} · ${ago(it.pubdate)}` }));
      meta.appendChild(sub);
      meta.appendChild(el('div', { class: 'bcf-src', text: it._src || '' }));
      a.appendChild(cover); a.appendChild(meta);
      return a;
    }
  }

  function boot() {
    if (!document.body) { setTimeout(boot, 200); return; }
    buildUI();
    console.log('[bcf] Bili 自定义流已加载。改配方见脚本顶部 FEEDS。feeds:', FEEDS.map(f => f.name).join(' / '));
  }
  boot();
})();
