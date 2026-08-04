# Setup Wizard

The first time you open a fresh Bayanat installation, it redirects to a setup wizard that walks you through initial configuration in the browser. The wizard runs once: after you complete it, Bayanat goes to the normal login and the wizard is no longer shown.

## Before the Wizard

The wizard configures the application, but the database must exist first. After installing Bayanat (see [Installation](/deployment/installation)), create the database schema, then open the site in a browser to start the wizard.

```bash
flask create-db --create-exts
flask db stamp head
```

Until setup is complete, any page you visit redirects to the wizard.

## What the Wizard Covers

The wizard collects the essentials to get a working instance. The main steps are:

- **First admin user** — create the initial administrator account (username and password). This is the account you will log in with.
- **Language** — the default interface language for the system. Users can change their own later.
- **Default data** — optionally import Bayanat's built-in reference lists (violation types, event types, countries, and similar). You can skip this and add data later.
- **Location** — set the default map center and administrative division names for your context.
- **Storage** — choose where uploaded media is stored: the local filesystem or S3-compatible object storage.
- **Security** — password policy and whether two-factor authentication is required (see [Account Security](/guide/account-security)).
- **Access control** — whether new items are visible to everyone by default or restricted (see [Access Control](/guide/access-control)).
- **Tools** — enable optional features such as media import, spreadsheet import, and data export.
- **Retention** — how long activity logs, exports, and sessions are kept.

Most steps come with sensible defaults, so you can move through quickly and refine settings later.

## After Setup

Everything chosen in the wizard is saved to the application configuration and can be changed afterwards under **System Administration**. The wizard does not need to be run again.

::: tip Command-line alternative
The wizard is the recommended path for new installations, but the same setup can be done from the command line (`flask install` to create the first admin, `flask import-data` to load default data). This is handy for scripted or headless deployments.
:::
