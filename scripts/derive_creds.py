"""用钱包私钥派生 Polymarket CLOB 交易 API 凭据，并写回 .env。

读取 .env 中的 PRIVATE_KEY，调用 create_or_derive_api_key()（已存在则派生同一组，不存在则新建），
把 CLOB_API_KEY / CLOB_SECRET / CLOB_PASS_PHRASE 写回同一个 .env。终端只打印 api_key 的前后几位。

用法：
    python3 scripts/derive_creds.py            # 已配置三项凭据时跳过
    python3 scripts/derive_creds.py --force    # 强制重新派生并覆盖
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import set_key

from backend.poly_config import get_env_path, load_app_env

CRED_KEYS = ("CLOB_API_KEY", "CLOB_SECRET", "CLOB_PASS_PHRASE")


def main() -> int:
    force = "--force" in sys.argv[1:]
    env_path = get_env_path()
    load_app_env()

    key = (os.environ.get("PRIVATE_KEY") or "").replace("0x", "")
    if not key:
        print(f"未在 {env_path} 中找到 PRIVATE_KEY")
        return 1
    if all(os.environ.get(k) for k in CRED_KEYS) and not force:
        print(f"{env_path} 已有三项 CLOB 凭据，跳过（加 --force 重新派生）")
        return 0

    try:
        from py_clob_client_v2 import ClobClient
    except ImportError:
        print("未安装 py-clob-client-v2，请运行 pip install py-clob-client-v2")
        return 1

    host = os.environ.get("CLOB_HOST", "https://clob.polymarket.com")
    client = ClobClient(host=host, key=key, chain_id=137)
    creds = client.create_or_derive_api_key()

    env_path.touch(mode=0o600, exist_ok=True)
    set_key(str(env_path), "CLOB_API_KEY", creds.api_key, quote_mode="never")
    set_key(str(env_path), "CLOB_SECRET", creds.api_secret, quote_mode="never")
    set_key(str(env_path), "CLOB_PASS_PHRASE", creds.api_passphrase, quote_mode="never")
    os.chmod(env_path, 0o600)

    masked = f"{creds.api_key[:4]}…{creds.api_key[-4:]}"
    print(f"已写入 {env_path}：CLOB_API_KEY={masked}，CLOB_SECRET / CLOB_PASS_PHRASE 已保存")
    return 0


if __name__ == "__main__":
    sys.exit(main())
