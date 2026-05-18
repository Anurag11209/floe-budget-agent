# Floe Budget Agent - Setup & Integration Guide

## Architecture Overview

The Floe Budget Agent manages autonomous USDC credit lines on **Base mainnet**. Unlike traditional REST APIs, Floe operates through **on-chain smart contracts**. All credit operations (borrow, repay, x402 calls) are blockchain transactions.

### Key Components

1. **FloeClient** - Wraps the official Floe Python SDK (`floe-agentkit-actions`)
2. **BudgetEngine** - Deterministic financial decision layer (prevents reckless spending)
3. **LangChain Tools** - Agent tools for check_credit_status, estimate_x402_cost, post_borrow_intent, repay_credit
4. **Wallet Provider** - Handles private key management & on-chain signing (required)

---

## Step 1: Install Dependencies

```bash
# Core dependencies
pip install floe-agentkit-actions
pip install coinbase-agentkit
pip install langchain langgraph langchain-groq
pip install httpx structlog python-dotenv
```

---

## Step 2: Configure Environment

Update `.env` with your credentials:

```env
# Groq LLM
GROQ_API_KEY=gsk_...

# Floe (optional - mainly for heath checks)
FLOE_API_KEY=floe_live_...
FLOE_BASE_URL=https://credit-api.floelabs.xyz
FLOE_MCP_URL=https://mcp.floelabs.xyz/mcp

# Wallet / On-chain
BASE_RPC_URL=https://mainnet.base.org
PRIVATE_KEY=0x...          # For testing (EvmWalletProvider)
# OR use CDP for production (CdpWalletProvider)

# Budget constraints
CREDIT_WARNING_THRESHOLD=0.20
CREDIT_MIN_RESERVE_USDC=5.0
MAX_SINGLE_BORROW_USDC=500.0
MAX_APR_ACCEPTABLE=0.15  # 15%
```

---

## Step 3: Initialize Wallet Provider

### Option A: Development (Private Key)

```python
from coinbase_agentkit.wallet_providers import EvmWalletProvider
import os

wallet_provider = EvmWalletProvider.from_private_key(
    private_key=os.getenv("PRIVATE_KEY"),
    rpc_url=os.getenv("BASE_RPC_URL"),
    network_id="base-mainnet"
)
```

### Option B: Production (Coinbase DevKit)

```python
from coinbase_agentkit import Wallet
from coinbase.wallet_address import WalletAddress

# Requires CDP API credentials
wallet = Wallet()
wallet_provider = wallet  # Use directly with Floe
```

---

## Step 4: Run the Agent

```python
from app.agent.orchestrator import run_task
import asyncio

# Define task
task = "Fetch the latest Bitcoin price and store it in the database"

# Run with wallet
wallet_provider = EvmWalletProvider.from_private_key(...)
result = await run_task(task, wallet_provider=wallet_provider)

print(result["output"])
```

---

## How It Works - The Full Circuit

### 1. Estimate Cost

Agent calls `estimate_x402_cost(endpoint_url)` to know upfront costs.

### 2. Check Balance

Agent calls `check_credit_status(loan_id)` to see available USDC.

### 3. Borrow if Needed

If balance insufficient:

```python
await post_borrow_intent(
    borrow_amount_usdc=100,      # Borrow $100
    collateral_amount_usdc=110,  # Lock $110 as collateral
    max_apr_bps=1200             # Max 12% APR
)
```

**Result**: On-chain transaction executes. Agent receives `loan_id` and USDC.

### 4. Execute Task

Agent uses USDC to pay for APIs, compute, data feeds, etc.

### 5. Repay

After task completion:

```python
await repay_credit(loan_id=loan_id)
```

**Result**: Loan repaid, collateral returned atomically in same transaction.

---

## Error Handling

### Wallet Not Set

If you forget to pass `wallet_provider=` to `run_task()`:

- ✓ `check_credit_status()` returns mock data (doesn't fail)
- ✗ `post_borrow_intent()` raises error (requires wallet)
- ✗ `repay_credit()` raises error (requires wallet)

**Fix**: Always pass wallet provider to `run_task()` or call `set_floe_wallet()` first.

### No Collateral

If you lack WETH or USDC to collateralize:

- `post_borrow_intent()` returns `{"success": False, "reason": "Insufficient collateral"}`

**Fix**: Fund your wallet on Base first.

### APR Too High

If interest rates exceed `MAX_APR_ACCEPTABLE`:

- `post_borrow_intent()` rejects the borrow
- BudgetEngine returns `{"success": False, "reason": "APR ... exceeds max acceptable"}`

**Fix**: Wait for rates to drop or raise `MAX_APR_ACCEPTABLE` in .env.

---

## Testing Without On-Chain (Mock Mode)

For testing without a real wallet:

```python
# Mock wallet - no on-chain operations
result = await run_task(task, wallet_provider=None)

# Returns:
# {
#   "success": True,
#   "output": "... agent reasoning ..."
# }
```

Check logs to see what _would_ happen:

```
check_credit_status: remaining_usdc=1000, limit_usdc=5000
post_borrow_intent: would borrow $100 (rejected: wallet_provider_not_set)
```

---

## API Reference

### check_credit_status

```python
await check_credit_status(loan_id: str = None) -> dict
```

Returns: `{remaining_usdc, limit_usdc, active_loan_id, is_healthy}`

### estimate_x402_cost

```python
await estimate_x402_cost(endpoint_url: str) -> dict
```

Returns: `{endpoint, estimated_usdc, currency}`

### post_borrow_intent

```python
await post_borrow_intent(
    borrow_amount_usdc: float,
    collateral_amount_usdc: float = None,
    max_apr_bps: int = 1200
) -> dict
```

Returns: `{success, loan_id, amount_usdc, collateral_usdc, apr_bps, reason}`

### repay_credit

```python
await repay_credit(loan_id: str = None, repay_amount_usdc: float = None) -> dict
```

Returns: `{success, loan_id, repaid_usdc, result}`

---

## Troubleshooting

**Q: `ImportError: No module named 'floe_agentkit_actions'`**

- A: Run `pip install floe-agentkit-actions`

**Q: Agent won't borrow - keeps saying "Insufficient credit"**

- A: Check `MAX_SINGLE_BORROW_USDC` in .env. Increase if needed.

**Q: On-chain transaction keeps failing**

- A:
  - Check wallet has USDC/WETH balance on Base mainnet
  - Verify `BASE_RPC_URL` is valid and responsive
  - Check gas prices aren't too high

**Q: Loan stays active after repayment**

- A: Repayment is async. Wait a few seconds, then call `check_credit_status()` again.

---

## Next Steps

1. **Fund wallet**: Send WETH/USDC to your Base wallet
2. **Get Floe credits**: Register at dev-dashboard.floelabs.xyz
3. **Run a test circuit**: Execute a task via the agent
4. **Monitor costs**: Check Floe dashboard for real-time spend tracking

Ready to go! 🚀
