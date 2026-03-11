# Data Import

Bayanat supports importing data from spreadsheets (CSV, XLSX, XLS) to create Bulletins, Actors, and Incidents in bulk.

## Supported Formats

- CSV (.csv)
- Excel (.xlsx, .xls)

## Workflow

1. Upload a spreadsheet file
2. Map spreadsheet columns to Bayanat fields using the column mapping interface
3. Save the mapping for reuse with similar files
4. Submit the import for processing
5. Rows are validated and processed asynchronously
6. Review results: each row is logged with its status (Pending, Processing, Ready, Failed) and any error details

## Validation

Each row is validated before creation:

- Required fields must be present
- Data types are coerced automatically (numbers, dates, booleans)
- Lookup references are validated (labels, sources, nationalities, etc.)
- Boolean fields accept flexible input: "y", "yes", "true", "t" are treated as true
- Dates are parsed in multiple formats

Rows that fail validation are logged with detailed error messages and skipped without affecting other rows.

## Column Mapping

The mapping interface lets you match each spreadsheet column to the corresponding Bayanat field. Mappings can be saved and reloaded for recurring imports with consistent column structures.

## Access Control

Imported items can be assigned to access groups during import. See [Access Control](/guide/access-control) for details.

## Deduplication

Files are tracked by hash to prevent duplicate imports of the same spreadsheet.
