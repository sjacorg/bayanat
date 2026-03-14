# Threat Model

::: info
This threat model was last reviewed for Bayanat v2.9.0.
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

## Assets Characterization

### Secrets and Keys

- Trust Level Access: 6, 7, 8
- Storage: Environment Variables
- Transmission: Terminal -> Env Var
- Execution Environment: Memory
- Input: Manual by user
- Output: None

### Users Login Credentials

- Trust Level Access: 2, 6, 7, 9
- Storage: Postgres DB
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database
- Execution Environment: Memory
- Input: Bayanat login page
- Output: None

### Bulletins Data

- Trust Level Access: 2, 3, 4, 5
- Storage: Postgres DB, Redis DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, Nginx -> Redis -> Database, User browser -> Nginx -> Celery -> Database, User browser -> Nginx -> Disk Storage
- Input: Bulletins Endpoint, Bulk Updates Endpoint, Media Uploads, Export Endpoint
- Output: Bulletins Endpoint, Export Endpoint

### Actors Data

- Trust Level Access: 2, 3, 4, 5
- Storage: Postgres DB, Redis DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, Nginx -> Redis -> Database, User browser -> Nginx -> Celery -> Database, User browser -> Nginx -> Disk Storage
- Input: Actors Endpoint, Bulk Updates Endpoint, Media Uploads, Export Endpoint
- Output: Actors Endpoint, Export Endpoint

### Incidents Data

- Trust Level Access: 2, 3, 4, 5
- Storage: Postgres DB, Redis DB
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, Nginx -> Redis -> Database, User browser -> Nginx -> Celery -> Database
- Input: Incident Endpoint, Bulk Updates Endpoint, Export Endpoint
- Output: Incident Endpoint, Export Endpoint

### Locations Data

- Trust Level Access: 2, 3, 4, 5
- Storage: Postgres DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, User browser -> Nginx -> Disk Storage
- Input: Locations Endpoint, User uploaded CSV file
- Output: Locations Endpoint

### Sources Data

- Trust Level Access: 3, 4, 5
- Storage: Postgres DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, User browser -> Nginx -> Disk Storage
- Input: Sources Endpoint, User uploaded CSV file
- Output: Sources Endpoint

### Labels Data

- Trust Level Access: 2, 3, 4, 5
- Storage: Postgres DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, User browser -> Nginx -> Disk Storage
- Input: Labels Endpoint, User uploaded CSV file
- Output: Labels Endpoint

### Activities Data

- Trust Level Access: 3
- Storage: Postgres DB
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database
- Input: None
- Output: Activities Log

### User Data

- Trust Level Access: 3
- Storage: Postgres DB, Redis DB
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, User browser -> Nginx -> Redis DB -> Database
- Input: User Management Endpoint
- Output: User Management Endpoint

### Roles Data

- Trust Level Access: 3
- Storage: Postgres DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, User browser -> Nginx -> Disk Storage
- Input: Roles Endpoint, User uploaded CSV file
- Output: Roles Endpoint

### Data Import

- Trust Level Access: 3, 6, 9
- Storage: Postgres DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database, User browser -> Nginx -> Celery -> Disk Storage
- Input: User's uploaded media files, User's uploaded CSV files
- Output: Import Log, Data Import Endpoint

### System Settings

- Trust Level Access: 2, 3, 4, 5
- Storage: Postgres DB, Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Database
- Input: Settings Endpoint
- Output: Settings Endpoint

### System Logs

- Trust Level Access: 3
- Storage: Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Postgres DB, User browser -> Nginx -> Disk Storage
- Input: Logs Endpoint
- Output: Logs Endpoint

### Setup Wizard

- Trust Level Access: 1
- Storage: Disk Storage
- Transmission: User browser -> Nginx -> SQLAlchemy -> Postgres DB, User browser -> Nginx -> Redis DB -> Database
- Input: Setup Wizard Endpoint
- Output: Setup Wizard Endpoint, User Login Endpoint, System Settings Endpoint

### Notifications

- Trust Level Access: 2, 6, 7, 9
- Storage: Disk Storage
- Transmission: Input Endpoint -> Notifications Endpoint -> SQLAlchemy -> Postgres DB
- Input: Celery, Login Endpoint, Users Endpoint, Roles Endpoint, Bulletins Endpoint, Actors Endpoint, Incidents Endpoint, Labels Endpoint, Locations Endpoint, Media Import Endpoint, Settings Endpoint
- Output: Notifications Endpoint

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

| Control | Asset | Description | Cost | Impact | Likelihood | Score |
| --- | --- | --- | --- | --- | --- | --- |
| Account lockout after failed attempts | Users Login Credentials | Prevents brute-force attacks by locking accounts after repeated failed login attempts | 4 | 5 | 7 | 31 |
| Secrets Vault for third-party keys | Secrets and Keys | Store third-party API keys and secrets in a dedicated vault instead of environment variables to reduce exposure | 8 | 9 | 7 | 55 |
| Content Security Policy (CSP) | Bulletins Data, Actors Data, Incidents Data | Implement CSP headers to prevent XSS attacks and unauthorized script execution in the browser | 8 | 7 | 8 | 48 |
| Clean up unused media imports | Data Import | Remove orphaned media files from failed or incomplete imports to reduce attack surface and disk usage | 5 | 7 | 3 | 16 |
| Full input sanitization | Bulletins Data, Actors Data, Incidents Data, Locations Data | Sanitize all user inputs across all endpoints to prevent injection attacks and data corruption | 8 | 9 | 9 | 73 |
| Restrict .env access to required users | Secrets and Keys | Limit file system permissions on .env to only the users that need access, preventing credential leakage if a lower-trust user is compromised | 3 | 9 | 7 | 60 |
| Disable or protect Flask CLI | System Settings, User Data | Restrict access to Flask CLI commands in production to prevent unauthorized database modifications or user creation | 5 | 8 | 3 | 19 |
| Server-side MIME type validation | Bulletins Data, Actors Data | Validate uploaded file MIME types on the server side to prevent malicious file uploads disguised with incorrect extensions | 3 | 4 | 6 | 21 |
| Disable PUT/DELETE HTTP methods | Bulletins Data, Actors Data, Incidents Data | Disable unused HTTP methods at the Nginx level to reduce the attack surface and enforce REST conventions | 3 | 8 | 7 | 53 |
| POST for recovery codes endpoint | Users Login Credentials | Use POST instead of GET for recovery codes to prevent tokens from appearing in server logs and browser history | 1 | 6 | 6 | 35 |
| Disallow * on robots.txt | System Settings | Configure robots.txt to disallow all paths, preventing search engines from indexing sensitive endpoints | 1 | 2 | 8 | 15 |
| Validate uploaded JSON settings | System Settings | Validate structure and content of uploaded JSON configuration files to prevent injection of malicious settings | 2 | 2 | 4 | 6 |

## Known Risks

| Risk | Impact | Probability | Score |
| --- | --- | --- | --- |
| .env accessible if any trust-level user is compromised | High | High | 9 |
