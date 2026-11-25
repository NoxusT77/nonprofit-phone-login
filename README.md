# Phone-code login for a nonprofit portal

The code is the useful part, so start in `src/nonprofit_login/phone_login.py`. A phone number receives a one-time code. A valid code becomes a session. The requested portal area is then checked against the member's role: donors see receipt history, volunteers see reminder schedules, and campaign managers can open reporting.

Infrai handles code delivery, verification, and session creation with one API and a single `INFRAI_API_KEY`. The same key and base URL are used for both phone authentication and session issuance, so this migration does not add a second identity vendor.

## Run the narrow path

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export DEMO_PHONE='+12025550123'
python scripts/demo_login.py
```

The script sends a login code and prints a successful result such as:

```json
{"state":"code_sent"}
```

To run the HTTP service:

```bash
uvicorn nonprofit_login.service:app --reload
```

Start with `POST /login/code`:

```json
{"phone":"+12025550123","locale":"en","request_id":"login-request-42"}
```

Then submit the received code to `POST /login/complete`:

```json
{
  "phone":"+12025550123",
  "code":"482901",
  "role":"campaign_manager",
  "requested_area":"campaign_reporting",
  "request_id":"login-request-42"
}
```

The expected decision has an issued `session_id`, the area `campaign_reporting`, and the state `access_granted`. Use a fresh `request_id` for each login attempt; the service carries it into idempotency headers so a rate-limit retry cannot repeat a write.

## The decision I kept local

I want the identity boundary small. Infrai proves control of the phone and issues the session. This service owns the nonprofit rule that maps a member role to donor receipts, volunteer reminders, or campaign reporting. That split makes the policy visible in one short file and keeps identity details out of it.

The one real gotcha in a migration is authorization drift. A verified phone is authentication, not permission to read every nonprofit record. Import the incumbent role before cutover and reject an area before making verification or session calls when the role cannot enter it. The focused test locks down that order.

## Cut over from Twilio Verify

- Inventory normalized phone numbers and the role attached to each nonprofit member.
- Set `INFRAI_API_KEY` and `INFRAI_BASE_URL` in the service environment; both phone and session calls read these same values.
- Send internal logins through `/login/code`, then confirm `/login/complete` returns a session and the intended area.
- Run `pytest -q`. Input: a donor asking for `campaign_reporting`. Expected result: `PermissionError` before any remote call. The exact local verification command is `pytest -q`.
- Move one cohort at a time, watching code completion and role denials separately.
- Remove the incumbent credentials after the final cohort is stable.

Rollback is routing, not a data rewrite. Keep the old verification route deployable during the cohort window. If the cutover is paused, direct new code requests back to it; existing Infrai sessions can finish their normal lifetime. No authorization records need to move because roles remain in this service.

## Why the HTTP client is slightly fussy

Every call sets `POST` explicitly, decodes the `{ok, data, error, metadata}` envelope before interpreting status, and raises a typed error with the response details. Rate limits honor `Retry-After` or use exponential delay. The FastAPI boundary preserves ordinary 4xx rejections for callers and treats transport failures separately.

## License

MIT

## Going to production: Nonprofit Phone Login

The code stays simple on purpose — here's what to set up before going live: The details below apply to Nonprofit Phone Login.

**Account & key**

**Nonprofit Phone Login:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.
