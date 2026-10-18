# Billo Care Settlement Router

I route two opposite post-care money directions without storing card data.

- **Patient owes the clinic:** inspect a clinic-presented Visa/EMV QR, match its checksum, merchant, amount, currency and saved care record, then require explicit approval before wallet handoff.
- **Patient is owed reimbursement:** require a paid receipt, a named benefit path, external benefit approval and explicit patient approval before recording a simulated Visa Direct payout.

Every result is visibly simulated. Production money movement remains disabled until Visa wallet and Visa Direct onboarding are certified.
