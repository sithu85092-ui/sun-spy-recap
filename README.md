Build the foundation of my project SUN SPY RECAP as a professional AI Video Recap platform.

IMPORTANT:

- Do NOT use OpenAI API.
- Do NOT require any paid API.
- Do NOT require API keys for the initial foundation.
- Do NOT use Cloudflare.
- The architecture must be modular so AI providers can be added later.
- The project must be suitable for development from an Android phone.

Create this repository structure:

sun-spy-recap/
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── api/
│   │   ├── upload.py
│   │   ├── recap.py
│   │   └── jobs.py
│   ├── services/
│   │   ├── ffmpeg.py
│   │   ├── transcription.py
│   │   ├── analyzer.py
│   │   ├── clipper.py
│   │   ├── narrator.py
│   │   ├── subtitles.py
│   │   └── renderer.py
│   └── workers/
│       └── video_worker.py
├── storage/
│   ├── uploads/.gitkeep
│   ├── temp/.gitkeep
│   └── output/.gitkeep
├── tests/
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md

Backend requirements:

1. Use Python + FastAPI.

2. Create a clean REST API.

3. Add:
   POST /api/upload/init
   POST /api/upload/chunk
   POST /api/upload/complete
   POST /api/recap
   GET /api/status/{job_id}
   GET /api/health

4. Implement chunked video upload.

5. Never convert uploaded video into base64.

6. Support resumable uploads.

7. Validate file size and extension.

8. Generate unique upload IDs and job IDs.

9. Store uploaded files in storage/uploads.

10. Store temporary processing files in storage/temp.

11. Store completed videos in storage/output.

12. Add proper HTTP error responses.

13. Add structured logging.

14. Add CORS configuration.

15. Add environment-based configuration.

16. Use SQLite for the initial job database.

17. Create job states:

QUEUED
UPLOADING
PROCESSING
ANALYZING
CLIPPING
NARRATING
SUBTITLING
RENDERING
COMPLETED
FAILED

18. Create a modular processing pipeline:

Upload
→ Audio Extraction
→ Transcription
→ Video Analysis
→ Highlight Detection
→ Automatic Clip
→ Burmese Recap Generation
→ Burmese TTS
→ Subtitle Generation
→ 9:16 Rendering
→ Final Output

For the initial version, AI-dependent services should have safe placeholder implementations instead of fake AI results.

FFmpeg service:

- Detect whether FFmpeg is installed.
- Provide reusable functions for:
  - extracting audio
  - getting video duration
  - cutting clips
  - converting to 9:16
  - burning subtitles
  - exporting MP4

Frontend:
Create a professional responsive SUN SPY RECAP interface.

Brand:
☀️ SUN SPY RECAP

Tagline:
Upload • Discover • Recap

UI:

- Dark modern interface
- Video upload area
- Drag/drop support
- Mobile-friendly file picker
- Upload progress
- Processing progress
- Job status
- Video preview
- Final video download button
- Error message area

Do NOT pretend that AI processing is working if an AI model is not connected.

README must explain:

- Project architecture
- Installation
- FFmpeg installation
- Environment variables
- Running backend
- Running frontend
- API endpoints
- Development roadmap

Also create a clean .gitignore.

Make the code production-oriented, modular, readable and easy to extend.

After creating the files, ensure all Python imports work correctly and the FastAPI application can start without requiring external API keys.
