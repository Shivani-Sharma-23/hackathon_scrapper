# fixed_hackathon_app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from appwrite_client import HackathonAppwriteClient
from recommendation_engine import HackathonRecommendationEngine
import os
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=['*'])

# Initialize clients with error handling
try:
    appwrite_client = HackathonAppwriteClient()
    logger.info("Appwrite client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Appwrite client: {e}")
    appwrite_client = None

try:
    recommendation_engine = HackathonRecommendationEngine(appwrite_client) if appwrite_client else None
    logger.info("Recommendation engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize recommendation engine: {e}")
    recommendation_engine = None

@app.route('/')
def home():
    logger.info("Home route accessed")
    return jsonify({
        'message': 'Hackathon Recommendation API',
        'status': 'running',
        'appwrite_connected': appwrite_client is not None,
        'recommendation_engine_ready': recommendation_engine is not None,
        'endpoints': {
            'health': '/api/health',
            'test': '/api/test',
            'hackathons': '/api/hackathons',
            'search_hackathons': '/api/search-hackathons',
            'recommendations': '/api/recommendations/<user_id>',
            'personalized_hackathons': '/api/get-personalized-hackathons',
            'hackathon_details': '/api/hackathon/<hackathon_id>'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    logger.info("Health check accessed")
    return jsonify({
        'status': 'healthy', 
        'message': 'Hackathon Recommendation API is running',
        'appwrite_status': 'connected' if appwrite_client else 'disconnected',
        'recommendation_engine_status': 'ready' if recommendation_engine else 'not ready'
    })

@app.route('/api/test', methods=['GET'])
def test_route():
    logger.info("Test route accessed")
    
    if not appwrite_client:
        return jsonify({
            'success': False,
            'message': 'Appwrite client not initialized',
            'appwrite_connection': False,
            'appwrite_message': 'Client initialization failed'
        })
    
    # Test Appwrite connection
    try:
        is_connected, message = appwrite_client.test_connection()
        
        # Try to get a sample of hackathons
        sample_hackathons = None
        try:
            hackathons_response = appwrite_client.get_hackathons(limit=1)
            if hackathons_response and hackathons_response.get('documents'):
                sample_hackathons = len(hackathons_response['documents'])
        except Exception as e:
            logger.error(f"Error getting sample hackathons: {e}")
        
        return jsonify({
            'success': True, 
            'message': 'Test route working!',
            'appwrite_connection': is_connected,
            'appwrite_message': message,
            'sample_hackathons_count': sample_hackathons
        })
    except Exception as e:
        logger.error(f"Error in test route: {e}")
        return jsonify({
            'success': False,
            'message': f'Test failed: {str(e)}',
            'appwrite_connection': False
        })

# This is the endpoint your frontend is calling
@app.route('/api/hackathons', methods=['GET'])
def get_hackathons():
    """Main endpoint for getting hackathons - matches your frontend call"""
    try:
        logger.info("GET /api/hackathons called")
        
        if not appwrite_client:
            logger.error("Appwrite client not available")
            return jsonify({
                'success': False,
                'error': 'Database connection not available',
                'hackathons': []
            }), 500
        
        # Get query parameters
        query = request.args.get('q', '')
        location = request.args.get('location', '')
        mode = request.args.get('mode', '')
        limit = int(request.args.get('limit', 50))
        
        logger.info(f"Query params - q: '{query}', location: '{location}', mode: '{mode}', limit: {limit}")
        
        # Get hackathons from database
        try:
            if location or mode:
                hackathons_response = appwrite_client.get_hackathons_by_filters(
                    location=location if location else None,
                    mode=mode if mode else None,
                    limit=limit
                )
            else:
                hackathons_response = appwrite_client.get_hackathons(limit=limit)
            
            logger.info(f"Appwrite response type: {type(hackathons_response)}")
            logger.info(f"Appwrite response: {hackathons_response}")
            
        except Exception as e:
            logger.error(f"Error calling Appwrite: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({
                'success': False,
                'error': f'Database query failed: {str(e)}',
                'hackathons': []
            }), 500
        
        if not hackathons_response:
            logger.warning("No response from Appwrite")
            return jsonify({
                'success': True,
                'hackathons': [],
                'data': [],
                'total': 0,
                'message': 'No hackathons found'
            })
        
        # Handle different response formats
        hackathons = []
        if isinstance(hackathons_response, dict):
            if 'documents' in hackathons_response:
                hackathons = hackathons_response['documents']
            elif 'data' in hackathons_response:
                hackathons = hackathons_response['data']
            else:
                hackathons = [hackathons_response]  # Single document
        elif isinstance(hackathons_response, list):
            hackathons = hackathons_response
        
        logger.info(f"Processing {len(hackathons)} hackathons")
        
        # Filter hackathons based on query
        filtered_hackathons = []
        for hackathon in hackathons:
            try:
                # Skip invalid hackathons
                if not hackathon or not isinstance(hackathon, dict):
                    continue
                
                # Text search in title and organization if query provided
                if query:
                    title = str(hackathon.get('title', '')).lower()
                    organization = str(hackathon.get('organization', '')).lower()
                    location_text = str(hackathon.get('location', '')).lower()
                    
                    search_text = f"{title} {organization} {location_text}"
                    if query.lower() not in search_text:
                        continue
                
                # Format hackathon for response
                formatted_hackathon = {
                    'id': hackathon.get('$id', hackathon.get('id', '')),
                    'title': hackathon.get('title', 'Untitled Hackathon'),
                    'organization': hackathon.get('organization', 'Unknown Organization'),
                    'location': hackathon.get('location', 'Location TBA'),
                    'mode': hackathon.get('mode', 'online'),
                    'prize': hackathon.get('prize', 'Prize not specified'),
                    'registration_deadline': hackathon.get('registration_deadline', ''),
                    'submission_deadline': hackathon.get('submission_deadline', ''),
                    'start_date': hackathon.get('start_date', ''),
                    'participation_link': hackathon.get('participation_link', '#'),
                    'source': 'Database'
                }
                
                filtered_hackathons.append(formatted_hackathon)
                
            except Exception as e:
                logger.error(f"Error processing hackathon {hackathon}: {e}")
                continue
        
        logger.info(f"Returning {len(filtered_hackathons)} filtered hackathons")
        
        return jsonify({
            'success': True,
            'hackathons': filtered_hackathons,
            'data': filtered_hackathons,  # Alternative key for compatibility
            'total': len(filtered_hackathons),
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Unexpected error in get_hackathons: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': f'Internal server error: {str(e)}',
            'hackathons': []
        }), 500

@app.route('/api/search-hackathons', methods=['GET'])
def search_hackathons():
    """Alternative search endpoint"""
    try:
        logger.info("Search hackathons endpoint called")
        
        if not appwrite_client:
            return jsonify({
                'success': False,
                'message': 'Database connection not available',
                'hackathons': []
            }), 500
        
        # Get query parameters
        query = request.args.get('q', '')
        location = request.args.get('location', 'all')
        mode = request.args.get('mode', 'all')
        limit = int(request.args.get('limit', 50))
        
        logger.info(f"Search params - query: '{query}', location: '{location}', mode: '{mode}'")
        
        # Get hackathons from database
        hackathons_response = appwrite_client.get_hackathons(limit=limit * 2)
        
        if not hackathons_response or not hackathons_response.get('documents'):
            return jsonify({
                'success': True,
                'hackathons': [],
                'total': 0,
                'message': 'No hackathons found in database'
            })
        
        hackathons = hackathons_response['documents']
        filtered_hackathons = []
        
        for hackathon in hackathons:
            # Skip invalid entries
            if not hackathon.get('title'):
                continue
            
            # Apply filters
            if location != 'all' and location.lower() not in hackathon.get('location', '').lower():
                continue
            
            if mode != 'all' and mode.lower() != hackathon.get('mode', '').lower():
                continue
            
            # Text search
            if query:
                hackathon_text = f"{hackathon.get('title', '')} {hackathon.get('organization', '')}".lower()
                if query.lower() not in hackathon_text:
                    continue
            
            # Format hackathon
            formatted_hackathon = {
                'id': hackathon.get('$id', ''),
                'title': hackathon.get('title', ''),
                'organization': hackathon.get('organization', ''),
                'location': hackathon.get('location', ''),
                'mode': hackathon.get('mode', ''),
                'prize': hackathon.get('prize', 'Prize not specified'),
                'registration_deadline': hackathon.get('registration_deadline', ''),
                'submission_deadline': hackathon.get('submission_deadline', ''),
                'start_date': hackathon.get('start_date', ''),
                'participation_link': hackathon.get('participation_link', '#'),
                'source': 'Database'
            }
            
            filtered_hackathons.append(formatted_hackathon)
            
            if len(filtered_hackathons) >= limit:
                break
        
        return jsonify({
            'success': True,
            'hackathons': filtered_hackathons,
            'total': len(filtered_hackathons),
            'query': query
        })
        
    except Exception as e:
        logger.error(f"Error in search_hackathons: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False, 
            'message': str(e), 
            'hackathons': []
        }), 500

@app.route('/api/debug/database', methods=['GET'])
def debug_database():
    """Debug endpoint to check database contents"""
    try:
        if not appwrite_client:
            return jsonify({
                'success': False,
                'message': 'Appwrite client not available'
            })
        
        # Test connection
        is_connected, message = appwrite_client.test_connection()
        
        # Try to get raw database response
        try:
            raw_response = appwrite_client.get_hackathons(limit=5)
            return jsonify({
                'success': True,
                'connection_status': is_connected,
                'connection_message': message,
                'raw_response': raw_response,
                'response_type': str(type(raw_response))
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'connection_status': is_connected,
                'connection_message': message,
                'database_error': str(e),
                'traceback': traceback.format_exc()
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# Keep your existing routes
@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        if not appwrite_client:
            return jsonify({'success': False, 'message': 'Database not available'}), 500
            
        user = appwrite_client.get_user(user_id)
        if user:
            return jsonify({'success': True, 'user': user})
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_user: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/hackathon/<hackathon_id>', methods=['GET'])
def get_hackathon(hackathon_id):
    try:
        if not appwrite_client:
            return jsonify({'success': False, 'message': 'Database not available'}), 500
            
        hackathon = appwrite_client.get_hackathon(hackathon_id)
        if hackathon:
            return jsonify({'success': True, 'hackathon': hackathon})
        else:
            return jsonify({'success': False, 'message': 'Hackathon not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_hackathon: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found',
        'available_endpoints': [
            '/api/health',
            '/api/test',
            '/api/hackathons',
            '/api/search-hackathons',
            '/api/debug/database'
        ]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"Starting Flask app on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)