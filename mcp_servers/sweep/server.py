"""sweep MCP：Polymarket 全市场初筛，基于 /events API + offset 分页，不评分，返回原始候选供 AI 评分（端口 8104）。

策略：
- /events API 支持 active/date/offset 过滤，90天内有 600+ events / 7000+ markets
- 每个 event 含多个 binary markets（候选/选项），可以精准按类别排除
- 不扫今日到期体育盘（offset 限制 10000，全是体育）
- 扫描 categories 适合扫尾策略的主题（选举/地缘政治/法律/经济/科技）
"""

import gzip
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Optional

sys.path.insert(0, "/root/aipolymarket")

from fastmcp import FastMCP

mcp = FastMCP("sweep")

# ── API ──────────────────────────────────────────────
EVENTS_URL = "https://gamma-api.polymarket.com/events"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; aipolymarket-sweep/1.0)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}

# ── 排除：体育 ──────────────────────────────────────
SPORTS_TITLE_KW = [
    # 球类联赛
    "nba", "nfl", "mlb", "nhl", "nba playoff", "nba finals",
    "champions league", "europa league", "fa cup", "ligue 1",
    "bundesliga", "serie a", "la liga", "premier league",
    "copa del rey", "world cup", "super bowl", "stanley cup",
    "world series", "formula 1", "formula one", "grand prix",
    "ufc", "mma", "wimbledon", "grand slam",
    # 球队/联赛名词
    "lakers", "celtics", "warriors", "knicks",
    "manchester", "real madrid", "barcelona", "juventus",
    "chelsea", "arsenal", "liverpool", "psg",
    # 体育动作词
    " spread", "over/under", "o/u ", "exact score",
    "moneyline", "handicap", " vs. ",
    "top scorer", "golden boot",
    # 网球/高尔夫/赛车
    "french open", "wimbledon", "us open tennis",
    "masters golf", "pga tour", "nascar",
    # 体育运动词
    "basketball", "football matchup", "soccer match",
    "baseball", "cricket", "rugby", "cycling race",
]

# ── 排除：加密货币 ──────────────────────────────────
CRYPTO_TITLE_KW = [
    "bitcoin", "btc", "ethereum", "eth ", "solana", "crypto",
    "dogecoin", "doge", "bnb", "blockchain", "defi", "nft",
    "altcoin", "memecoin", "stablecoin", "$trump", "$move",
    "binance", "coinbase", "chainlink", "polygon", "avalanche",
    "cardano", "shiba", "pepe", "web3",
    "will btc", "will eth", "will sol", "will xrp",
]

# ── 包含：适合扫尾策略的主题 ──────────────────────────
# 这些关键词出现在 event title 里，说明是合适的预测市场
GOOD_TOPIC_KW = [
    # 选举类（高流动性，明确二元结果）
    "election", "primary", "senate", "congress", "governor",
    "mayoral", "presidential", "nominee", "candidat",
    "democrat", "republican", "ballot",
    # 地缘政治（清晰结果，高关注度）
    "ceasefire", "peace deal", "war", "conflict", "invasion",
    "sanctions", "treaty", "diplomatic", "nato", "ukraine",
    "russia", "israel", "iran", "china", "taiwan",
    # 法律/监管
    "court", "verdict", "ruling", "impeach", "indict",
    "sentence", "conviction", "supreme court", "legislation",
    "bill pass", "signed into law",
    # 经济/央行
    "federal reserve", "fed rate", "interest rate", "inflation",
    "gdp", "recession", "unemployment", "tariff", "trade deal",
    # 科技/娱乐事件（有明确结果）
    "released before", "launch", "ipo", "merger", "acquisition",
    "bankruptcy", "resign", "fired", "appointed",
    # 健康/科学
    "vaccine", "drug approved", "fda", "pandemic", "outbreak",
]


def _fetch_events_page(params: dict) -> tuple[list, int]:
    """获取 events 一页，返回 (events_list, total_markets_count)。失败返回 ([], 0)。"""
    url = EVENTS_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, 3):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
                enc = r.headers.get("Content-Encoding", "")
            data = gzip.decompress(raw) if enc.lower() == "gzip" else raw
            obj = json.loads(data.decode("utf-8"))
            events = obj if isinstance(obj, list) else obj.get("events", [])
            mkt_cnt = sum(len(e.get("markets", [])) for e in events)
            return events, mkt_cnt
        except Exception:
            if attempt < 2:
                time.sleep(2)
    return [], 0


def _event_is_excluded(title: str, tags: list) -> tuple[bool, str]:
    """根据 event 标题和 tags 判断是否排除。"""
    t = " " + title.lower() + " "

    # 先查 tag 标签
    for tag in tags or []:
        lbl = (tag.get("label") or "").lower()
        if lbl in ("sports", "crypto", "cryptocurrency", "soccer", "football",
                   "basketball", "baseball", "tennis", "golf", "boxing",
                   "mma", "racing", "rugby", "cricket", "hockey", "esports"):
            return True, f"tag:{lbl}"

    # 体育关键词
    for kw in SPORTS_TITLE_KW:
        if kw in t:
            return True, f"sports:{kw}"

    # 加密关键词
    for kw in CRYPTO_TITLE_KW:
        if kw in t:
            return True, f"crypto:{kw}"

    return False, ""


def _get_category(title: str, tags: list) -> str:
    """从 event title 推断类别。"""
    t = title.lower()
    tag_labels = {(tag.get("label") or "").lower() for tag in (tags or [])}

    if any(kw in t for kw in ["election", "primary", "senate", "congress", "governor",
                               "mayoral", "presidential", "nominee", "candidat",
                               "democrat", "republican", "ballot"]):
        return "politics"
    if any(kw in t for kw in ["ceasefire", "peace", "war", "invasion", "nato",
                               "ukraine", "russia", "israel", "iran", "china",
                               "taiwan", "diplomacy", "sanction", "conflict"]):
        return "geopolitics"
    if any(kw in t for kw in ["federal reserve", "fed rate", "interest rate",
                               "inflation", "gdp", "recession", "unemployment",
                               "tariff", "trade deal", "fiscal", "monetary"]):
        return "macro"
    if any(kw in t for kw in ["court", "verdict", "ruling", "impeach", "indict",
                               "sentence", "conviction", "supreme", "legislation",
                               "bill pass", "law"]):
        return "legal"
    if any(kw in t for kw in ["release", "launch", "ipo", "merger", "acquisition",
                               "bankruptcy", "resign", "fired", "appointed", "ai ",
                               "artificial intelligence", "technology"]):
        return "tech"
    if any(kw in t for kw in ["vaccine", "drug", "fda", "pandemic", "health",
                               "medical", "disease", "outbreak", "treatment"]):
        return "health"
    return "other"


def _parse_prices(m: dict) -> Optional[list[float]]:
    raw = m.get("outcomePrices")
    if not raw:
        return None
    try:
        lst = json.loads(raw) if isinstance(raw, str) else raw
        return [float(p) for p in lst]
    except Exception:
        return None


@mcp.tool()
def scan_markets(
    days: int = 30,
    min_p: float = 0.90,
    max_p: float = 0.97,
    limit: int = 50,
    categories: str = "all",
) -> str:
    """扫描 Polymarket 全量预测市场（非体育/非加密），基于 /events API 分页。

    策略说明：
    - 适合"扫尾策略"：买入高概率（接近结算）的市场，赚取最后几个百分点的 ROI
    - 默认扫 30 天窗口（7天内候选较少，30天内有更多选举/地缘政治事件）
    - 自动排除体育博彩和加密货币价格预测
    - 返回的候选按流动性降序排列，供 AI 综合评分决定买入

    参数：
    - days: 到期窗口（默认 30 天，7天候选少，推荐 14-60 天）
    - min_p: 最低概率（默认 0.90）
    - max_p: 最高概率（默认 0.97）
    - limit: 返回最多候选数（默认 50）
    - categories: 过滤类别，逗号分隔，可选 politics/geopolitics/macro/legal/tech/health/other，
                  或 "all" 返回全部（默认 all）

    返回字段（每个候选）：
    - question: 市场问题
    - outcome: 高概率方向（Yes/No/候选人名）
    - token_id: 交易用 token ID
    - slug: 市场 slug
    - event_title: 所属事件标题
    - prob: 当前概率（0-1）
    - roi_pct: 预期 ROI（%）
    - liquidity_usd: 流动性
    - days_left: 剩余天数
    - end_date: 到期日期
    - category: politics/geopolitics/macro/legal/tech/health/other
    """
    today = date.today()
    now_utc = datetime.now(timezone.utc)
    d_min = today.isoformat() + "T00:00:00Z"
    d_max = (today + timedelta(days=days)).isoformat() + "T23:59:59Z"

    # 解析 category 过滤
    cat_filter: Optional[set] = None
    if categories and categories.lower() != "all":
        cat_filter = {c.strip().lower() for c in categories.split(",")}

    candidates: list[dict] = []
    seen_market_ids: set = set()
    events_scanned = 0
    events_excluded = 0

    # 分页扫描 /events
    for offset in range(0, 10000, 100):
        params = {
            "active": "true",
            "closed": "false",
            "limit": 100,
            "offset": offset,
            "end_date_min": d_min,
            "end_date_max": d_max,
        }
        events, _ = _fetch_events_page(params)
        if not events:
            break

        events_scanned += len(events)

        for event in events:
            etitle = event.get("title") or event.get("slug") or ""
            etags = event.get("tags") or []

            # 排除体育/加密
            excluded, reason = _event_is_excluded(etitle, etags)
            if excluded:
                events_excluded += 1
                continue

            category = _get_category(etitle, etags)

            # category 过滤
            if cat_filter and category not in cat_filter:
                continue

            # 展开 event 内的所有 markets
            for m in event.get("markets") or []:
                if not isinstance(m, dict):
                    continue

                mid = m.get("id") or m.get("conditionId")
                if mid and mid in seen_market_ids:
                    continue
                if mid:
                    seen_market_ids.add(mid)

                # 跳过非 active
                if m.get("closed") or not m.get("active", True):
                    continue

                # 概率过滤
                prices = _parse_prices(m)
                if not prices or len(prices) < 2:
                    continue
                max_price = max(prices)
                if not (min_p <= max_price <= max_p):
                    continue

                # outcome 名称
                outcomes_raw = m.get("outcomes")
                outcomes: list = []
                if outcomes_raw:
                    try:
                        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                    except Exception:
                        pass
                max_idx = prices.index(max_price)
                outcome_name = outcomes[max_idx] if max_idx < len(outcomes) else "Yes"

                # token_id
                ct_ids = m.get("clob_token_ids") or m.get("clobTokenIds") or []
                if isinstance(ct_ids, str):
                    try:
                        ct_ids = json.loads(ct_ids)
                    except Exception:
                        ct_ids = []
                token_id = ct_ids[max_idx] if max_idx < len(ct_ids) else ""

                # end date & days_left
                end_str = ""
                days_left = 0
                raw_end = m.get("endDate") or event.get("endDate") or ""
                if raw_end:
                    end_str = raw_end[:10]
                    try:
                        end_dt = datetime.fromisoformat(raw_end.replace("Z", "+00:00"))
                        if end_dt.tzinfo is None:
                            end_dt = end_dt.replace(tzinfo=timezone.utc)
                        days_left = max(0, (end_dt - now_utc).days)
                    except Exception:
                        pass

                liquidity = float(m.get("liquidity") or m.get("liquidityNum") or 0)
                roi_pct = round((1.0 / max_price - 1.0) * 100, 2) if max_price > 0 else 0
                slug = m.get("slug") or m.get("marketSlug") or ""

                candidates.append({
                    "question": m.get("question") or "",
                    "outcome": outcome_name,
                    "token_id": token_id,
                    "slug": slug,
                    "event_title": etitle,
                    "prob": round(max_price, 4),
                    "roi_pct": roi_pct,
                    "liquidity_usd": round(liquidity, 0),
                    "days_left": days_left,
                    "end_date": end_str,
                    "category": category,
                })

        if len(candidates) >= limit * 10:
            break

    # 按流动性降序，最多返回 limit 个
    candidates.sort(key=lambda x: x["liquidity_usd"], reverse=True)
    top = candidates[:limit]

    # 统计类别分布
    from collections import Counter
    cat_dist = dict(Counter(c["category"] for c in top))

    return json.dumps({
        "scan_date": today.isoformat(),
        "params": {"days": days, "min_p": min_p, "max_p": max_p},
        "date_window": {"from": today.isoformat(), "to": (today + timedelta(days=days)).isoformat()},
        "events_scanned": events_scanned,
        "events_excluded_sports_crypto": events_excluded,
        "total_found": len(candidates),
        "returned": len(top),
        "category_distribution": cat_dist,
        "tip": (
            "以下为初筛结果（已排除体育/加密货币），未评分。"
            "推荐关注：politics（选举）和 geopolitics（地缘政治）类别的高流动性标的。"
            "ROI 低但确定性高的选举候选项通常是扫尾策略的良好标的。"
        ),
        "markets": top,
    }, ensure_ascii=False)


@mcp.tool()
def list_event_categories(days: int = 30) -> str:
    """列出当前所有活跃事件的类别分布，帮助制定扫描策略。

    参数：
    - days: 查看未来几天内的事件（默认 30 天）
    """
    today = date.today()
    d_min = today.isoformat() + "T00:00:00Z"
    d_max = (today + timedelta(days=days)).isoformat() + "T23:59:59Z"

    from collections import defaultdict
    categories: dict = defaultdict(list)
    total_excluded = 0

    for offset in range(0, 5000, 100):
        params = {
            "active": "true",
            "closed": "false",
            "limit": 100,
            "offset": offset,
            "end_date_min": d_min,
            "end_date_max": d_max,
        }
        events, _ = _fetch_events_page(params)
        if not events:
            break
        for event in events:
            etitle = event.get("title") or ""
            etags = event.get("tags") or []
            excl, reason = _event_is_excluded(etitle, etags)
            if excl:
                total_excluded += 1
                continue
            cat = _get_category(etitle, etags)
            mkts = event.get("markets") or []
            categories[cat].append({
                "title": etitle,
                "markets": len(mkts),
                "end_date": (event.get("endDate") or "")[:10],
            })

    result = {}
    for cat, evs in sorted(categories.items()):
        result[cat] = {
            "event_count": len(evs),
            "total_markets": sum(e["markets"] for e in evs),
            "sample_events": [e["title"] for e in evs[:5]],
        }

    return json.dumps({
        "days_window": days,
        "excluded_sports_crypto_events": total_excluded,
        "categories": result,
        "recommendation": (
            "扫尾策略最佳主题：\n"
            "1. politics — 选举初选/决选，结果明确，流动性高\n"
            "2. geopolitics — 停火/领土控制/外交，高关注度\n"
            "3. legal — 法院裁决，明确二元结果\n"
            "4. macro — 美联储利率决定，结果明确\n"
            "5. tech — 产品发布/上市，有截止日期"
        ),
    }, ensure_ascii=False)


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8104"))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
