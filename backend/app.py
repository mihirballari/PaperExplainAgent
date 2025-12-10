import os
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

PROJECT_ROOT = Path(__file__).resolve().parent.parent
THEOREM_AGENT_DIR = PROJECT_ROOT / "TheoremExplainAgent"
UPLOAD_DIR = PROJECT_ROOT / "uploads"
OUTPUT_BASE_DIR = THEOREM_AGENT_DIR / "output" / "api_jobs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="TheoremExplainAgent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/artifacts", StaticFiles(directory=OUTPUT_BASE_DIR), name="artifacts")

JobRecord = Dict[str, Any]
JOBS: Dict[str, JobRecord] = {}


def _record_artifact(job: JobRecord, line: str) -> None:
    lower = line.lower()
    keyword_hits = any(
        key in lower
        for key in (
            "saved to",
            "rendered to",
            "success!",
            "combined.mp4",
            "succ_rendered",
        )
    )
    if keyword_hits:
        artifacts = job.setdefault("artifacts", [])
        artifacts.append(line.strip())


def _find_combined_video(output_dir: Path) -> tuple[str, str]:
    for candidate in output_dir.rglob("*_combined.mp4"):
        rel_path = candidate.relative_to(OUTPUT_BASE_DIR)
        return str(candidate), f"/artifacts/{rel_path.as_posix()}"
    return "", ""


def _run_generation(job_id: str, pdf_path: Path, use_rag: bool, model: str, helper_model: str, api_key: str):
    job = JOBS[job_id]
    job["status"] = "running"
    job["message"] = "Running generation pipeline..."

    job_output_dir = OUTPUT_BASE_DIR / job_id
    job_output_dir.mkdir(parents=True, exist_ok=True)
    job["outputDir"] = str(job_output_dir)

    cmd = [
        "python3",
        "-u",
        "generate_video.py",
        "--pdf_path",
        str(pdf_path),
        "--output_dir",
        str(job_output_dir),
        "--model",
        model,
        "--helper_model",
        helper_model,
    ]

    env = os.environ.copy()
    if api_key:
        env["GEMINI_API_KEY"] = api_key

    job_stdout: list[str] = []
    job_stderr: list[str] = []
    job["logs"] = job.get("logs", [])
    job["artifacts"] = job.get("artifacts", [])

    with subprocess.Popen(
        cmd,
        cwd=THEOREM_AGENT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        bufsize=1,
    ) as proc:
        if proc.stdout:
            for raw_line in proc.stdout:
                line = raw_line.rstrip()
                if not line:
                    continue
                job_stdout.append(line)
                job["logs"].append(line)
                job["message"] = line[-160:]
                _record_artifact(job, line)
        proc.wait()
        return_code = proc.returncode or 0

    job["stdout"] = "\n".join(job_stdout)
    job["stderr"] = "\n".join(job_stderr)
    job["returncode"] = str(return_code)
    job["outputDir"] = str(job_output_dir)

    if return_code == 0:
        job["status"] = "done"
        job["message"] = "Generation complete."
        video_path, video_url = _find_combined_video(job_output_dir)
        if video_path:
            job["videoPath"] = video_path
            job["videoUrl"] = video_url
    else:
        job["status"] = "error"
        job["message"] = "Generation failed. Check logs for details."

    try:
        pdf_path.unlink()
    except FileNotFoundError:
        pass


@app.post("/api/generate")
async def create_job(
    background_tasks: BackgroundTasks,
    pdf: UploadFile = File(...),
    use_rag: bool = Form(False),
    model: str = Form("gemini/gemini-3-pro-preview"),
    helper_model: str = Form("gemini/gemini-3-pro-preview"),
    api_key: str = Form(""),
):
    if pdf.content_type not in {"application/pdf"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    job_id = str(uuid.uuid4())
    upload_path = UPLOAD_DIR / f"{job_id}.pdf"

    with upload_path.open("wb") as dest:
        shutil.copyfileobj(pdf.file, dest)

    JOBS[job_id] = {
        "status": "queued",
        "message": "Job queued.",
        "logs": [],
        "artifacts": [],
        "outputDir": "",
        "videoPath": "",
        "videoUrl": "",
    }

    background_tasks.add_task(_run_generation, job_id, upload_path, use_rag, model, helper_model, api_key)
    return {"jobId": job_id}


@app.get("/api/status/{job_id}")
async def job_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job
