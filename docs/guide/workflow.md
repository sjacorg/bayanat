# Workflow

SJAC's analysts follow a strict workflow for the analysis of Actors and Bulletins. The workflow is enforced in Bayanat's UI and can only be overridden by an administrator.

This workflow serves as a project management tool within Bayanat. It allows users to filter data by status and provides insights into team progress.

SJAC's workflow and statuses are shipped by default, but other users can add, remove, or modify statuses.

## Statuses

- Machine Created
- Human Created
- Assigned
- Updated
- Peer Review Assigned
- Peer Reviewed
- Revisited
- Senior Updated
- Senior Reviewed
- Machine Updated
- Finalized

## Process

### Initial Status

When an Actor/Bulletin/Incident is created, it gets either `Human Created` or `Machine Created` status, depending on whether it was created by a user or automatically imported.

### Analysis

The main part of the workflow. Items are transformed from raw condition to a processed state.

Administrators or Moderators assign items to analysts, changing status to `Assigned`. The assignee finds items via the "Assigned to me" shortcut. After processing, status changes to `Updated`. Items can be updated as many times as required.

### Review

Peer review is essential for quality control and learning.

Administrators or Moderators assign processed items to other analysts for review using `Peer Review Assigned`. The original assignee can't update the item until reviewed.

Reviewers examine all fields, comparing data with the source. They leave comments without changing data. After review, status becomes `Peer Reviewed`, with an indication of whether issues were found.

If issues exist, the assignee corrects them, changing status to `Revisited`.

### Senior Actions

Administrators can change all items. Convention is to use `Senior Updated` or `Senior Reviewed`.

### Machine Actions

`Machine Updated` is reserved for automatic actions by scripts or tools.
