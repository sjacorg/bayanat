# Media Management

Bayanat supports file attachments on Bulletins and Actors. Media files are uploaded, stored, and tracked with metadata and deduplication.

## Supported File Types

**General uploads**: MP4, WebM, JPG, GIF, PNG, PDF, DOC, TXT

**Video imports**: Extended format support including MKV, FLV, MOV, AVI, WMV, MPEG, 3GP, MTS, and many others.

**OCR-capable images**: PNG, JPEG, TIFF, JPG, GIF, WebP, BMP, PNM. See [OCR & Text Extraction](/guide/ocr).

## Upload

Files are uploaded via chunked upload (resumable). Each file is validated by extension and hashed (MD5) for deduplication. Duplicate files (matching hash) are rejected.

## Metadata

Each media item tracks:

- Title (bilingual: English/Arabic)
- Comments (bilingual)
- Category
- File type and duration (for videos)
- Orientation
- Hash (for deduplication)

## Storage Backends

Bayanat supports two storage backends:

- **Local filesystem**: Files stored in `enferno/media/`. Default for most deployments.
- **Amazon S3**: Configurable bucket and region. Files served via presigned URLs (1-hour expiry).

See [Configuration](/deployment/configuration) for storage backend setup.

## Video Features

Video attachments include a built-in player with screenshot capture functionality, allowing users to take snapshots from video frames.
