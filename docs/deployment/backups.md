# Backups

## What to Backup

### PostgreSQL Database

Contains all data except media files.

```bash
pg_dump bayanat > bayanat_backup.sql
```

#### Automatic Backups (Built-in)

Bayanat has an automatic backup feature. See [Configuration](/deployment/configuration) for settings:

- `BACKUPS`: Enable/disable
- `BACKUP_INTERVAL`: Days between backups (e.g., `2` for every two days)
- `BACKUPS_LOCAL_PATH`: Storage path (default: `backups/`)
- S3 settings: `BACKUPS_S3_BUCKET`, `BACKUPS_AWS_ACCESS_KEY_ID`, `BACKUPS_AWS_SECRET_ACCESS_KEY`, `BACKUPS_AWS_REGION`

::: info
Built-in backups are not encrypted.
:::

#### Encrypted Backups via Crontab

For encrypted backups uploaded to S3, use a script with `aws-cli` and GPG:

1. Install `aws-cli`, run `aws configure`, import your GPG public key
2. Create a backup script (set `key` and `bucket` variables)
3. Add to crontab for daily 3am backups:

```bash
0 3 * * * /home/bayanat/backup.sh >> /home/bayanat/backup.log 2>&1
```

### Media Files

Main directory: `enferno/media/` (unless using S3).

Inline files (images in descriptions): `enferno/media/inline/` (stored locally even with S3).

### Environment File

The `.env` file contains TOTP secret and password salt. If lost, users cannot log in with existing passwords or 2FA.

### Configuration File

`config.json` contains all Bayanat settings. If lost, settings reset to defaults.

### Export Files

Temporary, stored in `enferno/exports/`. Deleted when exports expire.

### Import Files

Temporary, stored in `enferno/imports/`. Moved to `enferno/media/` or S3 after processing.
