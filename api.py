from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List
import uvicorn
import os
import shutil
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
import traceback

from utils import process_context_data
import graphrag.api as api
from graphrag.config.load_config import load_config
from config import (
    PROJECT_DIRECTORY,
    COMMUNITY_LEVEL,
    CLAIM_EXTRACTION_ENABLED,
    RESPONSE_TYPE,
)

load_dotenv(Path(PROJECT_DIRECTORY) / ".env")

from claimify import Claimify
claimify = Claimify(model="gpt-4o-mini", p=2, f=2)

# ---------- helpers --------------------------------------------------------- #
OUTPUT_DIR = Path(PROJECT_DIRECTORY) / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_parquet_safe(path: Path, empty_cols: list[str] | None = None):
    """
    Load a parquet file if it exists and is non-empty; otherwise return an
    empty DataFrame with the supplied columns (or 0-col DF if None).
    """
    if path.exists() and path.stat().st_size:
        return pd.read_parquet(path)
    return pd.DataFrame(columns=empty_cols or [])

# ---------- lifespan -------------------------------------------------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.config = load_config(Path(PROJECT_DIRECTORY))

    app.state.entities           = load_parquet_safe(OUTPUT_DIR / "entities.parquet")
    app.state.communities        = load_parquet_safe(OUTPUT_DIR / "communities.parquet")
    app.state.community_reports  = load_parquet_safe(OUTPUT_DIR / "community_reports.parquet")
    app.state.text_units         = load_parquet_safe(OUTPUT_DIR / "text_units.parquet")
    app.state.relationships      = load_parquet_safe(OUTPUT_DIR / "relationships.parquet")

    # covariates are optional
    cov_path = OUTPUT_DIR / "covariates.parquet"
    app.state.covariates = (
        load_parquet_safe(cov_path) if CLAIM_EXTRACTION_ENABLED else None
    )

    yield
# --------------------------------------------------------------------------- #

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────── General utility routes ──────────────── #
# api.py  (add this route; upload route stays as-is)
@app.post("/reload")
async def reload_data(request: Request):
    request.app.state.entities          = load_parquet_safe(OUTPUT_DIR / "entities.parquet")
    request.app.state.relationships     = load_parquet_safe(OUTPUT_DIR / "relationships.parquet")
    request.app.state.documents         = load_parquet_safe(OUTPUT_DIR / "documents.parquet")
    request.app.state.text_units        = load_parquet_safe(OUTPUT_DIR / "text_units.parquet")
    request.app.state.communities       = load_parquet_safe(OUTPUT_DIR / "communities.parquet")
    request.app.state.community_reports = load_parquet_safe(OUTPUT_DIR / "community_reports.parquet")
    if CLAIM_EXTRACTION_ENABLED:
        request.app.state.covariates    = load_parquet_safe(OUTPUT_DIR / "covariates.parquet")

    return JSONResponse(content={"status": "Server data reloaded"})

@app.get("/check/settings")
async def check_settings():
    env_path  = Path(PROJECT_DIRECTORY, ".env")
    yaml_path = Path(PROJECT_DIRECTORY, "settings.yaml")
    ok = env_path.exists() and yaml_path.exists()
    return JSONResponse(
        content={"status": "✅ Both .env and settings.yaml exist." if ok
                         else "❌ One or both files are missing."}
    )

@app.get("/settings/view_adjustments")
async def view_settings():
    path = Path(PROJECT_DIRECTORY, "settings.yaml")
    if not path.exists():
        return JSONResponse(content={"status": "No settings.yaml file found."})
    return JSONResponse(
        content={"status": "Settings.yaml file found.", "content": path.read_text()}
    )

class SettingsUpdateRequest(BaseModel):
    content: str

@app.post("/settings/update")
async def update_settings(payload: SettingsUpdateRequest):
    try:
        Path(PROJECT_DIRECTORY, "settings.yaml").write_text(payload.content)
        return JSONResponse(content={"status": "Settings.yaml file updated."})
    except Exception as e:
        return JSONResponse(
            content={"status": "Error updating settings.yaml file.", "error": str(e)}
        )

# ─────────────── File-system helpers ──────────────── #
@app.get("/check/output")
async def check_output():
    files = [p.name for p in OUTPUT_DIR.iterdir()] if OUTPUT_DIR.exists() else []
    return JSONResponse(content={"files": files or "No output directory found."})

# @app.post("/clear/output")
# async def clear_output(request: Request):
#     if not OUTPUT_DIR.exists():
#         return JSONResponse(content={"status": "No output directory found."})

#     # 1️⃣ delete everything on disk
#     for item in OUTPUT_DIR.iterdir():
#         if item.is_file() or item.is_symlink():
#             item.unlink()
#         else:
#             shutil.rmtree(item)

#     # 2️⃣ refresh the app-state DataFrames
#     request.app.state.entities          = load_parquet_safe(OUTPUT_DIR / "entities.parquet")
#     request.app.state.relationships     = load_parquet_safe(OUTPUT_DIR / "relationships.parquet")
#     request.app.state.documents         = load_parquet_safe(OUTPUT_DIR / "documents.parquet")
#     request.app.state.text_units        = load_parquet_safe(OUTPUT_DIR / "text_units.parquet")
#     request.app.state.communities       = load_parquet_safe(OUTPUT_DIR / "communities.parquet")
#     request.app.state.community_reports = load_parquet_safe(OUTPUT_DIR / "community_reports.parquet")
#     if CLAIM_EXTRACTION_ENABLED:
#         request.app.state.covariates    = load_parquet_safe(OUTPUT_DIR / "covariates.parquet")

#     return JSONResponse(content={"status": "Output directory cleared and server state reset"})


# helper: return blank DF with same columns, or really empty if df is None
def _blank(df):
    import pandas as pd
    return df.iloc[0:0] if df is not None else pd.DataFrame()

@app.post("/clear/output")
async def clear_output(request: Request):
    if not OUTPUT_DIR.exists():
        return JSONResponse({"status": "No output directory found."})

    # 1️⃣ wipe folder
    for p in OUTPUT_DIR.iterdir():
        p.unlink() if p.is_file() or p.is_symlink() else shutil.rmtree(p)

    # 2️⃣ reset backend tables safely
    s = request.app.state
    for name in [
        "entities",
        "relationships",
        "documents",
        "text_units",
        "communities",
        "community_reports",
        "covariates",
    ]:
        # if attribute exists use blank-copy; else create empty DF
        old = getattr(s, name, None)
        setattr(s, name, _blank(old))

    return JSONResponse({"status": "Output folder cleared; backend tables reset"})

# ─────────────── Upload endpoint ──────────────── #
@app.post("/upload/new_file")
async def upload_new_file(files: List[UploadFile] = File(...)):
    uploaded = []
    for fil in files:
        dest = OUTPUT_DIR / fil.filename
        dest.write_bytes(await fil.read())
        uploaded.append(fil.filename)
    return JSONResponse(content={"status": "Files uploaded successfully", "files": uploaded})

# ─────────────── Search endpoints (unchanged) ──────────────── #
# Search endpoints with debug logs
@app.get("/search/global")
async def global_search(query: str = Query(..., description="Global Search")):
    try:
        print("🔍 Global Search Triggered: ", query)
        response, context = await api.global_search(
            config=app.state.config,
            entities=app.state.entities,
            communities=app.state.communities,
            community_reports=app.state.community_reports,
            community_level=COMMUNITY_LEVEL,
            dynamic_community_selection=False,
            response_type=RESPONSE_TYPE,
            query=query,
        )
        print("✅ global_search response:", response)
        payload = await claimify.extract(question=query, answer=response)
        print("✅ claimify payload:", payload)
        return JSONResponse(content={
            "response": response,
            "claimify": payload,
            "context_data": process_context_data(context),
        })
    except Exception as e:
        print("❌ Error in global_search:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/local")
async def local_search(query: str = Query(..., description="Local Search")):
    try:
        print("🔍 Local Search Triggered: ", query)
        response, context = await api.local_search(
            config=app.state.config,
            entities=app.state.entities,
            communities=app.state.communities,
            community_reports=app.state.community_reports,
            text_units=app.state.text_units,
            relationships=app.state.relationships,
            covariates=app.state.covariates,
            community_level=COMMUNITY_LEVEL,
            response_type=RESPONSE_TYPE,
            query=query,
        )
        print("✅ local_search response:", response)
        payload = await claimify.extract(question=query, answer=response)
        print("✅ claimify payload:", payload)
        return JSONResponse(content={
            "response": response,
            "claimify": payload,
            "context_data": process_context_data(context),
        })
    except Exception as e:
        print("❌ Error in local_search:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/drift")
async def drift_search(query: str = Query(..., description="DRIFT Search")):
    try:
        response, context = await api.drift_search(
                                config=app.state.config,
                                entities=app.state.entities,
                                communities=app.state.communities,
                                community_reports=app.state.community_reports,
                                text_units=app.state.text_units,
                                relationships=app.state.relationships,
                                community_level=COMMUNITY_LEVEL,                                
                                response_type=RESPONSE_TYPE,
                                query=query,
                            )
        response_dict = {
            "response": response,
            "context_data": process_context_data(context),
        }
        return JSONResponse(content=response_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/basic")
async def basic_search(query: str = Query(..., description="Basic Search")):
    try:
        response, context = await api.basic_search(
                                config=app.state.config,
                                text_units=app.state.text_units,                                
                                query=query,
                            )
        response_dict = {
            "response": response,
            "context_data": process_context_data(context),
        }
        return JSONResponse(content=response_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    return JSONResponse(content={"status": "Server is up and running"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)