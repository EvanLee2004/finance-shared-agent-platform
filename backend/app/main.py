"""Finance shared agent platform API — scaffold only."""

from fastapi import FastAPI

app = FastAPI(title="财务共享中台 Agent", version="0.0.1")


@app.get("/api/v1/health")
def health() -> dict:
    return {
        "status": "ok",
        "name": "finance-shared-agent-platform",
        "phase": "scaffold",
        "opencode": "external serve — not bundled",
        "skills_repo": "finance-shared-skills",
    }
