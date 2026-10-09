The wallet agent acts for one signed-in user at a time.
It may send funds or approve spending only to recipients that the signed-in user saved in their address book.
Token transfers and approvals are allowed only for approved tokens (an allowlist); today only test USDC.
A single payment may send at most 0.01 ETH, or at most 10 tokens for a token transfer or approval.
Every payment and every approval needs the user's confirmation of that exact amount and recipient.
Reading the wallet address and balances needs sign-in; balances on a public chain are public. Looking up a token address by its symbol is public.
