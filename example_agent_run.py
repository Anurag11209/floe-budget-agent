#!/usr/bin/env python3
"""
Example: Run the Floe Budget Agent with a wallet provider.

This example shows:
1. How to initialize a wallet provider
2. How to run an agent task with borrowing/repayment
3. How to handle results

Run with:
    python3 example_agent_run.py
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import agent components
from app.agent.orchestrator import run_task


async def example_with_mock_wallet():
    """
    Example 1: Run agent with mock wallet (no on-chain transactions).
    Useful for testing logic without spending gas.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Mock Wallet (Testing Mode)")
    print("=" * 60)

    task = """
    You are a budget-aware agent. Your task:
    1. Check how much credit you have available
    2. Report your credit status
    3. Calculate how much you would need to borrow if you spent $150

    Report back:
    - Current credit remaining
    - Current credit limit
    - Borrow amount needed
    - Whether you think you should borrow at 12% APR
    """

    result = await run_task(task, wallet_provider=None)
    print(f"\nAgent Result:")
    print(result["output"] if result["success"] else f"Error: {result['error']}")


async def example_with_private_key_wallet():
    """
    Example 2: Run agent with actual wallet provider (requires credentials).

    THIS PERFORMS REAL ON-CHAIN TRANSACTIONS - ONLY USE IF YOU HAVE FUNDS!

    To use this:
    1. Set PRIVATE_KEY in .env (or use environment variable)
    2. Ensure wallet has USDC/WETH on Base mainnet
    3. Review task carefully before running
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Real Wallet Provider (On-Chain Mode)")
    print("=" * 60)

    PRIVATE_KEY = os.getenv("PRIVATE_KEY")

    if not PRIVATE_KEY:
        print("⚠️  PRIVATE_KEY not set in .env")
        print("   Skipping real wallet example.")
        return

    try:
        from coinbase_agentkit.wallet_providers import EvmWalletProvider
    except ImportError:
        print("⚠️  coinbase-agentkit not installed")
        print("   Run: pip install coinbase-agentkit")
        return

    # Initialize wallet provider
    print("Initializing wallet provider...")
    wallet_provider = EvmWalletProvider.from_private_key(
        private_key=PRIVATE_KEY,
        rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
        network_id="base-mainnet"
    )

    # Define a task
    task = """
    You are an autonomous agent with access to USDC credit on Base mainnet.

    Your task:
    1. Check your current credit status
    2. Report: remaining USDC, credit limit, health indicator

    Do NOT borrow or execute any transactions.
    Just report the status.
    """

    print("Running agent task...")
    result = await run_task(task, wallet_provider=wallet_provider)

    print(f"\nAgent Result:")
    print(result["output"] if result["success"] else f"Error: {result['error']}")


async def example_full_credit_circuit():
    """
    Example 3: Full circuit (check → borrow → execute → repay).

    WARNING: THIS PERFORMS REAL TRANSACTIONS!
    Only run with real wallet if you understand the implications.
    """
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Full Credit Circuit")
    print("=" * 60)

    PRIVATE_KEY = os.getenv("PRIVATE_KEY")

    if not PRIVATE_KEY:
        print("⚠️  PRIVATE_KEY not set - using mock mode")
        task_mode = "mock"
    else:
        task_mode = "real"
        print("🔴 LIVE MODE: This will perform real on-chain transactions!")
        response = input("   Type 'yes' to continue, or press Enter to skip: ")
        if response.lower() != "yes":
            print("   Skipped.")
            return

    # Define a task that uses credit
    task = """
    You are an autonomous budget agent. Your mission:

    1. Check how much credit you have
    2. You need $200 USDC (estimate that an API call will cost $0.10)
    3. If you don't have enough, borrow $200 at up to 12% APR
      - Use 110% collateral amount (if needed)
    4. Pretend you executed the task (e.g., called an x402 API)
    5. Repay the loan fully to minimize interest

    Report at the end:
    - Did you borrow? (yes/no)
    - Loan ID if yes
    - Did you repay? (yes/no)
    - Total USDC flow
    """

    print("Running full circuit task...")
    if task_mode == "real":
        try:
            from coinbase_agentkit.wallet_providers import EvmWalletProvider
            wallet_provider = EvmWalletProvider.from_private_key(
                private_key=PRIVATE_KEY,
                rpc_url=os.getenv("BASE_RPC_URL", "https://mainnet.base.org"),
                network_id="base-mainnet"
            )
            result = await run_task(task, wallet_provider=wallet_provider)
        except Exception as e:
            print(f"Error: {str(e)}")
            return
    else:
        result = await run_task(task, wallet_provider=None)

    print(f"\nAgent Result:")
    print(result["output"] if result["success"] else f"Error: {result['error']}")


async def main():
    """Run all examples."""
    print("\n🚀 Floe Budget Agent Examples")
    print("=" * 60)

    # Example 1: Mock wallet (always works)
    await example_with_mock_wallet()

    # Example 2: Real wallet (requires credentials)
    await example_with_private_key_wallet()

    # Example 3: Full circuit (optional - requires real wallet + funds)
    # await example_full_credit_circuit()

    print("\n" + "=" * 60)
    print("✅ Examples complete!")
    print("\nNext steps:")
    print("1. Review INTEGRATION_GUIDE.md for full documentation")
    print("2. Fund your wallet on Base mainnet")
    print("3. Set PRIVATE_KEY in .env to run real transactions")
    print("4. Adjust MAX_SINGLE_BORROW_USDC and MAX_APR_ACCEPTABLE as needed")


if __name__ == "__main__":
    asyncio.run(main())
