# services/evm_readonly.py
import os, httpx, json
from typing import Optional

# You can override via env; defaults to Base Sepolia public RPC
BASE_SEPOLIA_RPC = os.getenv("BASE_SEPOLIA_RPC", "https://sepolia.base.org")

NETWORK_RPC = {
    "base-sepolia": BASE_SEPOLIA_RPC,
    # add "base-mainnet": "https://mainnet.base.org" if you support mainnet
}

async def _rpc_post(url: str, method: str, params):
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(url, json={"jsonrpc":"2.0","id":1,"method":method,"params":params})
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(f"RPC error: {data['error']}")
        return data["result"]

def _pad_32(hex_no_0x: str) -> str:
    return hex_no_0x.rjust(64, "0")

def _encode_address_32(addr: str) -> str:
    # strip 0x, left-pad to 32 bytes
    return _pad_32(addr.lower().replace("0x", ""))

async def get_native_eth_balance(address: str, network: str = "base-sepolia") -> float:
    rpc = NETWORK_RPC[network]
    result = await _rpc_post(rpc, "eth_getBalance", [address, "latest"])
    # hex -> int -> ETH
    wei = int(result, 16)
    return wei / 10**18

async def get_erc20_balance(address: str, token: str, network: str = "base-sepolia", decimals: int = 18) -> float:
    rpc = NETWORK_RPC[network]
    # ERC20 balanceOf(address) => 0x70a08231 + 32-byte address
    selector = "70a08231"
    data = "0x" + selector + _encode_address_32(address)
    call_obj = {"to": token, "data": data}
    result = await _rpc_post(rpc, "eth_call", [call_obj, "latest"])
    raw = int(result, 16)
    return raw / (10**decimals)
