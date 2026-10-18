# Archived legacy Visa pay-link integration

Visa is active again through the new guarded Care Settlement Router. This
directory preserves only the retired pay-link implementation; active code lives
in `core/app/visa.py` and `fetch.ai/settlement_router.py`.

This directory preserves the earlier mock/sandbox scaffolding for possible future research:

- `payment_guard_agent.py` — former Fetch.ai Payment Guard agent
- `visa_service.py` — former mock pay-link service and sandbox placeholder
- `check_xpay.py` — credential connectivity checker
- `agent_readme.md` — former Agentverse profile copy

The active workflow does not import these legacy modules. Production activation
still requires Visa wallet/Visa Direct onboarding, certified payloads, signed
status callbacks and a security review.
