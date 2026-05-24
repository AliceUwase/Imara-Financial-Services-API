# ADR-001: Bounded Django Apps for Domain Separation

## Decision Title

Structure the Imara MVP codebase as multiple bounded Django apps along
domain concept lines, rather than placing all models, serializers, and
views inside a single application.

## Context

Imara is preparing an MVP for merchant onboarding and financing requests.
The system must work reliably for users on unstable mobile data, and the
engineering team has explicitly asked for an API design that can survive
later security, testing, and deployment work rather than a rushed
prototype.

Three stakeholders’ pressures have influenced this decision. `Amina` wants
maintainable resource boundaries and clean service design. David wants
visible product progress and rapid onboarding. `Peter` wants lightweight
responses that work well in low-bandwidth contexts. With “Bounded Django Apps”,
The codebase structure most directly affects Amina's and David's concerns.
Peter's needs are addressed through complementary decisions on payload
shape and pagination.

## Options Considered

Before reaching my final verdict, these 3 approaches were also evaluated:

- **Single-app monolith.** All models, serializers, and views inside one
  Django application (e.g., `core`). I read it’s comparably faster during development, and it’s convenient for small projects.
- **Domain-driven microservices.** Separate Python services for
  merchants and financing, communicating over HTTP. Stronger boundaries than apps, but it is much harder to build, test, deploy, and keep running safely. 
- **Bounded Django apps.** Multiple Django apps within one project, each
  owning a single-domain concept with a shared `common` app that keeps code tidy and organized, without the massive headache of managing multiple servers and networks. 

## Chosen Option

Bounded Django apps. The codebase is split into three applications —
`merchants`, `financing`, and `common`. Each domain app owns one
concept; `common` holds shared utilities like error envelope handler,
cursor pagination class, role-based permission classes. Cross-app
foreign keys use string references to keep dependency direction
explicit and prevent circular imports.

## Why This Option

The codebase is easier to navigate and extend. New requirements have an
Standard home, changes stay local instead of being scattered through unrelated
code, and other developers can understand the system's shape from
the directory tree alone. 

The primary beneficiary is `Amina` , who, according to the given context, was concerned about maintainable
resource boundaries. Bounded apps give exactly that: domain concepts
are physically separated, ownership is clear, and the structure
makes it straightforward to later extract `financing` into its own
service if the system proceeds that way.

This decision primarily supports the **maintainability** and
**testability** non-functional requirements. Each app can evolve and be
tested independently, and any single change is
contained in one folder. Given that the brief explicitly asks for a
design that survives later security, testing, and deployment work,
maintainability is the right factor to optimise for at this stage.

The single-app monolith was rejected because the codebase could potentially grow
into a tangled mess within weeks, and this could work against the brief's
"survives later work" requirement. The microservices option
was rejected because the operational complexity exceeds the
MVP's needs.

## Trade-offs

The upfront cost is real. Developing multiple apps takes much longer than
one, and cross-app foreign keys must use string references
(`'merchants.Merchant'`) to avoid circular imports. Some concepts also
lack an obvious home. Like  `AlertAttempt` could be located in
`financing` or `common`,  and resolving those concerns slows down the development.

David loses his suggested `rapid onboarding`. This cost is recovered
as the cleaner structure makes subsequent endpoints faster
to add, but the early friction is worth addressing. 

The risk of over-splitting is contained by a single rule: code lives in
`common` only if at least two other apps would otherwise need to
import it from each other. 

## Deferred Work

The following decisions deliberately does not address:

- **A separate `lenders` app.** Lender behaviour is currently a role
  and a set of permissions on `FinancingRequest`, not a domain concept
  with its own data model. If lender profiles, lender registration,
  or lender-to-request matching logic emerges, this decision should
  be reconsidered.

- **Cross-app transaction boundaries.** Any future requirement for
  atomic operations spanning `merchants` and `financing` may surface
  the cost of the bounded-app. The current design assumes such
  cross-app transactions remain rare.

- **Service extraction.** The three apps currently share one Django project and one database. If a future scale or team-size pressure ever justifies splitting them into separate deployable services, the boundaries chosen here are intended to make that split easier, but the split itself is not in scope. 
