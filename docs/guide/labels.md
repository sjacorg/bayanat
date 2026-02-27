# Labels

Labels are tags that can be added to Actors, Bulletins, and Incidents.

## Purpose

Labels allow for easy search and filtering. They can tag content, metadata, or be used for references and workflow control.

## Methodology

Labels are split into two lists:

- [Unverified Labels](/methodology/unverified-labels): Descriptive labels based on observations and source allegations
- [Verified Labels](/methodology/verified-labels): Neutral labels based on analyst observation and evidence

## Fields

::: tip Admin only
Labels administration dashboard is available to admins only.
:::

### Title

Bilingual name visible to users.

### Comment

Bilingual admin note (e.g., reason for creation).

### Parent

Creates a hierarchy of parent and child Labels. Useful for search.

### Type and Visibility Controls

- **Verified**: Checkbox to mark as verified (default is unverified)
- **Visibility**: Checkboxes to control visibility in Actors, Bulletins, and Incidents

## Import from CSV

Admins can bulk import labels from a formatted CSV file.
