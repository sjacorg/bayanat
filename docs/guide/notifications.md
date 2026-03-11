# Notifications

Bayanat notifies users about important events through in-app notifications and optional email delivery.

## Notification Categories

### Security (always enabled)

Administrators are automatically notified of security-related events:

- Password changes
- Two-factor authentication changes
- New user registrations
- Login from a new IP address or country
- Unauthorized access attempts
- Item deletions
- Credential changes

These notifications cannot be disabled.

### Updates (configurable)

Configurable notifications for operational events:

- Bulk operation completion
- Export request approved
- Data import status changes
- Web import status changes
- Batch processing status

### Assignments

Users receive notifications when:

- They are assigned to an item
- An item they're assigned to needs peer review

## Delivery

- **In-app**: All notifications appear in the notification panel with unread count and urgency indicators
- **Email**: Optional, sent asynchronously. Requires email to be configured and enabled per notification type

## Managing Notifications

Users can:

- View paginated notification history
- Mark individual notifications as read
- Mark all notifications as read
- Filter by category (Security, Update, Announcement)

## Configuration

Notification events can be configured in `config.json` under the `NOTIFICATIONS` section. Each event type can have in-app and email delivery independently enabled or disabled.
