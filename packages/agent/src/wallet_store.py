# wallet_store.py
import json
from pathlib import Path
from typing import Optional

def _store_path() -> Path:
    return Path(__file__).resolve().parent / ".wallet_local.json"

def load_wallet() -> Optional[str]:
    p = _store_path()
    try:
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            w = data.get("wallet_id")
            if isinstance(w, str) and w.startswith("0x") and len(w) == 42:
                return w
    except Exception:
        pass
    return None

def save_wallet(wallet_id: str) -> None:
    if not (isinstance(wallet_id, str) and wallet_id.startswith("0x") and len(wallet_id) == 42):
        raise ValueError("Invalid wallet_id for save_wallet")
    p = _store_path()
    p.write_text(json.dumps({"wallet_id": wallet_id}, indent=2), encoding="utf-8")

def clear_wallet() -> None:
    p = _store_path()
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass
