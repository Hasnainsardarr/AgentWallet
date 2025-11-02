"""
Debug script to test CDP balance retrieval directly.
Run this to diagnose why balances might be showing as 0.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cdp import CdpClient
from dotenv import load_dotenv

load_dotenv()

async def debug_balance(address: str):
    """Debug balance retrieval for a specific address."""
    print("=" * 70)
    print("CDP Balance Debug Tool")
    print("=" * 70)
    print(f"\n🔍 Testing balance retrieval for: {address}")
    print(f"🌐 Network: base-sepolia\n")
    
    try:
        # Initialize CDP client
        print("1️⃣  Initializing CDP Client...")
        client = CdpClient()
        print("   ✅ CDP Client initialized\n")
        
        # Request balance
        print("2️⃣  Fetching token balances from CDP...")
        balances = await client.evm.list_token_balances(
            address=address,
            network="base-sepolia"
        )
        print(f"   ✅ Request completed\n")
        
        # Analyze response
        print("3️⃣  Analyzing response:")
        print(f"   • Type: {type(balances)}")
        print(f"   • Length: {len(balances) if balances else 0}")
        print(f"   • Is None: {balances is None}")
        print(f"   • Is Empty: {not balances}\n")
        
        if not balances:
            print("⚠️  WARNING: No balances returned!")
            print("\nPossible reasons:")
            print("  1. Wallet is empty (no tokens)")
            print("  2. Wallet is brand new (not indexed yet)")
            print("  3. CDP API issue")
            print("  4. Network issue")
            print(f"\n💡 Check wallet on BaseScan:")
            print(f"   https://sepolia.basescan.org/address/{address}\n")
        else:
            print(f"4️⃣  Found {len(balances)} balance(s):\n")
            
            for i, balance_obj in enumerate(balances, 1):
                print(f"   --- Balance #{i} ---")
                print(f"   Type: {type(balance_obj)}")
                
                # Try to extract all possible attributes
                attrs_to_check = [
                    'symbol', 'token_symbol', 'asset_symbol',
                    'balance', 'amount', 'value',
                    'decimals', 'token_decimals', 'asset_decimals'
                ]
                
                print(f"   Attributes:")
                for attr in attrs_to_check:
                    val = getattr(balance_obj, attr, None)
                    if val is not None:
                        print(f"     • {attr}: {val}")
                
                # Try to get the main info
                symbol = (getattr(balance_obj, "symbol", None) or 
                         getattr(balance_obj, "token_symbol", None) or
                         getattr(balance_obj, "asset_symbol", None) or
                         "UNKNOWN")
                
                balance_val = (getattr(balance_obj, "balance", None) or 
                              getattr(balance_obj, "amount", None) or
                              getattr(balance_obj, "value", None) or
                              "0")
                
                decimals = (getattr(balance_obj, "decimals", None) or 
                           getattr(balance_obj, "token_decimals", None) or
                           getattr(balance_obj, "asset_decimals", None) or
                           18)
                
                print(f"\n   📊 Parsed Values:")
                print(f"     • Symbol: {symbol}")
                print(f"     • Balance: {balance_val}")
                print(f"     • Decimals: {decimals}")
                print()
        
        # Close client
        await client.aclose()
        print("✅ Debug complete!\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\nFull error details:")
        import traceback
        traceback.print_exc()
        print()


async def test_faucet(address: str):
    """Test requesting faucet funds."""
    print("\n" + "=" * 70)
    print("Faucet Test")
    print("=" * 70)
    print(f"\n🚰 Testing faucet for: {address}\n")
    
    try:
        client = CdpClient()
        
        print("1️⃣  Requesting ETH from faucet...")
        result = await client.evm.request_faucet(
            address=address,
            network="base-sepolia",
            token="eth"
        )
        print(f"   ✅ Result: {result}")
        print(f"   Type: {type(result)}\n")
        
        # Extract tx hash
        if isinstance(result, str):
            tx_hash = result
        elif isinstance(result, dict):
            tx_hash = result.get("transactionHash") or result.get("txHash") or result.get("tx_hash")
        else:
            tx_hash = str(result)
        
        print(f"📝 Transaction Hash: {tx_hash}")
        print(f"🔗 View on BaseScan: https://sepolia.basescan.org/tx/{tx_hash}\n")
        
        print("⏳ Waiting 10 seconds for transaction to process...")
        await asyncio.sleep(10)
        
        print("\n2️⃣  Checking balance after faucet request...")
        balances = await client.evm.list_token_balances(
            address=address,
            network="base-sepolia"
        )
        
        if balances:
            for b in balances:
                symbol = getattr(b, "symbol", "UNKNOWN")
                balance = getattr(b, "balance", getattr(b, "amount", "0"))
                print(f"   • {symbol}: {balance}")
        else:
            print("   ⚠️  No balances returned yet (may need more time)")
        
        await client.aclose()
        print("\n✅ Faucet test complete!\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        print()


async def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("\nUsage:")
        print(f"  python {sys.argv[0]} <wallet_address> [--test-faucet]")
        print("\nExample:")
        print(f"  python {sys.argv[0]} 0x45176516F0ea8a2bE075379aac922b4DE95969Fd")
        print(f"  python {sys.argv[0]} 0x45176516F0ea8a2bE075379aac922b4DE95969Fd --test-faucet")
        sys.exit(1)
    
    address = sys.argv[1]
    test_faucet_flag = "--test-faucet" in sys.argv
    
    # Validate address format
    if not address.startswith("0x") or len(address) != 42:
        print(f"\n❌ Invalid address format: {address}")
        print("   Address must start with 0x and be 42 characters long")
        sys.exit(1)
    
    # Run balance debug
    await debug_balance(address)
    
    # Optionally test faucet
    if test_faucet_flag:
        response = input("\n❓ Do you want to test the faucet? (yes/no): ")
        if response.lower() in ['yes', 'y']:
            await test_faucet(address)


if __name__ == "__main__":
    asyncio.run(main())


