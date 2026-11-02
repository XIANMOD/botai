# DIMZ AI RESIZER

Telegram bot for AI outpainting and iPhone Live Photo-style export.

## Features
- AI photo outpainting: 9:16, 16:9, 19:6, 1:1, 4:5, 3:4.
- Keeps the source photo centered and marks the added canvas as editable.
- Video to short MOV + JPEG key-photo pair, zipped for transfer to iPhone.
- FFmpeg-based video processing; Pillow handles image preparation.

## Important Live Photo limitation
A native Apple Live Photo is more than a JPEG and a MOV with matching filenames. It requires Apple's specific metadata and timed still-image marker. This starter creates a paired asset export and writes a shared content identifier where ExifTool supports it, but it does **not** guarantee that Apple Photos will automatically recognize the ZIP contents as a native Live Photo. The user may need a trusted iOS Live Photo creator/import app. Do not advertise guaranteed native pairing until tested on real iPhones.

## Requirements
- Telegram bot token from BotFather.
- OpenAI API key with Images API access and billing enabled.
- Railway service with a persistent volume mounted at `/data`.
- Docker deployment (FFmpeg + ExifTool are installed by Dockerfile).

## Deploy to Railway
1. Push this folder to a GitHub repository.
2. Create a Railway project from the repository.
3. Add a Railway Volume and mount it at `/data`.
4. Add Variables:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `IMAGE_MODEL=gpt-image-2.5-sunburst`
   - `IMAGE_QUALITY=high`
   - `WORK_DIR=/data/work`
   - `MAX_UPLOAD_MB=20`
5. Deploy. Railway uses the included Dockerfile.

## Run locally
```bash
cp .env.example .env
# Fill TELEGRAM_BOT_TOKEN and OPENAI_API_KEY
docker build -t dimz-ai-resizer .
docker run --rm --env-file .env -v "$PWD/data:/data" dimz-ai-resizer
```

## How photo outpainting works
1. The source image is EXIF-corrected.
2. Pillow creates a larger canvas in the requested aspect ratio.
3. A mask protects the original photo and marks only the added canvas as editable.
4. OpenAI Images Edit generates the missing environment.
5. The result is returned as PNG.

The requested 19:6 ratio is wider than the documented 3:1 maximum aspect ratio for GPT Image 2.5. The current ratio helper may therefore need a provider-specific two-pass/edge-extension strategy for exact 19:6 output. Test this ratio before public launch; do not promise exact 19:6 from the AI provider until validated.

## Security and operations
- Never commit `.env`.
- Keep the OpenAI key only in Railway Variables.
- Add Telegram user allowlists/rate limits before opening the bot publicly.
- Add file cleanup, job queue, usage quotas, and payment integration before monetization.
- API calls incur usage charges. Set provider spending limits.
- Uploaded media is stored temporarily under `/data/work`; configure scheduled cleanup.

## Current project status
Starter implementation. Photo outpainting is wired to the OpenAI Images Edit API. Live Photo export is a paired-file prototype and needs real-device validation plus proper Apple metadata finalization before being sold as native Live Photo conversion.
