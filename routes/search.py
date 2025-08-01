"""
Search & Semantic API routes
Handles semantic search, topics, and keywords
"""

from flask import Blueprint, jsonify, request
import logging
from database.queries import SemanticQueries

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__, url_prefix='/api/search')


@search_bp.route('/', methods=['GET'])
def search_semantic_index_get():
    """Search the semantic index from database (GET endpoint)"""
    query = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    change_type = request.args.get('type', '').strip()  # content, tree, or empty for all
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    try:
        # Use database search instead of file operations
        result = SemanticQueries.search_semantic(query, limit, change_type)
        logger.info(f"Semantic search returned {len(result.get('results', []))} results")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error searching semantic index: {e}")
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


@search_bp.route('/semantic', methods=['POST'])
def search_semantic_index():
    """Search the semantic index from database"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query parameter is required'}), 400
        
        query = data['query']
        limit = data.get('limit', 10)
        
        results = SemanticQueries.search_semantic_index(query, limit)
        
        return jsonify({
            'query': query,
            'results': results,
            'total_results': len(results)
        })
    except Exception as e:
        logger.error(f"Failed to search semantic index: {e}")
        return jsonify({'error': str(e)}), 500


@search_bp.route('/topics', methods=['GET'])
def get_semantic_topics():
    """Get all available topics from database"""
    try:
        topics = SemanticQueries.get_all_topics()
        return jsonify({
            'topics': topics,
            'total_topics': len(topics)
        })
    except Exception as e:
        logger.error(f"Failed to get semantic topics: {e}")
        return jsonify({'error': str(e)}), 500


@search_bp.route('/keywords', methods=['GET'])
def get_semantic_keywords():
    """Get all available keywords from database"""
    try:
        keywords = SemanticQueries.get_all_keywords()
        return jsonify({
            'keywords': keywords,
            'total_keywords': len(keywords)
        })
    except Exception as e:
        logger.error(f"Failed to get semantic keywords: {e}")
        return jsonify({'error': str(e)}), 500
