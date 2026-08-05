# Transcription

Bayanat can transcribe audio and video media to searchable text using [Whisper](https://github.com/openai/whisper), running locally on your own server. It is the audio/video counterpart to [OCR](/guide/ocr): transcripts are stored alongside the media and become searchable.

## How It Works

Transcription runs as part of [Media Import](/guide/media-import). When you import audio or video files, you can opt to transcribe them, and a background worker generates the transcript automatically.

1. Start a Media Import and add audio or video files
2. Enable **Transcribe audio/video files** in the import options
3. Optionally choose a language, or leave it blank for automatic detection
4. Process the import; transcription runs asynchronously in the background
5. The transcript is attached to each media item and marked as auto-generated

## Models

Whisper offers several models, selected under **System Administration → Whisper Model**. Larger models are more accurate but slower and need more memory; smaller models are faster and lighter.

| Model | Relative size | Notes |
|-------|---------------|-------|
| `tiny`, `base` | Smallest | Fast, modest accuracy. `base` is the default. |
| `small`, `medium` | Mid | Better accuracy, slower. |
| `large` | Largest | Best accuracy, slowest, highest memory use. |

English-only variants (`.en`, e.g. `base.en`) are available and can be more accurate for English-only material.

::: tip First run downloads the model
The selected model is downloaded and cached on the server the first time it is used. Later transcriptions reuse the cached copy. A GPU speeds transcription up considerably but is not required; Whisper also runs on CPU.
:::

## Languages

Whisper auto-detects the spoken language by default. You can also set a specific language for an import when you know it in advance, which can improve accuracy.

## Reviewing and Correcting Transcripts

Auto-generated transcripts are a starting point, not a final record. Reviewers (Admin or Data Analyst roles) can correct the text directly on the media item. Edits are preserved with a history of changes, the original is not lost, and the corrected text becomes the searchable version.

## Searching Transcripts

Transcribed text is indexed and searchable the same way as OCR text, so a phrase spoken in a video can be found through normal search.

## Enabling Transcription

Transcription is off by default. An administrator enables it under **System Administration** (the "Allow Transcription of Media Files" setting) and selects a Whisper model. The transcription engine ships as an optional component; see [Configuration](/deployment/configuration) for installation details.
