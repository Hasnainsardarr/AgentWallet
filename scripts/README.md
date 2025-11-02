# Scripts

Helper scripts for testing and development.

## test_flow.py

Complete end-to-end test of the wallet flow.

**Usage:**
```bash
# Make sure backend is running first
cd packages/backend
uvicorn src.app:app --reload --port 8000

# In another terminal, run the test
python scripts/test_flow.py
```

**What it tests:**
1. Wallet creation
2. Testnet funding
3. Authority granting
4. Policy checking
5. Transfer execution
6. Idempotency (retry protection)
7. Authority revocation
8. Blocked transfer (after revocation)

**Expected output:**
```
============================================================
  CDP Wallet Demo - Complete Flow Test
============================================================
✓ Backend is running

============================================================
  1. Creating Wallet
============================================================
✓ Wallet created:
  Wallet ID: w_a1b2c3d4
  Address:   0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
  Network:   base-sepolia

... [more output] ...

============================================================
  ✓ All Tests Passed!
============================================================
```

## Future Scripts

Additional scripts to add:

- `migrate_to_mainnet.py` - Helper to switch from testnet to mainnet
- `stress_test.py` - Load testing for the API
- `backup_db.py` - Database backup utility
- `audit_report.py` - Generate audit reports from ledger



