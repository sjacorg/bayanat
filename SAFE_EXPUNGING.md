# Safe Expunging Process

This document describes when and how history-altering operations are permitted on the Bayanat source repository, satisfying the SLSA v1.2 Source track "Safe Expunging Process" requirement.

## Scope

Applies to the public repository `sjacorg/bayanat` and the private release repository `sjacorg/bayanat.prod`, specifically to operations that remove or rewrite committed history on protected references (`main`, release tags matching `v*`).

## Default

History on protected references is append-only. Force-push, branch deletion, tag deletion, and retagging are blocked by repository rulesets.

## Permitted Reasons to Expunge

Expunging may be approved only for one of the following reasons:

1. **Secret leak.** An unredacted credential, private key, or access token was committed.
2. **Personal data leak.** Non-public personal data of an identifiable individual was committed.
3. **Legal or safety order.** A verified order from counsel or a credible safety concern requires removal of specific content.
4. **Malicious injection.** Attacker-introduced code or data must be removed as part of incident response.

Bug fixes, style corrections, and cleanup are never valid reasons.

## Approval

Both maintainers must approve in writing, recorded in the security advisory created for the incident.

## Procedure

1. File a private security advisory at https://github.com/sjacorg/bayanat/security/advisories with the reason, affected commits, and proposed action.
2. Record both maintainer approvals in the advisory.
3. If the reason involves a secret, rotate it before rewriting.
4. Rewrite with `git filter-repo` (not `filter-branch`), preserving commit signatures where possible.
5. Temporarily bypass branch protection, force-update the protected reference, then re-enable protection.
6. Invalidate and regenerate any affected release tags. Old tags are not reused.

## Consumer Notification

After any expunging action, publish a public security advisory that includes:

- What was removed and why (redacted as needed).
- New commit hashes and release tags that replace the expunged revisions.
- Operator guidance (re-clone, re-verify signatures, check deployed commit against the new history).
