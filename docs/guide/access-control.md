# Access Control

Bayanat has a built-in feature to control access to Actors, Bulletins, and Incidents. Administrators can create roles/groups, add users to groups, and assign items to groups.

## Default Behavior

All items are unrestricted and accessible by all active users unless restricted by administrators.

## Restricting Imported Items

Media and Sheet Import tools provide the ability to assign imported items to groups during import.

## Restricting Existing Items

1. **Create groups**: Admin creates Roles/Groups in the system
2. **Assign users**: Add groups to users who need access (users can belong to multiple groups)
3. **Restrict items**: Select items in data tables and use bulk-update to assign groups

Restricted items appear blurry in the data table for unauthorized users. Attempting to access a restricted item shows a restriction message.
