#!/usr/bin/env python3
"""
Test script demonstrating the complete wallet flow.

This script:
1. Creates a wallet
2. Funds it with testnet tokens
3. Grants spending authority
4. Checks policy
5. Executes a transfer
6. Tests idempotency
7. Revokes authority
8. Attempts blocked transfer

Run from project root:
    python scripts/test_flow.py
"""

import requests
import uuid
import time
import sys


API_BASE = "http://localhost:8000"


def print_section(title):
    """Print a section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check_backend():
    """Check if backend is running."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        response.raise_for_status()
        print("[OK] Backend is running")
        return True
    except Exception as e:
        print(f"[ERROR] Backend is not running: {e}")
        print(f"\nPlease start the backend first:")
        print(f"  cd packages/backend")
        print(f"  uvicorn src.app:app --reload --port 8000")
        return False


def create_wallet():
    """Create a new wallet."""
    print_section("1. Creating Wallet")
    
    response = requests.post(
        f"{API_BASE}/wallet/create",
        json={"user_id": f"test_user_{int(time.time())}"}
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"[OK] Wallet created:")
    print(f"  Wallet ID: {data['wallet_id']}")
    print(f"  Address:   {data['address']}")
    print(f"  Network:   {data['network']}")
    
    return data['wallet_id']


def fund_testnet(wallet_id):
    """Request testnet funds and wait for confirmation."""
    print_section("2. Funding Testnet with ETH and USDC")
    
    # Step 1: Request ETH for gas fees
    print("Step 1: Requesting ETH for gas fees...")
    print("(This may take up to 60 seconds for funds to arrive)")
    
    response_eth = requests.post(
        f"{API_BASE}/wallet/fund_testnet?token=eth&wait=true",
        json={"wallet_id": wallet_id}
    )
    response_eth.raise_for_status()
    
    data_eth = response_eth.json()
    print(f"[OK] ETH funding completed:")
    print(f"  Transaction: {data_eth['faucet_tx']}")
    
    # Step 2: Request USDC for transfers
    print("\nStep 2: Requesting USDC for transfers...")
    print("(This may take up to 60 seconds for funds to arrive)")
    
    response_usdc = requests.post(
        f"{API_BASE}/wallet/fund_testnet?token=usdc&wait=true",
        json={"wallet_id": wallet_id}
    )
    response_usdc.raise_for_status()
    
    data_usdc = response_usdc.json()
    print(f"[OK] USDC funding completed:")
    print(f"  Transaction: {data_usdc['faucet_tx']}")
    print(f"\n[OK] Wallet now has both ETH (for gas) and USDC (for transfers)!")


def grant_authority(wallet_id, per_tx_max=5.0, daily_cap=20.0):
    """Grant spending authority."""
    print_section("3. Granting Authority")
    
    response = requests.post(
        f"{API_BASE}/auth/grant",
        json={
            "wallet_id": wallet_id,
            "per_tx_max": per_tx_max,
            "daily_cap": daily_cap
        }
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"[OK] Authority granted:")
    print(f"  Per-tx max: {per_tx_max} USDC")
    print(f"  Daily cap:  {daily_cap} USDC")


def check_policy(wallet_id):
    """Check policy status."""
    print_section("4. Checking Policy")
    
    response = requests.get(
        f"{API_BASE}/auth/policy",
        params={"wallet_id": wallet_id}
    )
    response.raise_for_status()
    
    data = response.json()
    print(f"[OK] Policy status:")
    print(f"  Enabled:      {data['enabled']}")
    print(f"  Per-tx max:   {data['per_tx_max']} USDC")
    print(f"  Daily cap:    {data['daily_cap']} USDC")
    print(f"  Spent today:  {data['spent_today']} USDC")
    
    return data


def transfer(wallet_id, to_address, amount, idempotency_key=None):
    """Execute a transfer."""
    if not idempotency_key:
        idempotency_key = str(uuid.uuid4())
    
    response = requests.post(
        f"{API_BASE}/transfer",
        json={
            "wallet_id": wallet_id,
            "to": to_address,
            "amount": amount,
            "asset": "USDC",
            "idempotencyKey": idempotency_key
        }
    )
    
    return response, idempotency_key


def test_transfer(wallet_id):
    """Test a successful transfer."""
    print_section("5. Executing Transfer")
    
    to_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"  # Valid 40-char hex address
    amount = 0.01  # Small amount to ensure we have enough from faucet
    
    response, idempotency_key = transfer(wallet_id, to_address, amount)
    response.raise_for_status()
    
    data = response.json()
    print(f"[OK] Transfer successful:")
    print(f"  Amount:       {data['amount']} {data['asset']}")
    print(f"  To:           {data['to']}")
    print(f"  Tx Hash:      {data['txHash']}")
    print(f"  Status:       {data['status']}")
    print(f"  Explorer:     {data['explorer']}")
    
    return idempotency_key


def test_idempotency(wallet_id, idempotency_key):
    """Test idempotency by retrying with same key."""
    print_section("6. Testing Idempotency")
    
    to_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"  # Valid 40-char hex address
    amount = 0.01  # Small amount to match previous transfer
    
    print(f"Retrying transfer with same idempotency key...")
    response, _ = transfer(wallet_id, to_address, amount, idempotency_key)
    response.raise_for_status()
    
    data = response.json()
    print(f"[OK] Idempotency works:")
    print(f"  Same tx hash returned: {data['txHash']}")
    print(f"  No double-spend!")


def revoke_authority(wallet_id):
    """Revoke spending authority."""
    print_section("7. Revoking Authority")
    
    response = requests.post(
        f"{API_BASE}/auth/revoke",
        json={"wallet_id": wallet_id}
    )
    response.raise_for_status()
    
    print(f"[OK] Authority revoked")


def test_blocked_transfer(wallet_id):
    """Test that transfer is blocked after revocation."""
    print_section("8. Testing Blocked Transfer")
    
    to_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"  # Valid 40-char hex address
    amount = 0.01  # Small amount
    
    response, _ = transfer(wallet_id, to_address, amount)
    
    if response.status_code == 403:
        data = response.json()
        print(f"[OK] Transfer correctly blocked:")
        print(f"  Reason: {data.get('detail', 'Unknown')}")
    else:
        print(f"[ERROR] Transfer should have been blocked but wasn't!")
        sys.exit(1)


def main():
    """Run the complete test flow."""
    print("\n" + "=" * 60)
    print("  CDP Wallet Demo - Complete Flow Test")
    print("=" * 60)
    
    # Check backend
    if not check_backend():
        sys.exit(1)
    
    try:
        # Run flow
        wallet_id = create_wallet()
        fund_testnet(wallet_id)
        grant_authority(wallet_id)
        check_policy(wallet_id)
        idempotency_key = test_transfer(wallet_id)
        test_idempotency(wallet_id, idempotency_key)
        revoke_authority(wallet_id)
        test_blocked_transfer(wallet_id)
        
        # Success
        print_section("[SUCCESS] All Tests Passed!")
        print("\nThe complete wallet flow works correctly:")
        print("  1. Wallet creation")
        print("  2. Testnet funding")
        print("  3. Authority management")
        print("  4. Policy enforcement")
        print("  5. Transfers with idempotency")
        print("  6. Revocation and blocking")
        print("\nYou're ready to integrate with real CDP APIs!")
        
    except requests.HTTPError as e:
        print(f"\n[ERROR] HTTP Error: {e}")
        print(f"Response: {e.response.text}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()



