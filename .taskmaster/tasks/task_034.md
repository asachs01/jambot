# Task ID: 34

**Title:** Implement Credit Management System

**Status:** cancelled

**Dependencies:** 32 ✗

**Priority:** high

**Description:** Build atomic credit deduction, addition, and balance query functions with transaction logging.

**Details:**

In `src/credits.py`: async def get_balance(tenant_id): query credits.balance - trial_used. async def deduct_credit(tenant_id, gen_id): WITH transaction: check balance>0, UPDATE credits SET balance-=1, trial_used+=1 if trial, INSERT credit_transactions(type='usage', amount=-1, balance_after=new_balance, generation_id=gen_id). async def add_credits(tenant_id, amount, stripe_id): UPDATE credits lifetime_purchased+=amount, balance+=amount, INSERT transaction(type='purchase'). Use async SQLAlchemy sessions.

**Test Strategy:**

Test atomicity (deduct/add concurrent), trial limits (max 5), balance queries accurate, all changes logged in transactions table, rollback on failure.
