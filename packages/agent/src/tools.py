"""LangChain tools for wallet operations."""
import requests, uuid, re, json
from typing import Optional, Callable
from langchain.tools import Tool

# -----------------------------
# Common sanitizers & validators
# -----------------------------
def _clean_value(v):
    if isinstance(v, str):
        return v.strip()
    return v

def _clean_dict(d: dict | None) -> dict | None:
    if d is None:
        return None
    return {k: _clean_value(v) for k, v in d.items()}

ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
def _is_evm_address(s: str) -> bool:
    return isinstance(s, str) and bool(ADDR_RE.match(s.strip()))

def _detect_create_intent(text: str) -> bool:
    t = (text or "").lower()
    patterns = [
        r"\bcreate\b.*\b(wallet|account|address)\b",
        r"\bopen\b.*\b(wallet|account)\b",
        r"\bmake\b.*\b(wallet|account|address)\b",
        r"\bspin\s*up\b.*\b(wallet|account)\b",
        r"\bset\s*up\b.*\b(wallet|account)\b",
        r"\bgenerate\b.*\b(wallet|account|address)\b",
        r"\bnew\b.*\b(wallet|account|address)\b",
        r"\bbuild\b.*\b(wallet|account)\b",
    ]
    import re as _re
    return any(_re.search(p, t) for p in patterns)

class WalletTools:
    """Wallet operation tools that call the backend API."""

    def __init__(
        self,
        api_base: str = "http://localhost:8000",
        get_current_user_input=None,
        on_wallet_created: Optional[Callable[[str], None]] = None,  # <-- NEW
    ):
        self.api_base = api_base
        self.get_current_user_input = get_current_user_input or (lambda: "")
        self.on_wallet_created = on_wallet_created

    # ---- HTTP helpers ----
    def _post(self, path: str, json_body: dict = None) -> dict:
        json_body = _clean_dict(json_body)
        r = requests.post(f"{self.api_base}{path}", json=json_body)
        r.raise_for_status()
        return r.json()

    def _get(self, path: str, params: dict = None) -> dict:
        params = _clean_dict(params)
        r = requests.get(f"{self.api_base}{path}", params=params)
        r.raise_for_status()
        return r.json()

    # ---- Tools ----
    def wallet_create(self, user_id: Optional[str] = None) -> str:
        """
        Create a new wallet only if the user's CURRENT input expresses clear create intent.
        On success, immediately persists the wallet via on_wallet_created callback.
        """
        turn_text = self.get_current_user_input()
        if not _detect_create_intent(turn_text):
            return ("Creation blocked: to create a wallet, say something like "
                    "'create a new wallet', 'open a new wallet', or 'generate a wallet'.")
        try:
            result = self._post("/wallet/create", {"user_id": user_id})
            address = result["address"]
            # IMMEDIATE PERSIST so we don't rely on parsing LLM output
            if self.on_wallet_created and _is_evm_address(address):
                try:
                    self.on_wallet_created(address)
                except Exception:
                    pass
            return (f"Wallet created successfully:\n"
                    f"Wallet ID: {result['wallet_id']}\n"
                    f"Address: {address}\n"
                    f"Network: {result['network']}")
        except Exception as e:
            return f"Error creating wallet: {str(e)}"

    def fund_testnet(self, args: str | dict) -> str:
        try:
            if isinstance(args, str):
                try:
                    parsed = json.loads(args)
                except json.JSONDecodeError:
                    parts = args.split()
                    parsed = {}
                    for part in parts:
                        if '=' in part:
                            k, v = part.split('=', 1)
                            parsed[k.strip()] = v.strip()
            else:
                parsed = args

            wallet_id = (parsed.get("wallet_id") or "").strip()
            token = (parsed.get("token") or "").strip().lower()
            tokens = (parsed.get("tokens") or "").strip().lower()

            if not _is_evm_address(wallet_id):
                return "Error: wallet_id must be a valid 42-char EVM address (0x + 40 hex)."

            tokens_to_fund = []
            if tokens:
                tokens_to_fund = [t.strip() for t in tokens.split(",") if t.strip()]
            elif token:
                tokens_to_fund = [token]

            if not tokens_to_fund:
                return "Error: specify token='eth' or 'usdc', or tokens='eth,usdc'."

            results, errors = [], []

            for t in tokens_to_fund:
                if t not in ("eth", "usdc"):
                    errors.append(f"Invalid token: {t}. Supported: eth, usdc")
                    continue
                try:
                    res = self._post(f"/wallet/fund_testnet?token={t}&wait=true", {"wallet_id": wallet_id})
                    results.append(f"""{t.upper()} funding completed:
  Transaction: {res['faucet_tx']}
  Status: {'Success' if res['success'] else 'Failed'}
  Message: {res.get('message', 'Funds received')}""")
                except Exception as e:
                    errors.append(f"Error requesting {t.upper()} funds: {str(e)}")

            msg = "Testnet funding results:\n\n"
            if results:
                msg += "\n".join(results)
            if errors:
                msg += "\n\nErrors:\n" + "\n".join(errors)
            if results and not errors:
                msg += "\n\n✅ All funding requests completed successfully!"
            elif results and errors:
                msg += "\n\n⚠️  Some funding requests succeeded, some failed."
            return msg
        except Exception as e:
            return f"Error requesting funds: {str(e)}"

    def auth_grant(self, args: str | dict) -> str:
        try:
            if isinstance(args, str):
                parsed = json.loads(args)
            else:
                parsed = args

            wallet_id = (parsed.get("wallet_id") or "").strip()
            if not _is_evm_address(wallet_id):
                return "Error: wallet_id must be a valid 42-char EVM address."

            per_tx_max = parsed["per_tx_max"]
            daily_cap = parsed["daily_cap"]

            self._post("/auth/grant", {
                "wallet_id": wallet_id,
                "per_tx_max": per_tx_max,
                "daily_cap": daily_cap
            })
            return (f"Authority granted for wallet {wallet_id}:\n"
                    f"Per-transaction max: {per_tx_max} USDC\n"
                    f"Daily cap: {daily_cap} USDC")
        except Exception as e:
            return f"Error granting authority: {str(e)}"

    def auth_revoke(self, wallet_id: str) -> str:
        wallet_id = (wallet_id or "").strip()
        if not _is_evm_address(wallet_id):
            return "Error: wallet_id must be a valid 42-char EVM address."
        try:
            self._post("/auth/revoke", {"wallet_id": wallet_id})
            return f"Authority revoked for wallet {wallet_id}"
        except Exception as e:
            return f"Error revoking authority: {str(e)}"

    def get_policy(self, wallet_id: str) -> str:
        wallet_id = (wallet_id or "").strip()
        if not _is_evm_address(wallet_id):
            return "Error: wallet_id must be a valid 42-char EVM address."
        try:
            result = self._get("/auth/policy", {"wallet_id": wallet_id})
            enabled = "ENABLED" if result['enabled'] else "DISABLED"
            remaining = (result['daily_cap'] - result['spent_today']) if result['daily_cap'] is not None else 'N/A'
            return f"""Policy status for wallet {wallet_id}:
Status: {enabled}
Per-transaction max: {result['per_tx_max']} USDC
Daily cap: {result['daily_cap']} USDC
Spent today: {result['spent_today']} USDC
Remaining today: {remaining} USDC"""
        except Exception as e:
            return f"Error getting policy: {str(e)}"

    def transfer(self, args: str | dict) -> str:
        try:
            if isinstance(args, str):
                parsed = json.loads(args)
            else:
                parsed = args

            wallet_id = (parsed.get("wallet_id") or "").strip()
            to = (parsed.get("to") or "").strip()
            amount = float(parsed.get("amount", 0))
            idem = parsed.get("idempotency_key") or str(uuid.uuid4())

            if not _is_evm_address(wallet_id):
                return "Error: invalid source wallet_id (must be 0x + 40 hex)."
            if not _is_evm_address(to):
                return f"Error: invalid recipient address '{to}'. Must be 42 chars (0x + 40 hex)."
            if not (amount > 0):
                return "Error: amount must be positive."

            # quick UX check for balances
            try:
                bal = self._get("/wallet/address", {"wallet_id": wallet_id})
                assets = bal.get("assets") or []
                eth, usdc = 0.0, 0.0
                for a in assets:
                    if not a: continue
                    sym = str(a.get("symbol", "")).upper()
                    try:
                        val = float(a.get("balance", "0") or 0)
                    except Exception:
                        val = 0.0
                    if sym == "ETH": eth = val
                    if sym == "USDC": usdc = val
                if usdc < amount:
                    return (f"❌ Insufficient USDC. Requested {amount}, have {usdc}.\n"
                            f"Use: fund_testnet token='usdc'.")
                if eth < 0.00005:
                    return (f"❌ Low ETH for gas (have {eth}).\n"
                            f"Use: fund_testnet token='eth'.")
            except Exception:
                pass

            result = self._post("/transfer", {
                "wallet_id": wallet_id,
                "to": to,
                "amount": amount,
                "asset": "USDC",
                "idempotencyKey": idem
            })

            return (f"Transfer successful:\n"
                    f"Amount: {result['amount']} {result['asset']}\n"
                    f"To: {result['to']}\n"
                    f"Transaction: {result['txHash']}\n"
                    f"Status: {result['status']}\n"
                    f"Explorer: {result['explorer']}\n\n"
                    f"View your transaction on BaseScan: {result['explorer']}")
        except requests.HTTPError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = str(e)
            if "insufficient balance" in detail.lower():
                return ("❌ Transfer Failed: Insufficient ETH for Gas\n\n"
                        "💡 fund_testnet token='eth' to top up gas.")
            if "exceeds balance" in detail.lower():
                return ("❌ Transfer Failed: USDC amount exceeds balance.\n\n"
                        "💡 fund_testnet token='usdc' to get more USDC.")
            return f"Transfer failed: {detail}"
        except Exception as e:
            return f"Error executing transfer: {str(e)}"

    def get_balance(self, wallet_id: str) -> str:
        wallet_id = (wallet_id or "").strip()
        if not _is_evm_address(wallet_id):
            return "Error: wallet_id must be a valid 42-char EVM address."
        try:
            result = self._get("/wallet/address", {"wallet_id": wallet_id})
            assets = result.get('assets')
            if not assets:
                return (f"Wallet {wallet_id}:\n"
                        f"Address: {result.get('address', wallet_id)}\n"
                        f"Network: {result.get('network', 'base-sepolia')}\n"
                        f"Balance: No assets found (wallet is empty)\n\n"
                        f"💡 Tip: fund_testnet token='eth' (gas), token='usdc' (transfers)")
            eth_balance = 0.0
            usdc_balance = 0.0
            for a in assets:
                if not a: continue
                sym = str(a.get("symbol", "")).upper()
                try:
                    val = float(a.get("balance", "0") or 0)
                except Exception:
                    val = 0.0
                if sym == "ETH": eth_balance = val
                if sym == "USDC": usdc_balance = val

            resp = (f"Wallet Balance for {wallet_id}:\n"
                    f"Address: {result.get('address', wallet_id)}\n"
                    f"Network: {result.get('network', 'base-sepolia')}\n\n"
                    f"💰 ETH (for gas):  {eth_balance} ETH\n"
                    f"💵 USDC (to send): {usdc_balance} USDC\n")
            if eth_balance < 0.0001:
                resp += "\n⚠️  Low ETH! Use: fund_testnet token='eth'"
            if usdc_balance < 0.01:
                resp += "\n💡 Low USDC. Use: fund_testnet token='usdc'"
            return resp
        except Exception as e:
            import traceback
            return f"Error getting balance: {str(e)}\nDetails: {traceback.format_exc()}"

    # ---- Tool bindings ----
    def _parse_fund_args(self, args: str) -> str:
        return self.fund_testnet(args)

    def _parse_grant_args(self, args: str) -> str:
        return self.auth_grant(args)

    def _parse_transfer_args(self, args: str) -> str:
        return self.transfer(args)

    def get_tools(self) -> list:
        return [
            Tool(
                name="wallet_create",
                func=lambda x: self.wallet_create(),
                description=("Create a new wallet on Base Sepolia testnet. "
                             "Only runs if the user's message clearly asks to create/open/generate/make/set up a wallet.")
            ),
            Tool(
                name="get_balance",
                func=self.get_balance,
                description='Check wallet balance (ETH & USDC). Input: wallet_id (string).'
            ),
            Tool(
                name="fund_testnet",
                func=self._parse_fund_args,
                description=('Request testnet funds. Input JSON: '
                             '{"wallet_id":"0x...","token":"eth"} or {"wallet_id":"0x...","tokens":"eth,usdc"} '
                             '(waits for funds).')
            ),
            Tool(
                name="auth_grant",
                func=self._parse_grant_args,
                description='Grant spending authority. Input JSON: {"wallet_id":"0x...","per_tx_max":5.0,"daily_cap":20.0}'
            ),
            Tool(
                name="auth_revoke",
                func=self.auth_revoke,
                description="Revoke spending authority. Input: wallet_id (string)."
            ),
            Tool(
                name="get_policy",
                func=self.get_policy,
                description="Get policy status. Input: wallet_id (string)."
            ),
            Tool(
                name="transfer",
                func=self._parse_transfer_args,
                description='Transfer USDC. Input JSON: {"wallet_id":"0x...","to":"0x...","amount":0.5}.'
            ),
        ]
