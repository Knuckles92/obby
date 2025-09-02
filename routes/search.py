"""
Search & Semantic API routes (FastAPI)
Handles semantic search, topics, and keywords
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import logging
from database.queries import SemanticQueries

logger = logging.getLogger(__name__)

search_bp = APIRouter(prefix='/api/search', tags=['search'])


@search_bp.get('/')
async def search_semantic_index_get(request: Request):
    """Search the semantic index from database (GET endpoint)"""
    query = (request.query_params.get('q', '') or '').strip()
    limit = int(request.query_params.get('limit', 20))
    change_type = (request.query_params.get('type', '') or '').strip()
    
    if not query:
        return JSONResponse({'error': 'Query parameter "q" is required'}, status_code=400)
    
    try:
        # Use database search instead of file operations
        result = SemanticQueries.search_semantic(query, limit, change_type)
        logger.info(f"Semantic search returned {len(result.get('results', []))} results")
        return result
        
    except Exception as e:
        logger.error(f"Error searching semantic index: {e}")
        return JSONResponse({'error': f'Search failed: {str(e)}'}, status_code=500)


@search_bp.post('/semantic')
async def search_semantic_index(request: Request):
    """Search the semantic index from database"""
    try:
        data = await request.json()
        if not data or 'query' not in data:
            return JSONResponse({'error': 'Query parameter is required'}, status_code=400)
        
        query = data['query']
        limit = data.get('limit', 10)
        
        results = SemanticQueries.search_semantic_index(query, limit)
        
        return {'query': query, 'results': results, 'total_results': len(results)}
    except Exception as e:
        logger.error(f"Failed to search semantic index: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@search_bp.get('/topics')
async def get_semantic_topics():
    """Get all available topics from database"""
    try:
        topics = SemanticQueries.get_all_topics()
        return {'topics': topics, 'total_topics': len(topics)}
    except Exception as e:
        logger.error(f"Failed to get semantic topics: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)


@search_bp.get('/keywords')
async def get_semantic_keywords():
    """Get all available keywords from database"""
    try:
        keywords = SemanticQueries.get_all_keywords()
        return {'keywords': keywords, 'total_keywords': len(keywords)}
    except Exception as e:
        logger.error(f"Failed to get semantic keywords: {e}")
        return JSONResponse({'error': str(e)}, status_code=500)
