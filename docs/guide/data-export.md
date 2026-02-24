# Data Export

Export items from the database to multiple formats, optionally including related media files.

## Enabling

The tool must be enabled in the environment. See [Configuration](/deployment/configuration) for details.

## Permissions

- All administrators can make export requests
- Individual `Can Request Exports` permission can be granted to other users
- Only administrators can approve or reject requests

## Output Formats

|        | Actor | Bulletin | Incident |
| ------ | ----- | -------- | -------- |
| PDF    | Yes   | Yes      | Yes      |
| JSON   | Yes   | Yes      | Yes      |
| CSV    | Yes   | Yes      | No       |
| Media  | Yes   | Yes      | No       |

## Workflow

1. User selects items, chooses format, and optionally includes media
2. Request submitted for admin approval
3. Admin approves or rejects
4. Approved requests can be downloaded before expiry
5. Admin can change expiry time or expire immediately
6. Expired requests can no longer be downloaded and files are deleted
