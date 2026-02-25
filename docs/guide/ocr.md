# OCR & Text Extraction

Bayanat can extract text from images attached to Bulletins using Google Vision API. Extracted text is stored alongside the media and becomes searchable.

## Supported Formats

PNG, JPEG, TIFF, JPG, GIF, WebP, BMP, PNM.

## How It Works

1. Upload image files to a Bulletin as media attachments
2. Trigger OCR from the Bulletin's media panel (individual or all pending)
3. Extraction runs asynchronously in the background
4. Results appear on each media item with: extracted text, confidence score, word count, and detected language

The system uses Google Vision API with automatic language detection and orientation correction. Default language hints are Arabic and English (configurable).

## Bulk Processing

OCR can be triggered in bulk for multiple Bulletins at once, processed asynchronously via the task queue. The system rate-limits requests to stay within API quotas (1200 requests/minute).

## Review and Editing

After extraction, users can:

- View the extracted text and confidence score
- Edit the extracted text manually (original is preserved)
- Mark extractions for manual review
- Search across all extracted text

## Configuration

OCR requires a Google Vision API key configured in the environment. See [Configuration](/deployment/configuration) for setup details.
