
## Decision I: Authentication Strategy

Using 2 login methods matched to who is connecting.

> Internal staff will be using the dashboard log in with `session-based authentication`, the cookie based login Django provides, where the server remembers that you're already logged in.

> Merchants and lender-partner systems consuming the API will be using `token-based authentication`, the API will be giving each consumer a token, which they send with every request instead of re-typing a password.

## Risk Addressed

It resolves the identity control problem, they were weak. No clear and secure way to prove who is making a request. So this closes this gap. The staff get a login session with proper logout and an additional built-in protection against cross-site request forgery.
The API consumers will present a valid token or they'll be deined access. It deliberately handles only `authentication` and `authorization` to the next decision. 

## Alternatives Considered

Full `OAuth 2.0 / delegated identity` was considered as i was exploring different auth strategies for this scenario. It's industry-standard and well recognized in fintechs, however, it meant a near-rewrite and more time to fully understand how it works for me to actually use it.
JWTs was also considered, but i read that they're harder to cancel once issued, and it kind of conflicted the auditor's visibility needs.

## Trade-off

The built-in tokens we chose do not expire on their own, as they stay valid until deleted. I went with it because they're simple to implement and are `instantly revocable`, deleting a token ends that acces instantly. In this case, easy revocation serves the `compliance` more than automatic expiry would.

## Deferred Work

Automatic token expiry and refresh, multi-factor authentication for staff, and any future move to OAuth 2.0 or single sign-on are left for later hardening.


## Decision II: Role and Access-Boundary Model

Using RBAC, each user has a role, and that role decides what actions they may take, which is strengthened with `object-level` checks (data-aware access) on top of the role, the system filters results so that a user only sees specific records that belong to them.
This roles also map directly with the case actors who are the merchant, lendeing-partner, compliance/admin, and support staff.
## Risk Addressed

Access boundaries were not clear, and this means that sensitive financial records were potentially accessible by the wrong people. What this decision solves in the over-board access in 2 layers. A `role gate` decides whether you may use an endpoint or not, and a `per-record filter` (only see your own) ensures a merchant cannot see another merchant's data and a lender only sees the requests they're entitled to. Compliance can read across every thing and support sees a limited slice too. 

## Alternatives Considered

`ABAC (Attribte-bassed access control)` was definetely considered in this scenario. Access decided by weighing many attributes and conditions (organisation, record status, time of day) against written policies. admit it's more flexible but it's another part to build and test, which is overkill for the 4 actors and i didn't feel confident to prove correct within the scope i have.
`Plain role labels with no record-level filtering` was also explored, but it's against what the brief was looking for becuase it doesn't give a solution to "can this user see this record".

## Trade-off

RBAC is detailed than ABAC. Dynamic, context-driven rules, for eaxample, access only during business hours or based on a fraud-risk core, this can't be expressed without code changes. I went with this, because the case needs none of them. its access rules are about role, and ownership. RBAC with record filtering handles this well.

## Deferred Work

A full attribute-based policy engine and any context-based rules (time, location, risk scoring) are deferred. If actor types multiply or rules become conditional, ABAC can be revisited.


## Decision III: Privacy and Auditability Approach

Adding `audit logging for sensitive-record access`. This is a separate log table that records who accessed which record, what they did, and when, including reads and not just changes along `privacy-safe logging`, where the only stores references (record ID, userID, action) excluuding the sensitive content or personal data.
And with that, move `secrets` (the app's keys and db password) the `.env` file.

## Risk Addressed

The core auditor compliant has no visibily into who can view financial records and who can't. The `access log` address this, every view or export of a sensitive record leaves a trail, which is the provable visibility complaince is requesting.

## Alternatives Considered

I looked into `managed secret manager` , a dedicated service like AWS secret manager for storing secrets, but didn't go ahead with it, as it's more complex and adds  infrastructure and setup. Environment variables felt like far less work and gets most of the benefit
## Trade-off

Writing an audit record on every sensitive read might add a small amount of work per request. But it's beneficial because of some users on slow mobile connection, and provides the visibility.

## Deferred Work

A managed secret manager, encryption of stored data at rest, tamper-proof (append-only) storage with a retention policy for the audit log were defered fo future stages.

### How these decisions resolve the stakeholdr tensions

***David (low friction, growth)***:  token access keeps API consumers smooth, and the security layers sit underneath without adding steps for everyday users.

**Neema (provable compliance)**: RBAC with record-level filtering provides role separation, and the audit log gives a provable record of who accesed sensitive data.

***Amina (no rewrite)***: every choice is going to be a retrofit and built on existing features, session login, built-in tokens, permission filtering, a single log table, and environment variables, rather than rewriting.
