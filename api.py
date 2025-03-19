from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
import tiktoken
import os
import uvicorn
import pandas as pd
import logging
from pathlib import Path

# Import GraphRAG modules
from graphrag.query.structured_search.global_search.search import GlobalSearch
from graphrag.query.structured_search.global_search.community_context import GlobalCommunityContext
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.local_search.mixed_context import LocalSearchMixedContext
from graphrag.query.indexer_adapters import (
    read_indexer_communities,
    read_indexer_entities,
    read_indexer_reports,
    read_indexer_text_units,
    read_indexer_relationships,
)
from graphrag.config.models.language_model_config import LanguageModelConfig
from graphrag.language_model.manager import ModelManager
from graphrag.config.enums import ModelType
from graphrag.query.context_builder.entity_extraction import EntityVectorStoreKey
from graphrag.vector_stores.lancedb import LanceDBVectorStore

# Load environment variables
_ = load_dotenv()

## Initialize FastAPI app
app = FastAPI()

# Logging setup
logging.basicConfig(level=logging.INFO)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load settings
INPUT_DIR = "./artifacts"
LANCEDB_URI = f"{INPUT_DIR}/lancedb"
COMMUNITY_TABLE = "communities"
COMMUNITY_REPORT_TABLE = "community_reports"
RELATIONSHIP_TABLE = "relationships"
TEXT_UNIT_TABLE = "text_units"
ENTITY_TABLE = "entities"
COMMUNITY_LEVEL = 2

# Load data from parquet files
community_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_TABLE}.parquet")
entity_df = pd.read_parquet(f"{INPUT_DIR}/{ENTITY_TABLE}.parquet")
report_df = pd.read_parquet(f"{INPUT_DIR}/{COMMUNITY_REPORT_TABLE}.parquet")
text_unit_df = pd.read_parquet(f"{INPUT_DIR}/{TEXT_UNIT_TABLE}.parquet")
relationship_df = pd.read_parquet(f"{INPUT_DIR}/{RELATIONSHIP_TABLE}.parquet")

# Process data
communities = read_indexer_communities(community_df, report_df)
reports = read_indexer_reports(report_df, community_df, COMMUNITY_LEVEL)
entities = read_indexer_entities(entity_df, community_df, COMMUNITY_LEVEL)
relationships = read_indexer_relationships(relationship_df)
text_units = read_indexer_text_units(text_unit_df)

# Initialize LanceDB Vector Store
description_embedding_store = LanceDBVectorStore(collection_name="default-entity-description")
description_embedding_store.connect(db_uri=LANCEDB_URI)

# Initialize Token Encoder
try:
    token_encoder = tiktoken.encoding_for_model(os.getenv("GRAPHRAG_LLM_MODEL", "cl100k_base"))
except KeyError:
    token_encoder = tiktoken.get_encoding("cl100k_base")

# Validate API Keys
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("❌ Missing OpenAI API Key. Set OPENAI_API_KEY in your .env file.")

# Initialize OpenAI LLM (GPT-4o-mini)
llm_model = "gpt-4o-mini"
llm_config = LanguageModelConfig(
    api_key=openai_api_key,
    type=ModelType.OpenAIChat,
    model=llm_model,
    max_retries=20,
)

llm = ModelManager().get_or_create_chat_model(
    name="global_search",
    model_type=ModelType.OpenAIChat,
    config=llm_config,
)

# Initialize OpenAI Embeddings
embedding_model = "text-embedding-3-large"  # You can also use "text-embedding-ada-002"
embedding_config = LanguageModelConfig(
    api_key=openai_api_key,
    type=ModelType.OpenAIEmbedding,
    model=embedding_model,
    max_retries=20,
)

text_embedder = ModelManager().get_or_create_embedding_model(
    name="openai_embedding",
    model_type=ModelType.OpenAIEmbedding,
    config=embedding_config,
)

import numpy as np
import pandas as pd

def clean_json(obj):
    """Recursively clean JSON to make it serializable."""
    if isinstance(obj, np.bool_):  
        return bool(obj)  # Convert NumPy bool to Python bool
    elif isinstance(obj, np.integer):  
        return int(obj)  # Convert NumPy int to Python int
    elif isinstance(obj, np.floating):  
        return float(obj)  # Convert NumPy float to Python float
    elif isinstance(obj, pd.DataFrame):  
        return obj.to_dict(orient="records")  # Convert DataFrame to JSON serializable list
    elif isinstance(obj, dict):  
        return {k: clean_json(v) for k, v in obj.items()}  # Process dicts recursively
    elif isinstance(obj, list):  
        return [clean_json(i) for i in obj]  # Process lists recursively
    return obj  # Return object if no conversion needed

# Initialize Local Search
def setup_local_search() -> LocalSearch:
    context_builder = LocalSearchMixedContext(
        community_reports=reports,
        text_units=text_units,
        entities=entities,
        relationships=relationships,
        entity_text_embeddings=description_embedding_store,
        embedding_vectorstore_key=EntityVectorStoreKey.ID,
        text_embedder=text_embedder,
        token_encoder=token_encoder,
    )

    local_context_params = {
        "text_unit_prop": 0.5,
        "community_prop": 0.1,
        "conversation_history_max_turns": 5,
        "conversation_history_user_turns_only": True,
        "top_k_mapped_entities": 10,
        "top_k_relationships": 10,
        "include_entity_rank": True,
        "include_relationship_weight": True,
        "include_community_rank": False,
        "return_candidate_context": False,
        "max_tokens": 12_000,
    }

    model_params = {"max_tokens": 2000, "temperature": 0.0}

    return LocalSearch(model=llm, context_builder=context_builder, token_encoder=token_encoder, model_params=model_params, context_builder_params=local_context_params)

# Initialize Global Search
def setup_global_search() -> GlobalSearch:
    context_builder = GlobalCommunityContext(
        community_reports=reports,
        communities=communities,
        entities=entities,
        token_encoder=token_encoder,
    )

    return GlobalSearch(model=llm, context_builder=context_builder, token_encoder=token_encoder, json_mode=True)

# Initialize Search Engines
global_search_engine = setup_global_search()
local_search_engine = setup_local_search()

# Search Endpoints
@app.get("/search/global")
async def global_search(query: str = Query(..., description="Search query for global context")):
    try:
        # result = await global_search_engine.search(query)

                # Perform the search using the global search engine
        result = await global_search_engine.search(query)

        # Prepare the response
        response_dict = jsonable_encoder({
            "response": result.response,  # Directly use the response from the search engine
            "context_data": result.context_data,  # Include context data
            "context_text": result.context_text,  # Include context text
            "reduce_context_data": result.reduce_context_data,  # Include reduce context data
            "reduce_context_text": result.reduce_context_text,  # Include reduce context text
            "map_responses": result.map_responses,  # Include map responses
            "completion_time": result.completion_time,  # Include completion time
            "llm_calls": result.llm_calls,  # Include LLM calls
            "llm_calls_categories": result.llm_calls_categories,  # Include LLM call categories
            "output_tokens": result.output_tokens,  # Include output tokens
            "output_tokens_categories": result.output_tokens_categories,  # Include output token categories
            "prompt_tokens": result.prompt_tokens,  # Include prompt tokens
            "prompt_tokens_categories": result.prompt_tokens_categories,  # Include prompt token categories
        })
        
        return JSONResponse(content=response_dict)
    

    
    except Exception as e:
        logging.error(f"Error in global_search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.get("/search/local")
async def local_search(query: str = Query(..., description="Search query for local context")):
    try:
        result = await local_search_engine.search(query)
        
        # ✅ Convert NumPy and Pandas objects to JSON serializable format
        response_dict = clean_json({
            "response": result.response,
            "context_data": result.context_data,
            "context_text": result.context_text,
            # "reduce_context_data": result.reduce_context_data,  # ✅ Now safely included
            # "reduce_context_text": result.reduce_context_text,
            # "map_responses": result.map_responses,
            "completion_time": result.completion_time,
            "llm_calls": result.llm_calls,
            "llm_calls_categories": result.llm_calls_categories,
            "output_tokens": result.output_tokens,
            "output_tokens_categories": result.output_tokens_categories,
            "prompt_tokens": result.prompt_tokens,
            "prompt_tokens_categories": result.prompt_tokens_categories,
        })
        
        return JSONResponse(content=jsonable_encoder(response_dict))
    
    except Exception as e:
        logging.error(f"Error in local_search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

# Status Endpoint
@app.get("/status")
async def status():
    return JSONResponse(content={"status": "Server is up and running"})

# Run the application
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
