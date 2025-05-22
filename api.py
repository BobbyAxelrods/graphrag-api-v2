from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from pathlib import Path
import uvicorn
import pandas as pd
import shutil
from typing import List, Dict, Any
import traceback
import zipfile
from fastapi import UploadFile, File, HTTPException
from fastapi.responses import JSONResponse


from dotenv import load_dotenv
from utils import process_context_data
import graphrag.api as api
from graphrag.config.load_config import load_config
from config import (
    PROJECT_DIRECTORY,
    COMMUNITY_LEVEL,
    CLAIM_EXTRACTION_ENABLED,
    RESPONSE_TYPE,
)

# Load environment variables
load_dotenv(Path(PROJECT_DIRECTORY) / ".env")

# Initialize Claimify
from claimify import Claimify
claimify = Claimify(model="gpt-4o-mini", p=2, f=2)

# Prepare output directory
OUTPUT_DIR = Path(PROJECT_DIRECTORY) / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

def load_parquet_safe(path: Path, empty_cols: list[str] | None = None) -> pd.DataFrame:
    if path.exists() and path.stat().st_size:
        df = pd.read_parquet(path)
        print(f"Loaded {path.name}: rows={len(df)}, cols={df.shape[1]}")
        return df
    print(f"Missing or empty {path.name}. Returning empty DataFrame with cols={empty_cols}.")
    return pd.DataFrame(columns=empty_cols or [])

def reload_state(app: FastAPI):
    app.state.config = load_config(Path(PROJECT_DIRECTORY))
    app.state.entities = load_parquet_safe(OUTPUT_DIR / "entities.parquet")
    app.state.communities = load_parquet_safe(
        OUTPUT_DIR / "communities.parquet",
        empty_cols=["entity_ids", "community_id"],
    )
    app.state.community_reports = load_parquet_safe(OUTPUT_DIR / "community_reports.parquet")
    app.state.text_units = load_parquet_safe(OUTPUT_DIR / "text_units.parquet")
    app.state.relationships = load_parquet_safe(OUTPUT_DIR / "relationships.parquet")
    cov_path = OUTPUT_DIR / "covariates.parquet"
    app.state.covariates = (
        load_parquet_safe(cov_path) if CLAIM_EXTRACTION_ENABLED else None
    )

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://researchrag.southeastasia.cloudapp.azure.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/reload")
async def _reload(request: Request):
    reload_state(app)
    return JSONResponse({"status": "Server data reloaded"})

@app.get("/check/settings")
async def check_settings():
    env_path = Path(PROJECT_DIRECTORY) / ".env"
    yaml_path = Path(PROJECT_DIRECTORY) / "settings.yaml"
    ok = env_path.exists() and yaml_path.exists()
    return JSONResponse({
        "status": "✅ Both .env and settings.yaml exist." if ok else "❌ Missing .env or settings.yaml."
    })

@app.get("/check/output")
async def check_output():
    files = [p.name for p in OUTPUT_DIR.iterdir()] if OUTPUT_DIR.exists() else []
    return JSONResponse({"files": files or "No output directory found."})
# helper: return blank DF with same columns, or really empty if df is None
def _blank(df):
    import pandas as pd
    return df.iloc[0:0] if df is not None else pd.DataFrame()

# @app.post("/clear/output")
# async def clear_output(request: Request):
#     if not OUTPUT_DIR.exists():
#         return JSONResponse({"status": "No output directory found."})

#     # 1️⃣ wipe folder
#     for p in OUTPUT_DIR.iterdir():
#         p.unlink() if p.is_file() or p.is_symlink() else shutil.rmtree(p)

#     # 2️⃣ reset backend tables safely
#     s = request.app.state
#     for name in [
#         "entities",
#         "relationships",
#         "documents",
#         "text_units",
#         "communities",
#         "community_reports",
#         "covariates",
#     ]:
#         # if attribute exists use blank-copy; else create empty DF
#         old = getattr(s, name, None)
#         setattr(s, name, _blank(old))

#     return JSONResponse({"status": "Output folder cleared; backend tables reset"})

@app.post("/clear/output")
async def clear_output(request: Request):
    if not OUTPUT_DIR.exists():
        return JSONResponse({"status": "No output directory found."})

    # 1️⃣ wipe folder except "lancedb"
    for p in OUTPUT_DIR.iterdir():
        # skip the lancedb folder entirely
        if p.name == "lancedb":
            continue

        if p.is_file() or p.is_symlink():
            p.unlink()
        else:
            shutil.rmtree(p)

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
        old = getattr(s, name, None)
        setattr(s, name, _blank(old))

    return JSONResponse({"status": "Output folder cleared; backend tables reset"})

@app.post("/upload/new_file")
async def upload_file(files: List[UploadFile] = File(...)):
    if not files:
        return JSONResponse(status_code=400, content={"error": "No files provided."})
    saved = []
    for up in files:
        # up.filename may be "filename.txt" or "subdir/inner.txt"
        dest = OUTPUT_DIR / up.filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        content = await up.read()
        dest.write_bytes(content)
        saved.append(str(dest.relative_to(OUTPUT_DIR)))

    return JSONResponse({"status": "uploaded", "files": saved})


@app.get("/search/global")
async def global_search(query: str = Query(..., description="Global Search")):
    try:
        print("🔍 Global Search Triggered:", query)
        reload_state(app)
        print("entities:", app.state.entities.shape)
        print("communities:", app.state.communities.shape)
        if app.state.entities.empty or app.state.communities.empty:
            return JSONResponse(
                status_code=400,
                content={"error": "Missing entities or communities data."},
            )
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
        return JSONResponse({
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
        print("🔍 Local Search Triggered:", query)
        reload_state(app)
        print("entities:", app.state.entities.shape)
        print("communities:", app.state.communities.shape)
        print("text_units:", app.state.text_units.shape)
        if (
            app.state.entities.empty
            or app.state.communities.empty
            or app.state.text_units.empty
        ):
            return JSONResponse(
                status_code=400,
                content={"error": "Missing entities, communities, or text_units data."},
            )
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
        return JSONResponse({
            "response": response,
            "claimify": payload,
            "context_data": process_context_data(context),
        })
    except Exception as e:
        print("❌ Error in local_search:", e)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status():
    return JSONResponse({"status": "Server is up and running"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
