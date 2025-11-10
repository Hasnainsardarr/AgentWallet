"""Agent tools that directly call services."""
import logging
import re
import json
from typing import Optional
from langchain.tools import StructuredTool, Tool
from pydantic import BaseModel, Field, model_validator

logger = logging.getLogger(__name__)

ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")


def _first_address(s: str) -> Optional[str]:
    if not isinstance(s, str):
        return None
    m = ADDR_RE.search(s.strip())
    return m.group(0) if m else None


_KV_PAIR_RE = re.compile(r"\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*([^,;]+)")


def _parse_kv_string(s: str) -> dict:
    """Parse strings like 'wallet=0xabc, per_tx_max=10, daily_cap=100' or JSON strings."""
    data: dict = {}
    if not isinstance(s, str):
        return data
    
    # Try JSON parsing first if it looks like JSON
    s_stripped = s.strip()
    if s_stripped.startswith("{") and s_stripped.endswith("}"):
        try:
            parsed = json.loads(s_stripped)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass  # Fall through to key=value parsing
    
    # Try key=value parsing
    for key, val in _KV_PAIR_RE.findall(s):
        v = val.strip().strip("'\"")
        data[key.strip()] = v
    
    # Heuristics: if no wallet key, try to extract address
    if "wallet" not in data:
        addr = _first_address(s)
        if addr:
            data["wallet"] = addr
    return data


class CreateWalletInput(BaseModel):
    """No input required for wallet creation."""
    pass


class GetBalanceInput(BaseModel):
    wallet: str = Field(default="", description="Wallet address (optional, uses active wallet if empty)")

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, v):
        if isinstance(v, str):
            # Allow just an address or wallet=0x...
            d = _parse_kv_string(v)
            if not d and _first_address(v):
                d = {"wallet": _first_address(v)}
            return d
        if isinstance(v, dict) and "wallet" in v and isinstance(v["wallet"], str):
            s = v["wallet"]
            if ("," in s) or ("=" in s) or ("0x" in s and len(s) > 42):
                d = _parse_kv_string(s)
                d.update({k: val for k, val in v.items() if k != "wallet"})
                return d
        return v


class FundTestnetInput(BaseModel):
    token: str = Field(default="eth", description="Token to fund: 'eth' or 'usdc' (defaults to 'eth')")
    wallet: str = Field(default="", description="Wallet address (optional)")

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, v):
        if isinstance(v, str):
            # Try JSON parsing first
            s = v.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    parsed = json.loads(s)
                    if isinstance(parsed, dict):
                        # Extracted token from JSON
                        return {
                            "token": parsed.get("token", "eth"),
                            "wallet": parsed.get("wallet", parsed.get("wallet_id", ""))
                        }
                except (json.JSONDecodeError, ValueError):
                    pass
            
            # Try key=value parsing
            d = _parse_kv_string(s)
            if d:
                return {
                    "token": d.get("token", "eth"),
                    "wallet": d.get("wallet", d.get("wallet_id", ""))
                }
            
            # Simple string: treat as token value
            return {"token": s.strip().strip("'\""), "wallet": ""}
        
        if isinstance(v, dict):
            # Extract token and wallet, handling various field names
            token_val = str(v.get("token", "eth")).strip().strip("'\"")
            wallet_val = str(v.get("wallet", v.get("wallet_id", ""))).strip()
            
            # CRITICAL: If token value is actually a JSON string (LangChain bug), parse it
            if token_val.startswith("{") and token_val.endswith("}"):
                try:
                    parsed = json.loads(token_val)
                    if isinstance(parsed, dict):
                        token_val = parsed.get("token", "eth")
                        wallet_val = parsed.get("wallet", parsed.get("wallet_id", wallet_val))
                except (json.JSONDecodeError, ValueError):
                    pass
            
            return {
                "token": str(token_val).strip().strip("'\""),
                "wallet": str(wallet_val).strip()
            }
    
        return v
class GrantPolicyInput(BaseModel):
    per_tx_max: float = Field(default=10.0, description="Maximum per transaction (fallback 10.0)")
    daily_cap: float = Field(default=100.0, description="Maximum daily spending (fallback 100.0)")
    wallet: str = Field(default="", description="Wallet address (optional)")

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, v):
        # String input: key=value, or free text
        if isinstance(v, str):
            d = _parse_kv_string(v)
            if "per_tx" in d and "per_tx_max" not in d:
                d["per_tx_max"] = d.pop("per_tx")
            if "max_per_tx" in d and "per_tx_max" not in d:
                d["per_tx_max"] = d.pop("max_per_tx")
            if "daily" in d and "daily_cap" not in d:
                d["daily_cap"] = d.pop("daily")
            return d
        # Dict input with the first field receiving the whole string (LangChain behavior)
        if isinstance(v, dict) and "per_tx_max" in v and isinstance(v["per_tx_max"], str):
            s = v["per_tx_max"]
            if ("," in s) or ("=" in s) or ("0x" in s and len(s) > 42):
                d = _parse_kv_string(s)
                if "per_tx" in d and "per_tx_max" not in d:
                    d["per_tx_max"] = d.pop("per_tx")
                if "max_per_tx" in d and "per_tx_max" not in d:
                    d["per_tx_max"] = d.pop("max_per_tx")
                if "daily" in d and "daily_cap" not in d:
                    d["daily_cap"] = d.pop("daily")
                # merge with any other explicit fields
                d.update({k: val for k, val in v.items() if k != "per_tx_max"})
                return d
        return v


class CheckPolicyInput(BaseModel):
    wallet: str = Field(default="", description="Wallet address (optional)")

    @model_validator(mode="before")
    @classmethod
    def _coerce(cls, v):
        if isinstance(v, str):
            d = _parse_kv_string(v)
            if not d and _first_address(v):
                d = {"wallet": _first_address(v)}
            return d
        if isinstance(v, dict) and "wallet" in v and isinstance(v["wallet"], str):
            s = v["wallet"]
            if ("," in s) or ("=" in s) or ("0x" in s and len(s) > 42):
                d = _parse_kv_string(s)
                d.update({k: val for k, val in v.items() if k != "wallet"})
                return d
        return v


class TransferInput(BaseModel):
    """Transfer input that handles all LangChain edge cases."""
    to: str = Field(description="The recipient wallet address (0x-prefixed)")
    amount: float | str = Field(description="The amount of USDC to transfer")
    wallet: str = Field(default="", description="The source wallet (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "to": "0x742d35Cc6634C0532925a3b8D454342b3aB0a9b2",
                "amount": 0.05,
                "wallet": ""
            }
        }


class AgentTools:
    """Tools for the agent to interact with backend services."""
    
    def __init__(self, cdp_service, db_service, session_id: str, current_wallet: Optional[str] = None):
        self.cdp = cdp_service
        self.db = db_service
        self.session_id = session_id
        self.current_wallet = current_wallet
    
    async def create_wallet_raw(self, input_str: str = "") -> str:
        """Raw create_wallet function - no input needed."""
        try:
            result = await self.cdp.create_wallet()
            wallet_id = result["address"]
            
            await self.db.create_or_update_wallet(
                session_id=self.session_id,
                wallet_id=wallet_id,
                address=result["address"],
                network=result["network"]
            )
            
            self.current_wallet = wallet_id
            logger.info(f"✅ Wallet created and saved: {wallet_id} for session {self.session_id}")
            
            return f"""✅ Great! I've created a new wallet for you.

Your wallet address: {result['address']}
Network: {result['network']}

This wallet is now ready to use. Would you like me to request some testnet tokens so you can get started?"""
        except Exception as e:
            logger.error(f"Wallet creation error: {e}", exc_info=True)
            return f"❌ Error creating wallet: {str(e)}"

    async def grant_policy_raw(self, input_str: str) -> str:
        """Raw grant_policy function that parses input directly."""
        try:
            logger.info(f"[GRANT_POLICY_RAW] Raw input string: {input_str!r}")
            
            # Initialize defaults
            per_tx_max = 10.0
            daily_cap = 100.0
            wallet_addr = None
            
            # === STEP 1: PARSE RAW INPUT ===
            if isinstance(input_str, str) and input_str.strip():
                input_str = input_str.strip()
                
                # Case 1: JSON format
                if input_str.startswith("{") and input_str.endswith("}"):
                    try:
                        data = json.loads(input_str)
                        per_tx_max = float(data.get("per_tx_max", 10.0))
                        daily_cap = float(data.get("daily_cap", 100.0))
                        wallet_addr = data.get("wallet", "")
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        logger.warning(f"[GRANT_POLICY_RAW] JSON parsing failed: {e}")
                        return f"❌ Invalid input format. Expected JSON like {{\"per_tx_max\": 10.0, \"daily_cap\": 100.0}}"
                
                # Case 2: Key=value format
                elif "=" in input_str:
                    parts = input_str.split(",")
                    for part in parts:
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip().lower()
                            val = val.strip().strip('"\'')
                            if key in ("per_tx_max", "per_tx", "max_per_tx"):
                                try:
                                    per_tx_max = float(val)
                                except (ValueError, TypeError):
                                    pass
                            elif key in ("daily_cap", "daily", "daily_max"):
                                try:
                                    daily_cap = float(val)
                                except (ValueError, TypeError):
                                    pass
                            elif key in ("wallet", "address"):
                                wallet_addr = val
            
            # === STEP 2: DETERMINE WALLET ===
            if wallet_addr:
                wallet_addr = _first_address(str(wallet_addr))
            if not wallet_addr:
                wallet_addr = _first_address(str(self.current_wallet)) if self.current_wallet else None
            
            if not wallet_addr:
                return "❌ No active wallet found. Please create a wallet first."
            
            # === STEP 3: GRANT POLICY ===
            await self.db.create_or_update_policy(
                wallet_id=wallet_addr.lower(),
                enabled=True,
                per_tx_max=per_tx_max,
                daily_cap=daily_cap
            )
            
            return f"""✅ Perfect! I've set up spending permissions for your wallet.

Your spending limits:
- Maximum per transaction: {per_tx_max} USDC
- Maximum per day: {daily_cap} USDC

You're all set to make transfers now!"""
        except Exception as e:
            logger.error(f"[GRANT_POLICY_RAW] Policy grant error: {e}", exc_info=True)
            return f"❌ Error granting policy: {str(e)}"

    async def check_policy_raw(self, input_str: str = "") -> str:
        """Raw check_policy function that parses input directly."""
        try:
            logger.info(f"[CHECK_POLICY_RAW] Raw input string: {input_str!r}")
            
            wallet_addr = None
            
            # === STEP 1: PARSE RAW INPUT ===
            if isinstance(input_str, str) and input_str.strip():
                input_str = input_str.strip()
                
                # Case 1: JSON format
                if input_str.startswith("{") and input_str.endswith("}"):
                    try:
                        data = json.loads(input_str)
                        wallet_addr = data.get("wallet", "")
                    except (json.JSONDecodeError, ValueError, TypeError):
                        wallet_addr = _first_address(input_str)
                
                # Case 2: Key=value format
                elif "=" in input_str:
                    parts = input_str.split(",")
                    for part in parts:
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip().lower()
                            val = val.strip().strip('"\'')
                            if key in ("wallet", "address"):
                                wallet_addr = val
                
                # Case 3: Plain address
                else:
                    wallet_addr = _first_address(input_str)
            
            # === STEP 2: DETERMINE WALLET ===
            if wallet_addr:
                wallet_addr = _first_address(str(wallet_addr))
            if not wallet_addr:
                wallet_addr = _first_address(str(self.current_wallet)) if self.current_wallet else None
            
            if not wallet_addr:
                return "❌ No active wallet found. Please create a wallet first."
            
            # === STEP 3: CHECK POLICY ===
            policy = await self.db.get_policy(wallet_addr.lower())
            
            if not policy or not policy.enabled:
                return f"""Your wallet doesn't have spending permissions enabled yet.

To enable transfers, I can set up spending limits for you. Would you like me to do that?"""
            
            spent = await self.db.get_daily_spent(wallet_addr.lower())
            remaining = float(policy.daily_cap) - float(spent)
            
            return f"""Your wallet spending permissions are active! ✅

Current limits:
- Per transaction: up to {float(policy.per_tx_max)} USDC
- Daily limit: {float(policy.daily_cap)} USDC
- Spent today: {float(spent)} USDC
- Remaining today: {remaining} USDC"""
        except Exception as e:
            logger.error(f"[CHECK_POLICY_RAW] Policy check error: {e}", exc_info=True)
            return f"❌ Error checking policy: {str(e)}"
        """Create a new wallet. The underscore parameter is ignored (for LangChain compatibility)."""
        try:
            result = await self.cdp.create_wallet()
            wallet_id = result["address"]
            
            await self.db.create_or_update_wallet(
                session_id=self.session_id,
                wallet_id=wallet_id,
                address=result["address"],
                network=result["network"]
            )
            
            self.current_wallet = wallet_id
            logger.info(f"✅ Wallet created and saved: {wallet_id} for session {self.session_id}")
            
            return f"""✅ Great! I've created a new wallet for you.

Your wallet address: {result['address']}
Network: {result['network']}

This wallet is now ready to use. Would you like me to request some testnet tokens so you can get started?"""
        except Exception as e:
            logger.error(f"Wallet creation error: {e}", exc_info=True)
            return f"❌ Error creating wallet: {str(e)}"
    
    async def get_balance_raw(self, input_str: str = "") -> str:
        """
        Raw get_balance function that parses LangChain input directly.
        """
        try:
            logger.info(f"[GET_BALANCE_RAW] Raw input string: {input_str!r}")
            
            wallet_addr = None
            
            # === STEP 1: PARSE RAW INPUT ===
            if isinstance(input_str, str) and input_str.strip():
                input_str = input_str.strip()
                
                # Case 1: JSON format
                if input_str.startswith("{") and input_str.endswith("}"):
                    try:
                        data = json.loads(input_str)
                        wallet_addr = data.get("wallet", "")
                    except (json.JSONDecodeError, ValueError, TypeError):
                        # Try to extract address from malformed JSON
                        wallet_addr = _first_address(input_str)
                
                # Case 2: Key=value format
                elif "=" in input_str:
                    parts = input_str.split(",")
                    for part in parts:
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip().lower()
                            val = val.strip().strip('"\'')
                            if key in ("wallet", "address"):
                                wallet_addr = val
                
                # Case 3: Plain address
                else:
                    wallet_addr = _first_address(input_str)
            
            # === STEP 2: DETERMINE WALLET ===
            if wallet_addr:
                wallet_addr = _first_address(str(wallet_addr))
            if not wallet_addr:
                wallet_addr = _first_address(str(self.current_wallet)) if self.current_wallet else None
            
            if not wallet_addr:
                return "❌ No active wallet found. Please create a wallet first."
            
            # === STEP 3: GET BALANCE ===
            balance = await self.cdp.get_balance(wallet_addr)
            assets = balance.get("assets", [])
            
            eth_bal = 0.0
            usdc_bal = 0.0
            
            for asset in assets:
                symbol = asset.get("symbol", "").upper()
                try:
                    bal = float(asset.get("balance", 0))
                    if symbol == "ETH":
                        eth_bal = bal
                    elif symbol == "USDC":
                        usdc_bal = bal
                except (ValueError, TypeError):
                    continue
            
            if eth_bal == 0.0 and usdc_bal == 0.0:
                return f"""Your wallet ({wallet_addr[:10]}...{wallet_addr[-8:]}) currently has no funds.

To get started, you can request testnet tokens:
- ETH for transaction fees: fund_testnet with {{"token": "eth"}}
- USDC for transfers: fund_testnet with {{"token": "usdc"}}"""
            
            response = f"""Here's your wallet balance:

💰 ETH: {eth_bal} ETH
💵 USDC: {usdc_bal} USDC

Address: {wallet_addr[:10]}...{wallet_addr[-8:]}"""
            
            if eth_bal < 0.0001:
                response += "\n\n⚠️  You're running low on ETH. You'll need ETH to pay for transaction fees."
            if usdc_bal < 0.01:
                response += "\n\n💡 You have very little USDC for transfers."
            
            return response
            
        except Exception as e:
            logger.error(f"[GET_BALANCE_RAW] Balance check error: {e}", exc_info=True)
            return f"❌ Error getting balance: {str(e)}"
        """Get wallet balance."""
        try:
            wallet_addr = _first_address(wallet) or _first_address(self.current_wallet or "")
            if not wallet_addr:
                return "You don't have an active wallet yet. Would you like me to create one for you?"
            
            balance = await self.cdp.get_balance(wallet_addr)
            assets = balance.get("assets", [])
            
            eth_bal = 0.0
            usdc_bal = 0.0
            
            for asset in assets:
                symbol = asset.get("symbol", "").upper()
                try:
                    bal = float(asset.get("balance", 0))
                except (ValueError, TypeError):
                    bal = 0.0
                if symbol == "ETH":
                    eth_bal = bal
                elif symbol == "USDC":
                    usdc_bal = bal
            
            if eth_bal == 0.0 and usdc_bal == 0.0:
                return f"""Your wallet ({wallet_addr[:10]}...{wallet_addr[-8:]}) currently has no funds.

To get started, I can request testnet tokens for you:
- ETH for transaction fees (gas)
- USDC for making transfers

Would you like me to fund your wallet with testnet tokens?"""
            
            response = f"""Here's your wallet balance:

💰 ETH: {eth_bal} ETH
💵 USDC: {usdc_bal} USDC

Address: {wallet_addr[:10]}...{wallet_addr[-8:]}"""
            
            if eth_bal < 0.0001:
                response += "\n\n⚠️  You're running low on ETH. You'll need ETH to pay for transaction fees. I can request some testnet ETH for you."
            if usdc_bal < 0.01:
                response += "\n\n💡 You have very little USDC. I can request testnet USDC if you'd like to make transfers."
            
            return response
        except Exception as e:
            logger.error(f"Balance check error: {e}")
            return f"❌ Error getting balance: {str(e)}"
    
    async def fund_testnet_raw(self, input_str: str) -> str:
        """
        Raw fund_testnet function that parses LangChain input directly without Pydantic.
        
        This bypasses all Pydantic validation issues and handles the input parsing manually.
        """
        try:
            logger.info(f"[FUND_TESTNET_RAW] Raw input string: {input_str!r}")
            
            # Initialize defaults
            token = "eth"
            wallet_addr = None
            
            # === STEP 1: PARSE RAW INPUT ===
            if isinstance(input_str, str):
                input_str = input_str.strip()
                
                # Case 1: Direct JSON string
                if input_str.startswith("{") and input_str.endswith("}"):
                    try:
                        data = json.loads(input_str)
                        token = data.get("token", "eth")
                        wallet_addr = data.get("wallet", "")
                        logger.info(f"[FUND_TESTNET_RAW] Parsed JSON: token={token}, wallet={wallet_addr}")
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        logger.warning(f"[FUND_TESTNET_RAW] JSON parsing failed: {e}")
                        return f"❌ Invalid input format. Expected JSON like {{\"token\": \"usdc\"}}"
                
                # Case 2: Key=value format
                elif "=" in input_str:
                    parts = input_str.split(",")
                    for part in parts:
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip().lower()
                            val = val.strip().strip('"\'')
                            if key in ("token", "asset"):
                                token = val
                            elif key in ("wallet", "address"):
                                wallet_addr = val
                
                # Case 3: Simple token name
                else:
                    # Look for token names in the string
                    input_lower = input_str.lower()
                    if "usdc" in input_lower:
                        token = "usdc"
                    elif "eth" in input_lower:
                        token = "eth"
                    else:
                        token = input_str.strip().lower()
            
            # === STEP 2: VALIDATION AND SETUP ===
            # Clean and validate token
            token = str(token).strip().lower().strip("'\"")
            valid_tokens = ["eth", "usdc"]
            if token not in valid_tokens:
                return f"❌ Invalid token '{token}'. Must be one of: {', '.join(valid_tokens)}"
            
            # Determine wallet address
            if wallet_addr:
                wallet_addr = _first_address(str(wallet_addr))
            if not wallet_addr:
                wallet_addr = _first_address(str(self.current_wallet)) if self.current_wallet else None
            
            if not wallet_addr:
                return "❌ No active wallet found. Please create a wallet first."
            
            logger.info(f"[FUND_TESTNET_RAW] Validated: requesting {token} for {wallet_addr}")
            
            # === STEP 3: BALANCE CHECK (OPTIONAL OPTIMIZATION) ===
            try:
                balance = await self.cdp.get_balance(wallet_addr)
                assets = balance.get("assets", [])
                
                for asset in assets:
                    symbol = asset.get("symbol", "").upper()
                    try:
                        bal = float(asset.get("balance", 0))
                        
                        # If requesting ETH and already have enough for gas fees, skip
                        if token == "eth" and symbol == "ETH" and bal >= 0.0001:
                            return f"""ℹ️ Your wallet already has {bal} ETH, which is sufficient for gas fees.

Base Sepolia has very low gas costs (~0.00000006 ETH per transfer).
You have enough ETH for approximately {int(bal / 0.00000006)} transactions.
No need to request more testnet ETH."""
                        
                        # If requesting USDC and already have a reasonable amount, skip
                        if token == "usdc" and symbol == "USDC" and bal >= 10.0:
                            return f"""ℹ️ Your wallet already has {bal} USDC.

If you need more, I can request additional testnet USDC, but you currently have enough for most transfers."""
                    except (ValueError, TypeError):
                        continue
            except Exception as e:
                logger.warning(f"[FUND_TESTNET_RAW] Balance check failed: {e}")
            
            # === STEP 4: REQUEST FUNDS ===
            logger.info(f"[FUND_TESTNET_RAW] Requesting {token} from faucet for {wallet_addr}")
            
            result = await self.cdp.request_faucet(
                address=wallet_addr,
                token=token,
                wait_for_confirmation=False
            )
            
            return f"""✅ I've requested {token.upper()} for your wallet!

Transaction submitted: {result.get('tx_hash', 'pending')}

The funds typically arrive within 1-2 minutes. Please check your balance again in a moment to confirm the funds have arrived before proceeding with transfers."""
            
        except Exception as e:
            logger.error(f"[FUND_TESTNET_RAW] Faucet failed: {e}", exc_info=True)
            return f"❌ Error funding wallet: {str(e)}"
        """Fund wallet from testnet faucet. Defaults to ETH if token not specified."""
        try:
            wallet_addr = _first_address(wallet) or _first_address(self.current_wallet or "")
            if not wallet_addr:
                return "You don't have an active wallet yet. Would you like me to create one for you?"
            
            # Clean and normalize token parameter
            token_clean = str(token).strip().lower().strip("'\"")
            
            # Remove any key=value formatting that might have slipped through
            if "=" in token_clean:
                token_clean = token_clean.split("=")[-1].strip().strip("'\"")
            
            # If token contains JSON-like structure (shouldn't happen with fixed validator, but just in case)
            if token_clean.startswith("{") or "," in token_clean or "0x" in token_clean:
                # Fallback to default
                logger.warning(f"Received malformed token input: {token_clean}, defaulting to 'eth'")
                token_clean = "eth"
            
            # Validate token
            valid_tokens = ["eth", "usdc"]
            if token_clean not in valid_tokens:
                return f"❌ Invalid token '{token_clean}'. Must be one of: {', '.join(valid_tokens)}"
            
            # Smart check: Verify balance first to avoid unnecessary faucet requests
            try:
                balance = await self.cdp.get_balance(wallet_addr)
                assets = balance.get("assets", [])
                
                for asset in assets:
                    symbol = asset.get("symbol", "").upper()
                    bal = float(asset.get("balance", 0))
                    
                    # If requesting ETH and already have enough for gas fees, skip
                    # Base Sepolia minimum threshold: 0.0001 ETH (enough for 1,500+ transactions)
                    if token_clean == "eth" and symbol == "ETH" and bal >= 0.0001:
                        return f"""ℹ️ Your wallet already has {bal} ETH, which is sufficient for gas fees.

Base Sepolia has very low gas costs (~0.00000006 ETH per transfer).
You have enough ETH for approximately {int(bal / 0.00000006)} transactions.
No need to request more testnet ETH."""
                    
                    # If requesting USDC and already have a reasonable amount, skip
                    if token_clean == "usdc" and symbol == "USDC" and bal >= 1.0:
                        return f"""ℹ️ Your wallet already has {bal} USDC.

If you need more, I can request additional testnet USDC, but you currently have enough for most transfers."""
            except Exception as e:
                logger.warning(f"Balance check before faucet failed: {e}")
                # Continue with faucet request anyway
            
            logger.info(f"Requesting {token_clean} from faucet for {wallet_addr}")
            
            result = await self.cdp.request_faucet(
                address=wallet_addr,
                token=token_clean,
                wait_for_confirmation=False  # Changed to False for faster response
            )
            
            return f"""✅ I've requested {token_clean.upper()} for your wallet!

Transaction submitted: {result.get('tx_hash', 'pending')}

The funds typically arrive within 1-2 minutes. Please check your balance again in a moment to confirm the funds have arrived before proceeding with transfers."""
        except Exception as e:
            logger.error(f"Faucet error: {e}", exc_info=True)
            return f"❌ Error funding wallet: {str(e)}"
    
    async def grant_policy(self, per_tx_max: float | str = 10.0, daily_cap: float | str = 100.0, wallet: str = "", **kwargs) -> str:
        """Grant spending policy."""
        try:
            # Coerce numbers from strings and apply safe defaults
            def _to_float(x, default):
                try:
                    return float(x)
                except Exception:
                    return float(default)

            per_tx_f = _to_float(per_tx_max, 10.0)
            daily_f = _to_float(daily_cap, 100.0)

            wallet_addr = _first_address(wallet) or _first_address(self.current_wallet or "")
            if not wallet_addr:
                return "You don't have an active wallet yet. Would you like me to create one for you?"
            
            await self.db.create_or_update_policy(
                wallet_id=(wallet_addr or "").lower(),
                enabled=True,
                per_tx_max=per_tx_f,
                daily_cap=daily_f
            )
            
            return f"""✅ Perfect! I've set up spending permissions for your wallet.

Your spending limits:
- Maximum per transaction: {per_tx_f} USDC
- Maximum per day: {daily_f} USDC

You're all set to make transfers now!"""
        except Exception as e:
            logger.error(f"Policy grant error: {e}")
            return f"❌ Error granting policy: {str(e)}"
    
    async def check_policy(self, wallet: str = "") -> str:
        """Check policy status."""
        try:
            wallet_addr = wallet.strip() or self.current_wallet
            if not wallet_addr:
                return "You don't have an active wallet yet. Would you like me to create one for you?"
            
            policy = await self.db.get_policy((wallet_addr or "").lower())
            
            if not policy or not policy.enabled:
                return f"""Your wallet doesn't have spending permissions enabled yet.

To enable transfers, I can set up spending limits for you. Would you like me to do that?"""
            
            spent = await self.db.get_daily_spent((wallet_addr or "").lower())
            remaining = float(policy.daily_cap) - float(spent)
            
            return f"""Your wallet spending permissions are active! ✅

Current limits:
- Per transaction: up to {float(policy.per_tx_max)} USDC
- Daily limit: {float(policy.daily_cap)} USDC
- Spent today: {float(spent)} USDC
- Remaining today: {remaining} USDC"""
        except Exception as e:
            logger.error(f"Policy check error: {e}")
            return f"❌ Error checking policy: {str(e)}"
    
    async def transfer_raw(self, input_str: str) -> str:
        """
        Raw transfer function that parses LangChain input directly without Pydantic.
        
        This bypasses all Pydantic validation issues and handles the input parsing manually.
        """
        try:
            logger.info(f"[TRANSFER_RAW] Raw input string: {input_str!r}")
            
            # Initialize defaults
            to_addr = None
            amount_value = 0.0
            from_addr = None
            
            # === STEP 1: PARSE RAW INPUT ===
            # Try to parse as JSON first
            if isinstance(input_str, str):
                input_str = input_str.strip()
                
                # Case 1: Direct JSON string
                if input_str.startswith("{") and input_str.endswith("}"):
                    try:
                        data = json.loads(input_str)
                        to_addr = data.get("to", "")
                        amount_value = float(data.get("amount", 0))
                        from_addr = data.get("wallet", "")
                        logger.info(f"[TRANSFER_RAW] Parsed JSON: to={to_addr}, amount={amount_value}")
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        logger.warning(f"[TRANSFER_RAW] JSON parsing failed: {e}")
                        return f"❌ Invalid input format. Expected JSON like {{\"to\": \"0x...\", \"amount\": 0.05}}"
                
                # Case 2: Key=value format
                elif "=" in input_str:
                    parts = input_str.split(",")
                    for part in parts:
                        if "=" in part:
                            key, val = part.split("=", 1)
                            key = key.strip().lower()
                            val = val.strip().strip('"\'')
                            if key in ("to", "recipient", "destination"):
                                to_addr = val
                            elif key in ("amount", "value"):
                                try:
                                    amount_value = float(val)
                                except (ValueError, TypeError):
                                    amount_value = 0.0
                            elif key in ("wallet", "from", "source"):
                                from_addr = val
                
                # Case 3: Try to extract address and amount from free text
                else:
                    # Look for Ethereum address
                    addr_match = ADDR_RE.search(input_str)
                    if addr_match:
                        to_addr = addr_match.group(0)
                    
                    # Look for amount (number)
                    import re
                    amount_match = re.search(r'\b(\d+(?:\.\d+)?)\b', input_str)
                    if amount_match:
                        try:
                            amount_value = float(amount_match.group(1))
                        except (ValueError, TypeError):
                            amount_value = 0.0
            
            # === STEP 2: VALIDATION ===
            # Clean up the recipient address  
            if to_addr:
                to_addr = _first_address(str(to_addr))
            if not to_addr:
                return "❌ Invalid or missing recipient address. Please provide a valid Ethereum address starting with 0x."
            
            # Validate amount
            if amount_value <= 0:
                return "❌ Invalid or missing amount. Please specify a positive number like 0.05 for 0.05 USDC."
            
            # Determine source wallet
            if from_addr:
                from_addr = _first_address(str(from_addr))
            if not from_addr:
                from_addr = _first_address(str(self.current_wallet)) if self.current_wallet else None
            
            if not from_addr:
                return "❌ No active wallet found. Please create a wallet first."
            
            # Prevent self-transfers
            if from_addr.lower() == to_addr.lower():
                return f"❌ Cannot transfer to the same wallet address. Please provide a different destination."
            
            logger.info(f"[TRANSFER_RAW] Validated: {amount_value} USDC from {from_addr} to {to_addr}")
            
            # === STEP 3: POLICY VALIDATION ===
            logger.info(f"[TRANSFER_RAW] Starting policy validation for {amount_value} USDC")
            try:
                validation_result = await self.db.validate_transaction(from_addr.lower(), amount_value)
                
                if not validation_result["allowed"]:
                    reason = validation_result["reason"]
                    policy_info = validation_result.get("policy_info", {})
                    
                    logger.error(f"[TRANSFER_RAW] Policy validation failed: {reason}")
                    
                    # Format detailed error message based on validation failure type
                    if "per-transaction limit" in reason:
                        per_tx_max = policy_info.get("per_tx_max", 0)
                        excess = policy_info.get("excess_amount", 0)
                        return f"""❌ Transfer blocked: Amount exceeds per-transaction limit.

Requested amount: {amount_value} USDC
Maximum per transaction: {per_tx_max} USDC
Excess amount: {excess:.6f} USDC

Please reduce the transfer amount or increase your per-transaction limit."""
                    
                    elif "daily limit" in reason:
                        daily_cap = policy_info.get("daily_cap", 0)
                        daily_spent = policy_info.get("daily_spent", 0)
                        remaining = policy_info.get("remaining_daily", 0)
                        excess = policy_info.get("excess_amount", 0)
                        return f"""❌ Transfer blocked: Amount exceeds daily spending limit.

Requested amount: {amount_value} USDC
Daily limit: {daily_cap} USDC
Already spent today: {daily_spent} USDC
Remaining today: {remaining:.6f} USDC
Excess amount: {excess:.6f} USDC

Please wait until tomorrow or reduce the transfer amount."""
                    
                    else:
                        return f"""❌ Transfer blocked: {reason}

Please grant spending authority first by setting transaction limits.
Example: grant_policy with {{"per_tx_max": 10.0, "daily_cap": 100.0}}"""
                
                # Log successful validation details
                policy_info = validation_result.get("policy_info", {})
                per_tx_max = policy_info.get("per_tx_max", 0)
                remaining_daily = policy_info.get("remaining_daily", 0)
                logger.info(f"[TRANSFER_RAW] Policy validation passed: {amount_value} <= {per_tx_max} per-tx, {amount_value} <= {remaining_daily:.6f} remaining daily")
                
            except Exception as e:
                logger.error(f"[TRANSFER_RAW] Policy validation failed: {e}", exc_info=True)
                return f"❌ Transfer blocked: Unable to validate spending policy. Error: {str(e)}"
            
            # === STEP 4: BALANCE CHECKS ===
            logger.info(f"[TRANSFER_RAW] Starting balance validation")
            try:
                balance_info = await self.cdp.get_balance(from_addr)
                assets = balance_info.get("assets", [])
                
                eth_balance = 0.0
                usdc_balance = 0.0
                
                for asset in assets:
                    symbol = asset.get("symbol", "").upper()
                    try:
                        bal = float(asset.get("balance", 0))
                        if symbol == "ETH":
                            eth_balance = bal
                        elif symbol == "USDC":
                            usdc_balance = bal
                    except (ValueError, TypeError):
                        continue
                
                logger.info(f"[TRANSFER_RAW] Current balances: ETH={eth_balance}, USDC={usdc_balance}")
                
                # Check USDC balance
                if usdc_balance < amount_value:
                    logger.error(f"[TRANSFER_RAW] Insufficient USDC: {usdc_balance} < {amount_value}")
                    return f"""❌ Insufficient USDC balance.

Available: {usdc_balance} USDC
Requested: {amount_value} USDC
Shortfall: {amount_value - usdc_balance} USDC

Please request more USDC first using: fund_testnet with {{"token": "usdc"}}
Then try the transfer again."""
                
                # Check ETH for gas
                if eth_balance < 0.0001:
                    logger.error(f"[TRANSFER_RAW] Insufficient ETH for gas: {eth_balance} < 0.0001")
                    return f"""❌ Insufficient ETH for transaction fees.

Current ETH: {eth_balance}
Minimum needed: 0.0001 ETH

Please request ETH first using: fund_testnet with {{"token": "eth"}}
Then try the transfer again."""
                
                logger.info(f"[TRANSFER_RAW] Balance validation passed")
                
            except Exception as e:
                logger.warning(f"[TRANSFER_RAW] Balance check failed: {e}")
                return f"❌ Unable to verify wallet balance. Please try again. Error: {str(e)}"
            
            # === STEP 5: EXECUTE TRANSFER ===
            logger.info(f"[TRANSFER_RAW] All validations passed. Executing transfer: {amount_value} USDC from {from_addr} to {to_addr}")
            
            transfer_result = await self.cdp.transfer_usdc(
                from_address=from_addr,
                to_address=to_addr,
                amount=str(amount_value)
            )
            
            # === STEP 6: RECORD TRANSACTION ===
            logger.info(f"[TRANSFER_RAW] Transfer successful, recording transaction")
            try:
                await self.db.record_transaction(
                    wallet_id=from_addr.lower(),
                    tx_hash=transfer_result.get("tx_hash"),
                    to_address=to_addr,
                    amount=amount_value,
                    asset="USDC"
                )
                await self.db.record_spend(from_addr.lower(), amount_value)
                logger.info(f"[TRANSFER_RAW] Transaction recorded successfully")
            except Exception as e:
                logger.warning(f"[TRANSFER_RAW] Failed to record transaction: {e}")
            
            # === STEP 7: SUCCESS RESPONSE ===
            tx_hash = transfer_result.get("tx_hash", "pending")
            
            return f"""✅ Transfer completed successfully!

💰 Amount: {amount_value} USDC
📤 From: {from_addr[:10]}...{from_addr[-8:]}
📥 To: {to_addr[:10]}...{to_addr[-8:]}
🔗 Transaction: {tx_hash}

View on BaseScan: https://sepolia.basescan.org/tx/{tx_hash}"""
            
        except Exception as e:
            logger.error(f"[TRANSFER_RAW] Transfer failed: {e}", exc_info=True)
            return f"❌ Transfer failed: {str(e)}"
        """
        Transfer USDC to another address.
        
        Robust implementation that handles all LangChain input quirks.
        """
        try:
            logger.info(f"[TRANSFER] Raw function inputs - to={to!r}, amount={amount!r}, wallet={wallet!r}")
            
            # === STEP 1: ROBUST INPUT PARSING ===
            # Handle the LangChain bug where JSON gets stuffed into the 'to' parameter
            actual_to = to
            actual_amount = amount
            actual_wallet = wallet
            
            # Check if 'to' contains JSON (common LangChain bug)
            if isinstance(to, str) and to.startswith("{") and to.endswith("}"):
                logger.info(f"[TRANSFER] Detected JSON in 'to' parameter, parsing...")
                try:
                    parsed_data = json.loads(to)
                    if isinstance(parsed_data, dict):
                        actual_to = parsed_data.get("to", "")
                        actual_amount = parsed_data.get("amount", amount)
                        actual_wallet = parsed_data.get("wallet", wallet)
                        logger.info(f"[TRANSFER] Successfully parsed JSON - to: {actual_to}, amount: {actual_amount}")
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"[TRANSFER] JSON parsing failed: {e}, using original values")
            
            # === STEP 2: CLEAN AND VALIDATE INPUTS ===
            # Clean up the recipient address
            to_addr = _first_address(str(actual_to)) if actual_to else None
            if not to_addr:
                return "❌ Invalid recipient address. Please provide a valid Ethereum address starting with 0x."
            
            # Parse and validate amount
            try:
                if isinstance(actual_amount, str):
                    actual_amount = actual_amount.strip()
                amount_value = float(actual_amount) if actual_amount not in (None, "", 0) else 0.0
            except (ValueError, TypeError):
                logger.error(f"[TRANSFER] Could not parse amount: {actual_amount!r}")
                return f"❌ Invalid amount '{actual_amount}'. Please specify a positive number like 0.05 or 1.5."
            
            # Validate amount is positive
            if amount_value <= 0:
                return "❌ Transfer amount must be greater than 0. Example: 0.05 for 0.05 USDC."
            
            # Determine source wallet
            from_addr = _first_address(str(actual_wallet)) or _first_address(str(self.current_wallet)) if self.current_wallet else None
            if not from_addr:
                return "❌ No active wallet found. Please create a wallet first using the create_wallet command."
            
            # === STEP 3: SAFETY CHECKS ===
            # Prevent self-transfers
            if from_addr.lower() == to_addr.lower():
                return f"""❌ Cannot transfer to the same wallet address.
                
Source: {from_addr}
Destination: {to_addr}

Please provide a different destination address."""
            
            logger.info(f"[TRANSFER] Validated transfer: {amount_value} USDC from {from_addr} to {to_addr}")
            
            # === STEP 4: BALANCE AND POLICY CHECKS ===
            # Check balances to provide helpful guidance
            try:
                balance_info = await self.cdp.get_balance(from_addr)
                assets = balance_info.get("assets", [])
                
                eth_balance = 0.0
                usdc_balance = 0.0
                
                for asset in assets:
                    symbol = asset.get("symbol", "").upper()
                    try:
                        bal = float(asset.get("balance", 0))
                        if symbol == "ETH":
                            eth_balance = bal
                        elif symbol == "USDC":
                            usdc_balance = bal
                    except (ValueError, TypeError):
                        continue
                
                # Check if sufficient USDC
                if usdc_balance < amount_value:
                    return f"""❌ Insufficient USDC balance.

Available: {usdc_balance} USDC
Requested: {amount_value} USDC
Needed: {amount_value - usdc_balance} USDC

Request more USDC using: fund_testnet with {{"token": "usdc"}}"""
                
                # Check if sufficient ETH for gas
                if eth_balance < 0.0001:  # Base Sepolia minimum
                    return f"""❌ Insufficient ETH for transaction fees.

Current ETH: {eth_balance}
Minimum needed: 0.0001 ETH

Request ETH using: fund_testnet with {{"token": "eth"}}"""
                
            except Exception as e:
                logger.warning(f"[TRANSFER] Balance check failed: {e}")
                # Continue with transfer attempt
            
            # === STEP 5: EXECUTE TRANSFER ===
            logger.info(f"[TRANSFER] Executing transfer: {amount_value} USDC from {from_addr} to {to_addr}")
            
            transfer_result = await self.cdp.transfer_usdc(
                from_address=from_addr,
                to_address=to_addr,
                amount=str(amount_value)
            )
            
            # === STEP 6: RECORD TRANSACTION ===
            try:
                await self.db.record_transaction(
                    wallet_id=from_addr.lower(),
                    tx_hash=transfer_result.get("tx_hash"),
                    to_address=to_addr,
                    amount=amount_value,
                    asset="USDC"
                )
                await self.db.record_spend(from_addr.lower(), amount_value)
            except Exception as e:
                logger.warning(f"[TRANSFER] Failed to record transaction: {e}")
                # Don't fail the transfer for this
            
            # === STEP 7: SUCCESS RESPONSE ===
            tx_hash = transfer_result.get("tx_hash", "pending")
            
            return f"""✅ Transfer completed successfully!

💰 Amount: {amount_value} USDC
📤 From: {from_addr[:10]}...{from_addr[-8:]}
📥 To: {to_addr[:10]}...{to_addr[-8:]}
🔗 Transaction: {tx_hash}

🔍 View on BaseScan: https://sepolia.basescan.org/tx/{tx_hash}

Your transfer is now processing on the blockchain and should be confirmed within 1-2 minutes."""
            
        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"[TRANSFER] Transfer failed: {e}", exc_info=True)
            
            # Provide specific error guidance
            if "insufficient" in error_msg and ("balance" in error_msg or "funds" in error_msg):
                return "❌ Transfer failed: Insufficient funds. Please check your balance and request more tokens if needed."
            elif "gas" in error_msg or "fee" in error_msg:
                return "❌ Transfer failed: Insufficient ETH for gas fees. Request ETH using fund_testnet."
            elif "policy" in error_msg or "authorization" in error_msg:
                return "❌ Transfer failed: No spending authorization. Please grant policy permissions first."
            elif "network" in error_msg or "connection" in error_msg:
                return "❌ Transfer failed: Network connection issue. Please try again in a moment."
            else:
                return f"❌ Transfer failed: {str(e)}"
    
    def get_tools(self) -> list:
        """Get LangChain tools using raw Tool wrappers to avoid Pydantic issues."""
        return [
            Tool(
                name="create_wallet",
                description="Create a new wallet. No input required.",
                func=self.create_wallet_raw,
                coroutine=self.create_wallet_raw,
            ),
            Tool(
                name="get_balance",
                description="Check wallet balance. Shows ETH and USDC amounts. Optional wallet parameter: {\"wallet\": \"0x...\"} or just empty for active wallet.",
                func=self.get_balance_raw,
                coroutine=self.get_balance_raw,
            ),
            Tool(
                name="fund_testnet",
                description=(
                    "Request testnet funds from faucet. Input should be JSON format like: {\"token\": \"usdc\"} or {\"token\": \"eth\"}\n"
                    "The 'token' field must be either 'eth' or 'usdc'.\n"
                    "Optional 'wallet' field for specific wallet (uses active wallet if not specified).\n"
                    "Funds arrive in 1-2 minutes (async), so tell user to wait after requesting."
                ),
                func=self.fund_testnet_raw,
                coroutine=self.fund_testnet_raw,
            ),
            Tool(
                name="grant_policy",
                description="Grant spending authority with per-transaction and daily limits. Input: {\"per_tx_max\": 10.0, \"daily_cap\": 100.0}",
                func=self.grant_policy_raw,
                coroutine=self.grant_policy_raw,
            ),
            Tool(
                name="check_policy",
                description="Check policy status and spending limits for the wallet. Optional wallet parameter: {\"wallet\": \"0x...\"} or empty for active wallet.",
                func=self.check_policy_raw,
                coroutine=self.check_policy_raw,
            ),
            Tool(
                name="transfer",
                description=(
                    "Transfer USDC to another address. Input should be JSON format like: {\"to\": \"0xRecipientAddress\", \"amount\": 0.05}\n"
                    "The 'to' field is the RECIPIENT/DESTINATION address (where funds go).\n"
                    "The 'amount' field is the USDC amount to transfer.\n"
                    "Optional 'wallet' field for source wallet (uses active wallet if not specified).\n"
                    "Automatically checks balances and policy before executing."
                ),
                func=self.transfer_raw,
                coroutine=self.transfer_raw,
            ),
        ]
