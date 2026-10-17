# Billo vs. Past Sponsor Winners

This file compares Billo with past winners of each sponsor track. Then four "judge" agents argued about what Billo should keep, change, or cut. At the end, we pick one final structure that gives each track what it needs without breaking the others.

Some sources could not be opened fully. GitHub file trees were blocked, so the agents read the READMEs from raw GitHub files. The LifeLink, Wavelength, messenger-ai and do-eve Devpost pages came back empty, so they are only partly covered.

---

## 1. What the winners have in common

| Track | Winners we studied | What made them win |
|---|---|---|
| Photon | News Next Door, Wavelength | One simple process. You start on the web and scan a QR code, then everything after that happens in iMessage. The bot texts you first. The demo uses a real phone. They support private chats (DMs) only. |
| Sentry | Canary, ChatGPU (HTN) | Sentry is **inside the product**. An agent reads Sentry traces or alerts and then acts on them (fixes a bug, retries a job). Sentry is not just a dashboard for humans. |
| Fetch.ai | Quorum, Fetch-Health, Vanguard Telematics | One front door on ASI:One, a small number of agents that clearly do real work, and live ASI:One chat links as proof. Quorum won with validators plus a consensus step. |
| Visa | Kasha, Veritas, Visa Verify | A clear **trust** story and a clean demo: one checkout, a risk check, a verification step, a result on screen. Most did not move real money. |

**The big lesson:** winners go deep on one clear loop. They do not win by counting features.

---

## 2. The fight: where the judges disagreed

| Conflict | Who wanted what | Final decision |
|---|---|---|
| Where does the demo start? | Photon: run the whole story in iMessage. Fetch: ASI:One must run the full flow. | **Both doors run the full flow.** The demo starts in ASI:One (Fetch). Billo's answer ends with a case link that shows a **QR code**. Maya scans it, and the same case continues in iMessage (Photon). |
| iMessage Gateway Agent | Fetch: cut it from the main flow. Photon: keep iMessage fast. | **Keep it, but as a thin adapter**, not a thinking agent. ASI:One never needs it. Show typing dots, and keep the first reply under 5 seconds. |
| How many agents? | Fetch: 4–5. Earlier Billo plan: 8 + Billing Caller. | **5 public agents** on Agentverse, plus 2 small helpers. The Visit Agent moves into the Coordinator. Charity-Care moves into the Bill Auditor. |
| Calendar and the 30-minute "Did you go?" check | Fetch: no judge will see it. Photon: "Billo texts first" is what wins. Sentry: a good reason to use Crons. | **Keep it, but small:** one timed job inside the Coordinator, watched by Sentry Crons. It is not a separate agent. |
| Place View (satellite, street, indoor photos) | Fetch: cut. Kacy: wants it. | **Keep one picture per place card** (satellite or Street View). Indoor photos are a stretch goal. |
| Deposit hold at booking | Visa: cut, too complex. Fetch: mock it. | **Cut from the core.** Mention it on the Roadmap slide. The core payment is paying a bill fairly. |
| Family group chats | Photon: cut. Medical bills in a group chat are a privacy risk. | **Updated:** groups get **before care only**, and only when someone writes @Billo (places, prices, pictures, "Call 911"). Bills, payments and approvals stay in private chats, so the privacy worry is answered. |
| ElevenLabs voice | Photon: cut, off-track. | **Optional add-on**, built last and only if time is left. Not in the core flow. |
| Sentry depth | Sentry: 6 products is not a story. | **Add "Case Medic"**: a Sentry alert wakes an agent that reads the trace and fixes the case. Cut Profiling. |
| Visa trust angle | Visa: add "verify before you pay". | **Add it to the Payment Guard:** check the hospital's NPI, the payment link domain, and the amount before any money moves. |
| Bill audit trust | Fetch: add a Quorum-style verifier. | **Add a two-check vote:** a rules check and a price check. A flag goes into the dispute letter only when both agree. |

---

## 3. The final Billo structure

### Front doors (same agents behind both)

1. **ASI:One (Fetch.ai).** The full flow works here: symptoms, places and prices, bill audit, payment request.
2. **iMessage (Photon).** You join with the **QR follow code** (the News Next Door method). Private chats get everything; group chats get before care only, with @Billo.

### QR follow code (from News Next Door)

1. Billo's case page asks the server for a code like `BILLO-4821`. The code lasts 15 minutes and is tied to one case.
2. The server builds a link `sms:<Billo line>&body=BILLO-4821` and turns it into a QR image with the `qrcode` npm package.
3. The page shows the QR and an "Open in iMessage" button. It checks `GET /api/link/:code` every few seconds (waiting, linked, stopped, expired).
4. Maya scans the QR and taps Send. The bridge sees the code and links this iMessage chat to her case. The page flips to "Linked" only after the server has processed her text.
5. The inbound handler treats the code, STOP and HELP the same way every time (idempotent per message id), so a resent code does not send a second hello.
6. The same code can be printed on a discharge sheet: "Text this to check your bill." This lets a patient who never used Billo before start with just a bill.

### Agents (5 public on Agentverse, 2 helpers)

| # | Agent | Job |
|---|---|---|
| 1 | Billo Coordinator | Front door for ASI:One. Plans the case. Also runs booking, the calendar file and the 30-minute "Did you go?" check. |
| 2 | Red-Flag Screener | Safety rules first. If it might be an emergency, says "Go to the ER now" and stops. |
| 3 | Care Finder | Places near you, real prices from Tiger Data, and one picture per place. |
| 4 | Bill Auditor + Verifier | Reads the bill. Two checks vote on each flag (rules check and price check). Adds charity-care eligibility and the $400 Good Faith Estimate check. |
| 5 | Payment Guard | Signed limits. Verifies the hospital before paying. Pays only the fair part. Never pays a disputed amount. |
| helper | iMessage Gateway | Thin adapter between the Photon bridge and the Coordinator. |
| helper | Case Medic (Sentry) | Wakes on a Sentry alert, reads the trace, and picks one of three fixed actions. |

### Visa (simple and real)

States: **Mandate signed → Hospital verified → Fair part paid → Disputed part held back → Closed.**

- One real sandbox payment, live on stage (pay-by-link from the Visa Acceptance Agent Toolkit, then a webhook updates the case).
- The Guard's refusals are shown on screen: a wrong hospital and an over-limit amount are blocked, with reasons.
- Cut from the core: the deposit hold, the 0% monthly plan, refunds. Anything mocked is clearly labeled "mocked".

### Sentry (inside the loop)

- Keep: 1 case = 1 trace across all agents, AI monitoring for the bill reader, Logs tagged with `rule_id`, Crons on the 30-minute check, Uptime.
- Add **Case Medic**: a Sentry alert webhook (for example "bill reader invalid JSON above 5%" or "NPI lookup failing") wakes the agent. It pulls the trace through Sentry's API and picks one action:
  1. Retry the bill reader with a stricter schema or a backup model.
  2. Mark the NPI result "unverified" and continue with cached data.
  3. Pause the Payment Guard on that case.

  Then it texts the patient ("One check is slow. I am re-checking.") and writes what it did back onto the same trace.
- Change: use a keyed hash (HMAC) for case IDs. Show one scrubbed event in the demo.
- Cut: Profiling. Remove any made-up numbers; show only measured ones.

### Tiger Data [MLH] (no change)

It stays the memory of the system. The price check in the Bill Auditor's vote uses Tiger Data percentiles.

---

## 4. Demo plan (3 to 5 minutes; see the README demo story for the final version)

1. **ASI:One (Fetch):** Maya asks about her knee pain. The Red-Flag Screener clears it. The Care Finder shows 3 places with prices and a picture. She books one.
2. **QR (Photon):** Billo's answer links to her case page. She scans the QR on a real iPhone, and the page flips to "Linked".
3. **iMessage (Photon):** 30 minutes later Billo texts first: "Did you go to your visit today?" Then she sends a photo of her bill.
4. **Audit:** The Bill Auditor finds 3 flags. The verifier **rejects one false flag on screen**. Two flags go into the dispute letter.
5. **Sentry:** We break the NPI lookup live. Case Medic heals the case, and Maya gets a calm text.
6. **Visa:** Maya taps Approve. The Payment Guard verifies the hospital, pays only the fair part in the sandbox, and holds back the disputed part. The case page updates from the webhook.
7. **STOP:** She texts STOP, and the queued reminders are cancelled.

---

## 5. What each track judge will see

| Track | The one thing they will remember |
|---|---|
| Fetch.ai | The full flow runs on ASI:One across 5 real agents, with a verifier that rejects a false flag. |
| Photon | QR to iMessage on a real phone, Billo texts first, and STOP works live. |
| Sentry | A live failure that the product heals by itself using Sentry data. |
| Visa | A real sandbox payment that pays only the fair part, after a visible trust check. |
| Tiger Data | Real price percentiles that decide which flags are fair. |
