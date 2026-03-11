# Bulk Operations

Bayanat supports bulk actions on multiple items at once. Select items from any data table and apply changes in batch.

## Available Actions

| Action | Bulletins | Actors | Incidents |
| --- | --- | --- | --- |
| Change status | Yes | Yes | Yes |
| Assign/reassign user | Yes | Yes | Yes |
| Clear assignee | Yes | Yes | Yes |
| Assign first peer reviewer | Yes | No | No |
| Add/replace tags | Yes | Yes | Yes |
| Set access roles | Yes | Yes | Yes |
| Add comment | Yes | Yes | Yes |

## How It Works

1. Select items from the data table using checkboxes
2. Click the bulk update button
3. Choose the action and set the new value
4. Submit the update

Updates are processed asynchronously in the background. You receive a notification when the operation completes, including success and failure counts.

## Tag Modes

When updating tags in bulk, you can choose:

- **Append**: Add new tags while keeping existing ones
- **Replace**: Replace all existing tags with the new set

## Permissions

- Administrators and Moderators can perform bulk operations
- Only Administrators can modify access roles (this option is hidden for Moderators)
- Status changes follow the same workflow rules as individual updates
