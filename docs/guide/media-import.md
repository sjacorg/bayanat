# Media Import

Bayanat's Media Import tool creates Bulletins in bulk from media files (images, video, audio, and documents). Each file becomes a new Bulletin with the media attached. This is distinct from [Data Import](/guide/data-import), which loads structured records from spreadsheets.

Media Import is an administrator tool, available under **Data Import → Media** when enabled.

## Import Sources

There are two ways to bring files in:

- **Upload** — select files from your computer and upload them through the browser.
- **Server path** — import files already present in a designated folder on the server. This is useful for large batches that are impractical to upload through a browser. It must be enabled and restricted by an administrator (see below).

## Workflow

1. Open **Media Import** and choose a source (upload files, or scan a server path)
2. Set shared metadata for the batch: sources, labels, and access roles
3. Choose processing options:
   - **Parse** text from PDFs and documents
   - **OCR** images and scanned PDFs (requires [OCR](/guide/ocr) enabled)
   - **Transcribe** audio and video (requires [Transcription](/guide/transcription) enabled)
4. Process the batch; files are handled asynchronously in the background
5. One Bulletin is created per file, each with its media and any extracted text. You receive a notification when the batch completes.

Imported Bulletins are marked as machine-created and tagged with a batch ID so you can find and review them together.

## Supported File Types

Common image, video, audio, PDF, and document formats are supported. The exact allowed extensions are configurable by an administrator under **System Administration**.

## Deduplication

Files are tracked so the same file is not imported twice, which makes it safe to re-run a batch that was interrupted.

## Server Path Import (Administrators)

Importing from a server path is disabled by default. To use it, an administrator must both enable it and restrict it to a specific folder:

- Turn on **Media Import from a local path** in **System Administration**.
- Set the allowed folder on the server via the `ETL_ALLOWED_PATH` environment variable.

::: warning Restrict the import folder
Server path import reads files from within `ETL_ALLOWED_PATH`. Point it at a dedicated staging folder that holds only material intended for import, not a broad system directory. If `ETL_ALLOWED_PATH` is not set, server path import stays disabled even when the toggle is on.
:::

See [Configuration](/deployment/configuration) for setup details.
