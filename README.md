# PaperExplainAgent

PaperExplainAgent turns a PDF paper into a narrated, Manim-rendered explainer video. The project glues together a simple React UI, a FastAPI job runner, and the TheoremExplainAgent generation pipeline to plan scenes, write Manim code, render clips, and return artifacts back to the browser.

Core idea:
- You upload a research PDF and provide an API key.
- The backend ingests the PDF into markdown + images, summarizes it, and feeds that context to the TheoremExplainAgent pipeline.
- The agent plans scenes, drafts Manim code, renders the scenes, and combines them into a final video (plus intermediate artifacts like logs and thumbnails).
- The frontend polls job status and previews the finished video and artifacts when ready.

High level stack:
- Frontend: Vite + React single page that accepts the PDF/API key and displays status, logs, artifacts, and the returned video.
- Backend: FastAPI that queues jobs, runs `TheoremExplainAgent/generate_video.py` as a subprocess, streams logs/artifacts, and serves generated media.
- Agent: TheoremExplainAgent (LLM + Manim) that does planning, codegen, rendering, optional RAG, and optional TTS.

This README focuses on the aim of the project; see `TheoremExplainAgent/README.md` for full generation details and `docs/` for the published site.
