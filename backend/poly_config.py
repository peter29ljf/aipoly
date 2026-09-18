"""配置管理：滑点、模式、路径"""

import json
import os
from dataclasses import dataclass
from pathlib import Path


def get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def get_env_path() -> Path:
    poly_trader_env = Path("/root/poly-trader/data/.env")
    if poly_trader_env.exists():
        return poly_trader_env
    return get_data_dir() / ".env"


def load_app_env():
    """加载凭据 .env（优先使用 poly-trader/data/.env）

    override=False 是刻意的：systemd 经 EnvironmentFile=/etc/aipoly/wallet.env
    注入的凭据必须赢过磁盘上的 .env。曾经这里是 override=True，意味着任何残留的
    /root/poly-trader/data/.env 会静默劫持全部凭据——改了配置却不生效，且用错钱包下单。
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(get_env_path(), override=False)
    except Exception:
        pass


# ---- Polymarket 签名类型 ----------------------------------------------------
# 决定订单怎么签、资金从哪个地址出。配错不会报"配错了"，只会以"余额/授权不足"
# 或"签名无效"的形式出现，所以这里不设默认值，必须显式配置。
SIG_EOA = 0            # 直接用 EOA 自己的地址持仓交易
SIG_EMAIL_PROXY = 1    # 邮箱/Magic Link 注册，资金在 Magic proxy wallet
SIG_GNOSIS_SAFE = 2    # 2026-05-04 之前用外部签名者创建的 Safe wallet
SIG_DEPOSIT_WALLET = 3 # POLY_1271：2026-05-04 之后创建的 Deposit Wallet

_SIG_NAMES = {
    SIG_EOA: "EOA（资金在 EOA 自身地址）",
    SIG_EMAIL_PROXY: "邮箱/Magic Link proxy wallet",
    SIG_GNOSIS_SAFE: "旧版 Gnosis Safe wallet",
    SIG_DEPOSIT_WALLET: "Deposit Wallet（EIP-1271，2026-05 后新建账号）",
}


def get_signature_type() -> int:
    """读取并校验 SIGNATURE_TYPE。未配置或非法值直接抛错，不静默兜底。

    取值取决于**钱包是什么时候部署的**，而不是登录方式：
    2026-05-04 之后新建的账号是 Deposit Wallet → 3；在那之前用外部签名者
    创建的是 Safe → 2。"用 MetaMask 登录就是 2"是过时说法。
    """
    raw = (os.environ.get("SIGNATURE_TYPE") or "").strip()
    if not raw:
        raise ValueError(
            "未配置 SIGNATURE_TYPE。2026-05 之后新建的钱包账号填 3（Deposit Wallet）；"
            "旧 Safe 填 2；邮箱/Magic Link 填 1；直接用 EOA 地址持仓填 0。"
        )
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"SIGNATURE_TYPE 必须是整数，当前值：{raw!r}") from None
    if value not in _SIG_NAMES:
        raise ValueError(
            f"SIGNATURE_TYPE={value} 不是已知值，可选：" +
            "、".join(f"{k}={v}" for k, v in _SIG_NAMES.items())
        )
    if value == SIG_DEPOSIT_WALLET:
        # 识别得出，但当前这条下单链路用不了：py-clob-client-v2 对 Deposit Wallet
        # 派生的 API key 绑在 EOA 上，下单会被 CLOB 以 signer 不匹配拒绝
        # （py-clob-client-v2 issue #70）。与其让订单在半夜静默失败，不如在这里拦住。
        # 解法是迁移到官方 polymarket-client（它按钱包类型自动选签名方式）。
        raise ValueError(
            "SIGNATURE_TYPE=3（Deposit Wallet）当前不支持：py-clob-client-v2 会把 "
            "API key 绑到 EOA，下单报 signer 不匹配（issue #70）。需迁移到 polymarket-client。"
        )
    return value


def describe_signature_type(value: int) -> str:
    return _SIG_NAMES.get(value, f"未知({value})")


def get_trade_mode() -> str:
    """'sim' 或 'live'。没有默认值——拼错一律拒绝。

    这个闸门属于**真正执行下单的那一层**（aipoly-core，唯一持有私钥的组件）。
    早先它判在 MCP 进程里，而 MCP 根本读不到私钥、也不再自己下单；闸门留在那里
    等于谁都没在把关。同一个开关只能有一处真源，否则两边不一致时没人知道哪个算数。
    """
    raw = (os.environ.get("AIPM_TRADE_MODE") or "").strip().lower()
    if raw not in ("sim", "live"):
        raise ValueError(
            f"AIPM_TRADE_MODE 必须是 'sim' 或 'live'，当前 {raw!r}。"
            "它在 /etc/aipoly/mcp.env 里配置。"
        )
    return raw


def is_live_trading() -> bool:
    return get_trade_mode() == "live"


def get_private_key() -> str:
    """签名私钥，去掉 0x 前缀。这是唯一的签名者，不一定是持仓地址。"""
    raw = (os.environ.get("PRIVATE_KEY") or "").strip()
    if not raw:
        raise ValueError("未配置 PRIVATE_KEY")
    key = raw[2:] if raw.lower().startswith("0x") else raw
    if len(key) != 64 or any(c not in "0123456789abcdefABCDEF" for c in key):
        raise ValueError("PRIVATE_KEY 格式不对：应为 64 位十六进制（0x 前缀可选）")
    return key


def get_funder_address() -> str:
    """持仓/出资地址（CLOB 的 funder）。

    signature_type=1/2/3 时它**不是**私钥对应的 EOA，而是 Polymarket 的账号钱包地址
    （网页端 profile 菜单里那个）。填成 EOA 不会明确报错，只会以
    "not enough balance / allowance" 或 "the order owner has to be the owner of
    the API KEY" 的形式失败。
    """
    wallet = (os.environ.get("WALLET_ADDRESS") or "").strip()
    if not wallet:
        raise ValueError("未配置 WALLET_ADDRESS")
    if not wallet.startswith("0x") or len(wallet) != 42:
        raise ValueError(f"WALLET_ADDRESS 格式不对：应为 0x 开头的 42 位地址，当前：{wallet!r}")
    return wallet


def get_config_path() -> Path:
    return get_data_dir() / "config.json"


def get_trades_path() -> Path:
    return get_data_dir() / "trades.json"


@dataclass
class Config:
    slippage_pct: float = 5.0
    slippage_mode: str = "partial"  # "partial" | "cancel"
    web_host: str = "0.0.0.0"
    web_port: int = 8000
    mcp_port: int = 8001
    clob_host: str = "https://clob.polymarket.com"
    chain_id: int = 137

    @classmethod
    def from_file(cls) -> "Config":
        path = get_config_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    slippage_pct=float(data.get("slippage_pct", 5.0)),
                    slippage_mode=str(data.get("slippage_mode", "partial")),
                    web_host=str(data.get("web_host", "0.0.0.0")),
                    web_port=int(data.get("web_port", 8000)),
                    mcp_port=int(data.get("mcp_port", 8001)),
                    clob_host=str(data.get("clob_host", "https://clob.polymarket.com")),
                    chain_id=int(data.get("chain_id", 137)),
                )
            except (json.JSONDecodeError, TypeError):
                pass
        return cls()

    def to_file(self):
        path = get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "slippage_pct": self.slippage_pct,
                    "slippage_mode": self.slippage_mode,
                    "web_host": self.web_host,
                    "web_port": self.web_port,
                    "mcp_port": self.mcp_port,
                    "clob_host": self.clob_host,
                    "chain_id": self.chain_id,
                },
                f,
                indent=2,
            )

    def slippage_ratio(self) -> float:
        return self.slippage_pct / 100.0
