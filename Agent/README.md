# PaperExplainAgent

> AI pipeline that ingests PDFs (or topics), plans multi‑scene stories, generates Manim animations with TTS, and combines them into narrated videos.

## What it does
- PDF → markdown + figures, builds a scene outline, generates per‑scene code, renders with manim + Kokoro voiceover, and stitches the scenes into a single MP4/SRT.
- Supports partial reruns: skips scenes with `succ_rendered.txt`, re‑renders missing scenes, and can combine only.
- Fast combine: optional stream‑copy ffmpeg concat (`--fast_combine`) to avoid full re‑encode when streams match.
- Utilities: status checks, peek of existing renders, context-learning/RAG support, and concurrent scene/topic processing.

## Quick start
### 1) Environment
```bash
conda create -n tea python=3.12.8
conda activate tea
pip install -r requirements.txt
```
Install manim dependencies (LaTeX, etc.) per https://docs.manim.community. Install SoX (for voiceover); on Windows ensure `sox.exe` is on PATH.

### 2) Models & keys
Download Kokoro TTS:
```bash
mkdir -p models
wget -P models https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v0_19.onnx
wget -P models https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices.bin
```
Create `.env` (see `.env.template`) with your model keys (OpenAI/Azure/Gemini/Vertex) and Kokoro paths.

### 3) Make imports work
From repo root:
```bash
# PowerShell
set "PYTHONPATH=%CD%;%PYTHONPATH%"
# or bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 4) Run
Single topic:
```bash
python generate_video.py \
  --model "gemini/gemini-3-pro-preview" \
  --helper_model "gemini/gemini-3-pro-preview" \
  --output_dir "output/exp1" \
  --topic "Big O notation" \
  --context "worst-case complexity explanation"
```

From a PDF:
```bash
python generate_video.py \
  --model "gemini/gemini-3-pro-preview" \
  --helper_model "gemini/gemini-3-pro-preview" \
  --output_dir "output/exp1" \
  --pdf_path "data/papers/nested_learning.pdf"
```

Combine only (reuse existing renders):
```bash
python generate_video.py \
  --pdf_path "data/papers/nested_learning.pdf" \
  --output_dir "output/exp1" \
  --model "gemini/gemini-3-pro-preview" \
  --helper_model "gemini/gemini-3-pro-preview" \
  --only_combine \
  --fast_combine   # optional stream-copy concat
```

Render missing scenes only (skip combine):
```bash
python generate_video.py ... --only_render
```

Plan only (no render/combine):
```bash
python generate_video.py ... --only_plan
```

### Common flags
- `--only_plan` generate outline + plans, stop.
- `--only_render` render missing scenes, no combine.
- `--only_combine` stitch existing scenes.
- `--fast_combine` try stream-copy concat (skip re-encode).
- `--peek_existing_videos` summarize combined/scene renders in output_dir.
- `--check_status` status table for batch theorems.
- `--scenes 1 3` limit to specific scenes (with theorems_path).
- Concurrency: `--max_scene_concurrency`, `--max_topic_concurrency`.

### Fast combine details
When `--fast_combine` is set, `combine_videos` first tries `ffmpeg -f concat -safe 0 -i <list> -c copy` with absolute paths. If streams mismatch or concat fails, it falls back to the re-encode path (libx264+aac) and then merges subtitles.

## Troubleshooting
- `ModuleNotFoundError: src`: ensure PYTHONPATH includes repo root (see step 3).
- SoX not found: add its `bin` (e.g., `C:\ProgramData\chocolatey\lib-bad\sox.portable\14.4.1\lib`) to PATH, reopen shell, `sox --version`.
- Missing LaTeX/manim deps: install TeX + manim prerequisites for your OS.
- Combining hangs: use `--fast_combine`; if it falls back, allow re-encode to finish or re-run `--only_combine --fast_combine` once scenes exist.

## Evaluation
Requires video (mp4) + subtitles (srt). Example:
```bash
python evaluate.py --file_path path/to/topic_folder --output_folder eval_out --model_text gpt-4o --eval_type all
```

## Citation
If you use this code/data:
```
@misc{ku2025theoremexplainagentmultimodalexplanationsllm,
  title  = {TheoremExplainAgent: Towards Multimodal Explanations for LLM Theorem Understanding},
  author = {Max Ku and Thomas Chong and Jonathan Leung and Krish Shah and Alvin Yu and Wenhu Chen},
  year   = {2025},
  eprint = {2502.19400},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url    = {https://arxiv.org/abs/2502.19400}
}
```

## License
MIT. See `LICENSE`.
