# Permissions

Bayanat has a simple permissions system with standard and additional permissions.

## User Management

The user management dashboard allows administrators to add and modify users.

### User Fields

- **Name**: As it appears to other users
- **Email**: Username for login
- **Password**: Can be set/reset by admin
- **Role**: User group membership
- **Active**: Toggle to enable/disable access

### Additional Permissions

Three permissions that can be toggled per user:

- **View users' names**: When disabled, names are replaced with aliases (e.g., "user15"). Useful for external users.
- **View simple log**: Access to the list view of change history
- **View full history**: Access to the detailed diff view of change history

## Roles

### Read Only

Users without a group role. Can view items in Actors, Bulletins, and Incidents without editing. Useful for researchers or investigators.

### Data Analyst (DA)

Read and conditional write. Can view all items but only edit items assigned to them. Can review items assigned for peer review.

### Moderator (Mod)

Same as DA, plus read/write access to Labels, Sources, Event Types, and Locations. Can perform bulk updates.

### Administrator

Unrestricted access to all actions. Can view Activity Monitor and manage users.
