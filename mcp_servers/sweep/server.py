"""sweep MCP：Polymarket 市场初筛，不评分，返回原始候选供 AI 评分（端口 8104）。"""

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
BASE_URL = "https://gamma-api.polymarket.com/markets/keyset"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; aipolymarket-sweep/1.0)",
    "Accept": "application/json",
    "Accept-Encoding": "gzip",
}

# ── 排除关键词（与 pm_sweep.py 保持一致）──────────────
CRYPTO_KW = [
    "bitcoin", "btc", "ethereum", "crypto", "solana", " sol ",
    "xrp", "dogecoin", "doge", "bnb", "blockchain", "defi", "nft",
    "web3", "altcoin", "memecoin", "meme coin", "stablecoin",
    "polymarket token", "$trump", "$move",
]

SPORTS_KW = [
    "nba ", "nfl ", "mlb ", "nhl ", "ufc ", "mma ",
    "bundesliga", "premier league", "serie a", "la liga", "ligue 1",
    "super bowl", "world cup", "wimbledon", "grand slam", "grand prix",
    "formula 1", "formula one", "olympic games", "paralympic",
    "champions league", "europa league", "fa cup", "copa del rey",
    " innings", " wicket", " over/under ", " moneyline",
    "lakers", "celtics", "warriors", "knicks", "heat ", "bulls ",
    "real madrid", "barcelona fc", "man united", "man city",
    "liverpool fc", "arsenal fc", "chelsea fc", "juventus",
    "nhl playoff", "nba playoff", "nba finals", "world series",
    "stanley cup", "super sunday",
]

SPORTS_EXTRA = [
    "spread:", "exact score:", " vs. ", " vs ", " fc ", " fk ", " sk ", " ff ",
    "basketball", "football", "soccer", "baseball", "tennis", "hockey",
    "cricket", "rugby", "golf", "boxing", "racing", "motorsport",
    "f1", "nascar", "playoff", "finals", "match", "game on", "win on 2026-",
]

SPORTS_SLUG_PARTS = ["-spread-", "-exact-score-", "-moneyline-", "-total-", "-over-under-"]
SPORTS_SLUG_PREFIX = re.compile(r"^(nor|swe|eng|esp|ita|ger|fra|usa|mlb|nba|nfl|nhl|ufc)-")


def _fetch(params: dict) -> tuple[list, str | None]:
    """返回 (markets_list, next_cursor)。"""
    url = BASE_URL + "?" + urllib.parse.urlencode(params)
    for attempt in range(1, 5):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                encoding = r.headers.get("Content-Encoding", "")
            data = gzip.decompress(raw) if encoding.lower() == "gzip" else raw
            obj = json.loads(data.decode("utf-8"))
            if isinstance(obj, dict):
                return obj.get("markets") or [], obj.get("next_cursor")
            if isinstance(obj, list):
                return obj, None
            return [], None
        except Exception:
            wait = min(2 ** attempt, 20)
            time.sleep(wait)
    return [], None


def _parse_dt(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except Exception:
        return None


def _parse_prices(m: dict) -> Optional[list[float]]:
    raw = m.get("outcomePrices")
    if not raw:
        return None
    try:
        lst = json.loads(raw) if isinstance(raw, str) else raw
        return [float(p) for p in lst]
    except Exception:
        return None


def _is_excluded(m: dict) -> tuple[bool, str]:
    q = (m.get("question") or "").lower()
    desc = (m.get("description") or "").lower()
    slug = (m.get("slug") or "").lower()
    text = " " + q + " " + desc + " "

    for ev in m.get("events", []) or []:
        if not isinstance(ev, dict):
            continue
        for tag in ev.get("tags", []) or []:
            if not isinstance(tag, dict):
                continue
            lbl = (tag.get("label") or "").lower()
            if lbl in ("sports", "crypto", "cryptocurrency", "soccer", "basketball",
                       "football", "baseball", "tennis", "golf", "boxing", "mma", "racing"):
                return True, f"tag:{lbl}"

    for kw in CRYPTO_KW:
        if kw in text:
            return True, f"crypto:{kw}"
    for kw in SPORTS_KW:
        if kw in text:
            return True, f"sports:{kw}"
    for kw in SPORTS_EXTRA:
        if kw in text:
            return True, f"sports_extra:{kw}"
    for part in SPORTS_SLUG_PARTS:
        if part in slug:
            return True, f"sports_slug:{part}"
    if SPORTS_SLUG_PREFIX.match(slug):
        return True, f"sports_slug_prefix"

    return False, ""


def _get_category(m: dict) -> str:
    q = (m.get("question") or "").lower()
    for ev in m.get("events", []) or []:
        if not isinstance(ev, dict):
            continue
        for tag in ev.get("tags", []) or []:
            if not isinstance(tag, dict):
                continue
            lbl = (tag.get("label") or "").lower()
            if lbl in ("politics", "political"):
                return "politics"
            if lbl in ("economics", "economy", "macro"):
                return "macro"
            if lbl in ("law", "legal", "court"):
                return "legal"
            if "bank" in lbl or "fed" in lbl or "rate" in lbl:
                return "central_bank"
    kws = {"fed ": "central_bank", "federal reserve": "central_bank", "interest rate": "central_bank",
           "inflation": "macro", "gdp": "macro", "recession": "macro",
           "election": "politics", "president": "politics", "congress": "politics", "senate": "politics",
           "court": "legal", "supreme": "legal", "verdict": "legal"}
    for kw, cat in kws.items():
        if kw in q:
            return cat
    return "other"


@mcp.tool()
def scan_markets(days: int = 7, min_p: float = 0.90, max_p: float = 0.97, limit: int = 50) -> str:
    """扫描 Polymarket 高概率即将到期市场（初筛，无评分）。

    返回符合条件的原始候选列表，由 AI 自行评分排序。

    参数：
    - days: 到期窗口（默认 7 天）
    - min_p: 最低概率（默认 0.90）
    - max_p: 最高概率（默认 0.97）
    - limit: 返回最多候选数（默认 50）

    返回字段（每个候选）：
    - question: 问题描述
    - outcome: 高概率一侧的结果名
    - token_id: 用于交易的 token ID
    - slug: 市场 slug
    - prob: 当前概率（0-1）
    - roi_pct: 结算后预期 ROI（%）
    - liquidity_usd: 流动性（USDC）
    - days_left: 剩余天数
    - end_date: 到期日期
    - category: 类别（politics/macro/legal/central_bank/other）
    """
    today = date.today()
    end_max = today + timedelta(days=days)
    d_min = today.isoformat() + "T00:00:00Z"
    d_max = end_max.isoformat() + "T23:59:59Z"

    candidates = []
    seen_ids = set()
    seen_slugs = set()
    page = 0
    next_cursor = None

    while True:
        params = {
            "active": "true",
            "closed": "false",
            "end_date_min": d_min,
            "end_date_max": d_max,
            "limit": 500,
        }
        if next_cursor:
            params["next_cursor"] = next_cursor

        try:
            markets, api_cursor = _fetch(params)
        except Exception:
            break

        if not markets:
            break

        page += 1

        for m in markets:
            if not isinstance(m, dict):
                continue
            mid = m.get("id") or m.get("conditionId")
            if mid in seen_ids:
                continue
            seen_ids.add(mid)

            if m.get("closed") or not m.get("active"):
                continue

            end_dt = _parse_dt(m.get("endDate") or m.get("end_date_iso"))
            if not end_dt:
                continue

            excluded, _ = _is_excluded(m)
            if excluded:
                continue

            prices = _parse_prices(m)
            if not prices or len(prices) < 2:
                continue

            max_price = max(prices)
            if not (min_p <= max_price <= max_p):
                continue

            # 找最高概率对应的 outcome
            outcomes_raw = m.get("outcomes")
            if outcomes_raw:
                try:
                    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                except Exception:
                    outcomes = []
            else:
                outcomes = []

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

            now_utc = datetime.now(timezone.utc)
            days_left = max(0, (end_dt - now_utc).days)
            liquidity = float(m.get("liquidity") or m.get("liquidityNum") or 0)
            slug = m.get("slug") or m.get("marketSlug") or ""

            # 去重 slug
            if slug and slug in seen_slugs:
                continue
            if slug:
                seen_slugs.add(slug)

            roi_pct = round((1.0 / max_price - 1.0) * 100, 2) if max_price > 0 else 0

            candidates.append({
                "question": m.get("question") or "",
                "outcome": outcome_name,
                "token_id": token_id,
                "slug": slug,
                "prob": round(max_price, 4),
                "roi_pct": roi_pct,
                "liquidity_usd": round(liquidity, 0),
                "days_left": days_left,
                "end_date": end_dt.date().isoformat(),
                "category": _get_category(m),
            })

            if len(candidates) >= limit * 3:
                break

        if not api_cursor or len(markets) < 100:
            break
        next_cursor = api_cursor
        if page > 50:
            break

    # 按流动性降序排列，最多返回 limit 个（不评分，交给 AI 判断）
    candidates.sort(key=lambda x: x["liquidity_usd"], reverse=True)
    top = candidates[:limit]

    return json.dumps({
        "scan_date": today.isoformat(),
        "params": {"days": days, "min_p": min_p, "max_p": max_p},
        "total_found": len(candidates),
        "returned": len(top),
        "note": "以下为初筛结果，未评分。请根据市场叙事、流动性、时间紧迫度、类别清晰度等综合评分，决定买入标的。",
        "markets": top,
    }, ensure_ascii=False)


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", "8104"))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
