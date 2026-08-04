# Account Security

Bayanat protects accounts with passwords, optional two-factor authentication, passkeys and hardware security keys, and optional single sign-on. Each user manages their own security from the **Account Security** page (available from the user menu); administrators set the policies that apply to everyone.

## Two-Factor Authentication (2FA)

Two-factor authentication adds a one-time code from an authenticator app on top of your password.

To enrol, open **Account Security → Authentication Methods**, start 2FA setup, and scan the displayed QR code with an authenticator app (such as Google Authenticator or Authy). Enter the 6-digit code to confirm. After that, each login asks for a current code from the app.

**Recovery codes** are generated when you enrol. Save them somewhere safe; each code can be used once to sign in if you lose access to your authenticator app.

::: tip Administrators can require 2FA
An administrator can enforce 2FA for everyone via the "Enforce 2FA User Enrollment" setting. When enabled, users are prompted to enrol before they can continue using Bayanat.
:::

## Passkeys and Security Keys

Bayanat supports WebAuthn passkeys and hardware security keys (such as YubiKey, or a device fingerprint/face unlock) as a second factor. They are used after your password, not as a passwordless replacement.

Register one under **Account Security → Authentication Methods**: give the device a name, then follow your browser's prompt to confirm with the key, fingerprint, or face scan. You can register several devices and remove them individually.

## Single Sign-On with Google

If enabled, the login page shows a **Sign in with Google** button. Signing in this way matches your Google account to an existing Bayanat user by email address.

Accounts are not created automatically: an administrator must create the Bayanat user first, otherwise sign-in is refused. Administrators can also restrict sign-in to a specific email domain. Single sign-on is configured by an administrator; see [Configuration](/deployment/configuration).

## Passwords

Administrators set the password policy:

- A **minimum length** (10 characters by default).
- A **strength requirement**, checked as you type, that rejects weak or easily guessed passwords.

Change your password anytime under **Account Security → Change Password**. If your account was created for single sign-on and has no password yet, setting one here adds it.

## Login Protection

To slow down automated guessing, administrators can enable a CAPTCHA challenge that appears on the login form after repeated failed attempts.

## Sessions

- **One active session** (default): logging in on a new device or browser signs you out everywhere else, so only one session is active at a time.
- **Re-authentication for sensitive actions**: after a period of inactivity, Bayanat asks you to confirm your password again before changing security settings.
- Old session records are cleaned up automatically after an administrator-defined retention period.

## What You Can Manage Yourself

From **Account Security**, every user can:

- Change their password
- Enrol or remove two-factor authentication
- Register or remove passkeys and security keys
- Generate and view recovery codes
