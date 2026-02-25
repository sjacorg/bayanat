# Search

Bayanat has a powerful search tool that allows searching every data field and creating advanced and complex queries. Available for Actors, Bulletins, and Incidents, and also for finding related items within any component.

## Quick Search

The main search box searches text fields (titles, descriptions, names) and the last update comment. Results update as you type.

## Advanced Search

Access by clicking the button on the right side of the search bar. This opens a panel with every searchable field for the current entity type.

### Searchable Fields

| Entity | Fields |
| --- | --- |
| Bulletins | Title, description, sources, labels, locations, events, publish date, documentation date, status, assigned user, reviewer, access roles |
| Actors | Name, nickname, description, nationality, ethnography, sex, age, labels, sources, status, assigned user |
| Incidents | Title, description, locations, labels, potential violations, claimed violations, status |

### Operators

- **AND (default)**: Multiple values in the same field must all match
- **OR ("Any" checkbox)**: Any of the selected values will match
- **Exclude**: Negate a field to exclude matching results

### Date Searching

For date fields, you can specify:

- Exact date
- Date range (from/to)
- **Within**: A time window around the chosen date (e.g., within 7 days)

### Location Searching

Locations support hierarchical search. Selecting a parent location (e.g., a governorate) will also match items tagged with child locations (districts, subdistricts).

## Complex Search

"Refine/Extend Search" allows building multi-step queries by combining search queries with logical operators.

1. Run an initial search
2. Click "Refine/Extend Search"
3. Set new search parameters
4. Choose how to combine with previous results:
   - **AND**: Narrow results (must match both queries)
   - **OR**: Broaden results (match either query)
5. Repeat to build arbitrarily complex queries

This is useful for queries that can't be expressed in a single search, such as "Bulletins from Damascus OR Aleppo that mention detention AND are assigned to me."

## Saved Searches

Save current search parameters for quick reuse:

1. Run any search (simple or complex)
2. Click "Save Search"
3. Name the search
4. Access saved searches from the search bar dropdown

Saved searches store the full query, including complex multi-step queries.
