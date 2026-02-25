# Access Control

Bayanat has a built-in feature to control access to Actors, Bulletins, and Incidents. Administrators can create roles/groups, add users to groups, and assign items to groups.

## Default Behavior

All items are unrestricted and accessible by all active users. Items only become restricted when explicitly assigned to a group by an administrator.

## How It Works

1. **Create groups**: Administrator creates Roles/Groups in user management
2. **Assign users to groups**: Users can belong to multiple groups
3. **Restrict items**: Assign items to one or more groups

Once restricted, only users who belong to at least one of the item's assigned groups can view or edit it. Other users see restricted items as blurred entries in data tables. Attempting to open a restricted item shows a restriction message.

## Restricting Items

### During Import

Media and Sheet Import tools provide the option to assign imported items to groups during the import process. This is useful for bulk imports of sensitive data.

### Existing Items

Select items in the data table and use the bulk update tool to assign groups. See [Bulk Operations](/guide/bulk-operations) for details.

### Individual Items

Edit any item and set its access groups in the access control section.

## Permissions

- Only administrators can create and manage groups
- Only administrators can assign or change access restrictions
- Moderators cannot modify access roles (the option is hidden)
- Users see only the items they have access to in search results and data tables
