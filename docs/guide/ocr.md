# OCR & Text Extraction

Bayanat extracts text from images attached to Bulletins. Extracted text is stored alongside the media and becomes searchable.

## Supported Formats

PNG, JPEG, TIFF, JPG, GIF, WebP, BMP, PNM.

## How It Works

1. Upload image files to a Bulletin as media attachments
2. Trigger OCR from the Bulletin's media panel (individual or all pending)
3. Extraction runs asynchronously in the background
4. Results appear on each media item with: extracted text, confidence score, word count, and detected language

Default language hints are Arabic and English (configurable).

## OCR Providers

Bayanat supports two OCR providers, configured via the `OCR_PROVIDER` environment variable.

### Google Vision (`google_vision`)

Google's cloud OCR service. Returns confidence scores, detected language, orientation correction, and bounding box data used by the Text Map feature.

```env
OCR_PROVIDER=google_vision
GOOGLE_VISION_API_KEY=your-api-key
```

### LLM (`llm`)

Works with any OpenAI-compatible `/v1/chat/completions` endpoint. This includes self-hosted models (Ollama, vLLM, SGLang) and cloud APIs (OpenAI, OpenRouter).

```env
OCR_PROVIDER=llm
LLM_OCR_URL=http://localhost:11434
LLM_OCR_MODEL=llava
LLM_OCR_API_KEY=               # optional, for authenticated endpoints
```

Example configurations:

| Provider | URL | Model |
|----------|-----|-------|
| Ollama (local) | `http://localhost:11434` | `llava` |
| vLLM on RunPod | `https://{pod_id}-8000.proxy.runpod.net` | `Qwen/Qwen2.5-VL-72B-Instruct-AWQ` |
| OpenAI | `https://api.openai.com` | `gpt-4o` |
| OpenRouter | `https://openrouter.ai/api` | `anthropic/claude-sonnet-4-20250514` |

The LLM provider includes automatic EXIF orientation correction and image downscaling for large files.

::: tip
The Text Map visual overlay feature is only available with the Google Vision provider, as it requires bounding box coordinates that LLM endpoints don't return.
:::

## Bulk Processing

OCR can be triggered in bulk for multiple Bulletins at once, processed asynchronously via the task queue. The system rate-limits requests to stay within API quotas (1200 requests/minute).

## Review and Editing

After extraction, users can:

- View the extracted text and confidence score
- Edit the extracted text manually (original is preserved)
- View a Text Map overlay showing text locations on the image (Google Vision only)
- Search across all extracted text

## Configuration

See [Configuration](/deployment/configuration) for full setup details.
