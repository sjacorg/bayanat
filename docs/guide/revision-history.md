# Revision History

Bayanat logs every change made to Actors, Bulletins, and Incidents. The system provides two levels of detail, accessible based on user permissions.

## Simple History Log

Accessible in view mode at the bottom of each item. For every update, the log shows:

- The user who performed the update
- The time of the update
- The workflow status at that point
- The comment left by the user

This gives a quick timeline of who changed what and when, without needing to inspect the actual data changes.

## Advanced History Log (Diff View)

In addition to the simple log, the system takes a full snapshot of the item on each update. This enables side-by-side comparison of any two consecutive versions to see exactly what changed.

The diff view highlights:

- Added fields or values (new data)
- Removed fields or values (deleted data)
- Modified fields (before/after comparison)
- Changes to relationships (added/removed related items)
- Changes to access restrictions

## What Gets Tracked

All fields on the item are captured in each snapshot, including:

- Core fields (title, description, dates)
- Related entities (actors, bulletins, incidents)
- Labels, sources, events, and locations
- Access control group assignments
- Workflow status transitions
- Media attachments

## Permissions

- All users can see the simple history log for items they can access
- The advanced diff view requires additional permissions granted by an administrator
