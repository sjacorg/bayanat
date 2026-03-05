# Dynamic Fields

Administrators can create custom fields on Bulletins, Actors, and Incidents to capture data beyond the built-in fields.

## Field Types

| Type | Description |
| --- | --- |
| Text | Short text input (configurable max length, default 255) |
| Long Text | Multi-line text area |
| Number | Integer input |
| Select | Single or multi-select dropdown with predefined options |
| DateTime | Date and time picker with timezone |

## Creating a Field

1. Go to the Dynamic Fields management page
2. Choose the target entity (Bulletin, Actor, or Incident)
3. Set the field name, type, and configuration
4. Configure display options (label, help text, width, sort order)
5. Optionally mark as searchable (for text fields) or required

Field names must be valid identifiers and cannot conflict with existing built-in field names.

## Configuration Options

- **Display**: Label, help text, width, sort order, visibility, read-only
- **Validation**: Required flag, regex patterns, min/max length
- **Search**: Text and Long Text fields can be marked searchable, which enables full-text search indexing
- **Select options**: Define the list of available choices with labels and values

## Searchability

When a text field is marked searchable, Bayanat creates a full-text search index on it. This means the field's content appears in search results alongside built-in fields.
