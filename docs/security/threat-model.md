# Threat Model

::: info
This threat model is current as of Bayanat v2.9.0.
:::

## Goal

- Recognize, measure, and manage security risks related to Bayanat
- Safeguard confidentiality, integrity, and availability of data
- Mitigate vulnerabilities to minimize potential risks

### Out of Scope

- Hosting infrastructure security (follow industry best practices, restrict access to port 443)
- Third-party component security (keep all components updated)
- DDoS protection (address separately)

## Threat Surfaces

### Evaluated

- Databases and storage
- Codebase (manual review, continuous static analysis via SemGrep and CodeQL)
- Configuration files
- Web UI (vulnerability assessment via Tenable Nessus)

### Not Evaluated (Out of Scope)

Hosting infrastructure, Nginx, Flask, Flask extensions, Vue/Vuetify, Redis, PostgreSQL, Celery, and third-party libraries.

## Access Control

### Roles

- **Data Analyst (DA)**: Read and conditional write on assigned items
- **Moderator**: DA permissions plus Labels, Sources, Event Types, Locations, and bulk updates
- **Administrator**: Unrestricted access, Activity Monitor, user management

### System Users

Following the official installation guide, the `www-data`/`nginx` user does not have direct access to PostgreSQL databases, limiting the impact of web server compromise.

## Authentication

Multi-factor authentication with:

- Recaptcha
- Google OAuth
- Hardware Keys (WebAuthn/FIDO, recommended)

## Trust Levels

1. Anonymous Web User
2. User with valid login credentials
3. Administrator
4. Data Analyst
5. Moderator
6. Root local user
7. Bayanat local user
8. Nginx local user
9. Postgres local user

## Implemented Security Controls

| Area | Control |
| --- | --- |
| Login | Minimum 8-character passwords |
| Login | Non-revealing failed login messages |
| Login | Activity logging for logins |
| Login | No password recovery via UI |
| Login | Password complexity enforcement |
| Login | 2FA via authenticator apps |
| Secrets | Random generation per Flask recommendations |
| Secrets | Critical secrets masked during transmission |
| Sessions | HTTP-only cookies |
| Sessions | CSRF tokens with rate limiting |
| Sessions | Admin-managed session tracking |
| Data | Activity logging for all CRUD operations |
| Data | Per-request authentication and authorization |
| Data | No direct DB access from www-data user |
| Data | Automatic export cleanup |
| Data | Enforced authentication for sensitive operations |
| Data | Input sanitization (Bleach) and validation (Pydantic) |
| Codebase | Continuous static analysis (SemGrep) |
| Codebase | Non-privileged dependency installation |
| Codebase | Dependency scanning (Dependabot) |

## Recommended Controls

| Control | Cost | Impact | Likelihood | Score |
| --- | --- | --- | --- | --- |
| Account lockout after failed attempts | 4 | 5 | 7 | 31 |
| Secrets Vault for third-party keys | 8 | 9 | 7 | 55 |
| Content Security Policy (CSP) | 8 | 7 | 8 | 48 |
| Clean up unused media imports | 5 | 7 | 3 | 16 |
| Full input sanitization | 8 | 9 | 9 | 73 |
| Restrict .env access to required users | 3 | 9 | 7 | 60 |
| Disable or protect Flask CLI | 5 | 8 | 3 | 19 |
| Server-side MIME type validation | 3 | 4 | 6 | 21 |
| Disable PUT/DELETE HTTP methods | 3 | 8 | 7 | 53 |
| POST for recovery codes endpoint | 1 | 6 | 6 | 35 |
| Disallow * on robots.txt | 1 | 2 | 8 | 15 |
| Validate uploaded JSON settings | 2 | 2 | 4 | 6 |

## Known Risks

| Risk | Impact | Probability | Score |
| --- | --- | --- | --- |
| .env accessible if any trust-level user is compromised | High | High | 9 |
