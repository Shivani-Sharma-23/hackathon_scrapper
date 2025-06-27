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

def format_hackathon_for_frontend(hackathon):
    """Format hackathon data to match frontend expectations"""
    return {
        'id': hackathon.get('$id', hackathon.get('id', '')),
        'title': hackathon.get('title', 'Untitled Hackathon'),
        'name': hackathon.get('title', 'Untitled Hackathon'),  # Alternative field name
        'organizer': hackathon.get('organization', 'Unknown Organization'),
        'organization': hackathon.get('organization', 'Unknown Organization'),
        'description': hackathon.get('description', 'No description available'),
        'location': hackathon.get('location', 'Location TBA'),
        'mode': hackathon.get('mode', 'online'),
        'prize_pool': hackathon.get('prize', 'Prize not specified'),
        'prize': hackathon.get('prize', 'Prize not specified'),
        'registration_deadline': hackathon.get('registration_deadline', ''),
        'submission_deadline': hackathon.get('submission_deadline', ''),
        'start_date': hackathon.get('start_date', ''),
        'date': hackathon.get('start_date', ''),  # Alternative field name
        'registration_link': hackathon.get('participation_link', '#'),
        'participation_link': hackathon.get('participation_link', '#'),
        'link': hackathon.get('participation_link', '#'),  # Alternative field name
        'status': determine_hackathon_status(hackathon),
        'themes': hackathon.get('themes', []),
        'technologies': hackathon.get('technologies', []),
        'team_size': hackathon.get('team_size', ''),
        'duration': hackathon.get('duration', ''),
        'logo': hackathon.get('logo', ''),
        'source': 'Database'
    }

def determine_hackathon_status(hackathon):
    """Determine hackathon status based on dates"""
    import datetime
    
    try:
        current_date = datetime.datetime.now()
        
        registration_deadline = hackathon.get('registration_deadline')
        start_date = hackathon.get('start_date')
        submission_deadline = hackathon.get('submission_deadline')
        
        if registration_deadline:
            reg_date = datetime.datetime.fromisoformat(registration_deadline.replace('Z', '+00:00'))
            if current_date < reg_date:
                return 'upcoming'
        
        if start_date and submission_deadline:
            start = datetime.datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end = datetime.datetime.fromisoformat(submission_deadline.replace('Z', '+00:00'))
            
            if start <= current_date <= end:
                return 'ongoing'
            elif current_date > end:
                return 'ended'
            elif current_date < start:
                return 'upcoming'
        
        return 'open'  # Default status
        
    except Exception as e:
        logger.error(f"Error determining status: {e}")
        return 'open'

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
        status = request.args.get('status', '')
        difficulty = request.args.get('difficulty', '')
        limit = int(request.args.get('limit', 50))
        
        logger.info(f"Query params - q: '{query}', location: '{location}', mode: '{mode}', status: '{status}', difficulty: '{difficulty}'")
        
        # Get hackathons from database
        try:
            hackathons_response = appwrite_client.get_hackathons(limit=limit * 2)  # Get more to filter
            logger.info(f"Appwrite response type: {type(hackathons_response)}")
            
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
        
        # Filter hackathons based on query and filters
        filtered_hackathons = []
        for hackathon in hackathons:
            try:
                # Skip invalid hackathons
                if not hackathon or not isinstance(hackathon, dict):
                    continue
                
                # Format hackathon first
                formatted_hackathon = format_hackathon_for_frontend(hackathon)
                
                # Apply text search filter
                if query:
                    search_fields = [
                        formatted_hackathon.get('title', ''),
                        formatted_hackathon.get('organization', ''),
                        formatted_hackathon.get('description', ''),
                        formatted_hackathon.get('location', ''),
                        ' '.join(formatted_hackathon.get('themes', [])),
                        ' '.join(formatted_hackathon.get('technologies', []))
                    ]
                    search_text = ' '.join(search_fields).lower()
                    if query.lower() not in search_text:
                        continue
                
                # Apply mode filter
                if mode and mode != 'all':
                    hackathon_mode = formatted_hackathon.get('mode', '').lower()
                    if mode.lower() != hackathon_mode:
                        continue
                
                # Apply status filter
                if status and status != 'all':
                    hackathon_status = formatted_hackathon.get('status', '').lower()
                    if status.lower() not in hackathon_status:
                        continue
                
                # Apply location filter (if location is specified)
                if location and location != 'all':
                    hackathon_location = formatted_hackathon.get('location', '').lower()
                    if location.lower() not in hackathon_location and location.lower() != 'online':
                        continue
                
                filtered_hackathons.append(formatted_hackathon)
                
                # Limit results
                if len(filtered_hackathons) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"Error processing hackathon {hackathon}: {e}")
                continue
        
        logger.info(f"Returning {len(filtered_hackathons)} filtered hackathons")
        
        return jsonify({
            'success': True,
            'hackathons': filtered_hackathons,
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
    """Alternative search endpoint that matches frontend expectations"""
    try:
        logger.info("Search hackathons endpoint called")
        
        if not appwrite_client:
            return jsonify({
                'success': False,
                'message': 'Database connection not available',
                'hackathons': []
            }), 500
        
        # Get query parameters (same as frontend sends)
        query = request.args.get('q', '')
        mode = request.args.get('mode', '')
        status = request.args.get('status', '')
        difficulty = request.args.get('difficulty', '')
        limit = int(request.args.get('limit', 50))
        
        logger.info(f"Search params - query: '{query}', mode: '{mode}', status: '{status}', difficulty: '{difficulty}'")
        
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
            
            # Format hackathon
            formatted_hackathon = format_hackathon_for_frontend(hackathon)
            
            # Apply filters
            if mode and mode != 'all' and mode.lower() != formatted_hackathon.get('mode', '').lower():
                continue
            
            if status and status != 'all' and status.lower() not in formatted_hackathon.get('status', '').lower():
                continue
            
            # Text search
            if query:
                search_text = f"{formatted_hackathon.get('title', '')} {formatted_hackathon.get('organization', '')} {formatted_hackathon.get('description', '')}".lower()
                if query.lower() not in search_text:
                    continue
            
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

@app.route('/api/get-personalized-hackathons', methods=['POST'])
def get_personalized_hackathons():
    """Get personalized hackathon recommendations based on user profile"""
    try:
        logger.info("Personalized hackathons endpoint called")
        
        if not appwrite_client:
            return jsonify({
                'success': False,
                'message': 'Database connection not available',
                'hackathons': []
            }), 500
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided',
                'hackathons': []
            }), 400
        
        user_skills = data.get('skills', [])
        experience_level = data.get('experience_level', 'beginner')
        interests = data.get('interests', [])
        preferred_mode = data.get('preferred_mode', 'any')
        
        logger.info(f"Personalization params - skills: {user_skills}, experience: {experience_level}, interests: {interests}, mode: {preferred_mode}")
        
        # Get all hackathons
        hackathons_response = appwrite_client.get_hackathons(limit=100)
        
        if not hackathons_response or not hackathons_response.get('documents'):
            return jsonify({
                'success': True,
                'hackathons': [],
                'total': 0,
                'message': 'No hackathons found in database'
            })
        
        hackathons = hackathons_response['documents']
        scored_hackathons = []
        
        # Score each hackathon based on user profile
        for hackathon in hackathons:
            if not hackathon.get('title'):
                continue
            
            formatted_hackathon = format_hackathon_for_frontend(hackathon)
            
            # Calculate relevance score
            score = 0.0
            
            # Skill matching (40% weight)
            if user_skills:
                hackathon_text = f"{formatted_hackathon.get('title', '')} {formatted_hackathon.get('description', '')} {' '.join(formatted_hackathon.get('themes', []))} {' '.join(formatted_hackathon.get('technologies', []))}".lower()
                skill_matches = sum(1 for skill in user_skills if skill.lower() in hackathon_text)
                skill_score = skill_matches / len(user_skills) if user_skills else 0
                score += skill_score * 0.4
            
            # Interest matching (30% weight)
            if interests:
                hackathon_text = f"{formatted_hackathon.get('title', '')} {formatted_hackathon.get('description', '')}".lower()
                interest_matches = sum(1 for interest in interests if interest.lower() in hackathon_text)
                interest_score = interest_matches / len(interests) if interests else 0
                score += interest_score * 0.3
            
            # Mode preference (20% weight)
            if preferred_mode and preferred_mode != 'any':
                hackathon_mode = formatted_hackathon.get('mode', '').lower()
                if preferred_mode.lower() == hackathon_mode:
                    score += 0.2
                elif preferred_mode.lower() == 'online' and hackathon_mode in ['online', 'virtual']:
                    score += 0.2
                elif preferred_mode.lower() == 'offline' and hackathon_mode in ['offline', 'physical']:
                    score += 0.2
            
            # Experience level matching (10% weight)
            hackathon_text = f"{formatted_hackathon.get('title', '')} {formatted_hackathon.get('description', '')}".lower()
            if experience_level == 'beginner' and any(word in hackathon_text for word in ['beginner', 'student', 'first-time', 'newbie']):
                score += 0.1
            elif experience_level == 'intermediate' and any(word in hackathon_text for word in ['intermediate', 'experienced']):
                score += 0.1
            elif experience_level == 'advanced' and any(word in hackathon_text for word in ['advanced', 'expert', 'professional']):
                score += 0.1
            
            # Add some randomness to avoid always showing same results
            import random
            score += random.uniform(0, 0.1)
            
            scored_hackathons.append({
                'hackathon': formatted_hackathon,
                'score': score
            })
        
        # Sort by score and return top results
        scored_hackathons.sort(key=lambda x: x['score'], reverse=True)
        top_hackathons = [item['hackathon'] for item in scored_hackathons[:50]]
        
        logger.info(f"Returning {len(top_hackathons)} personalized hackathons")
        
        return jsonify({
            'success': True,
            'hackathons': top_hackathons,
            'total': len(top_hackathons),
            'personalized': True
        })
        
    except Exception as e:
        logger.error(f"Error in get_personalized_hackathons: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'message': f'Error getting personalized recommendations: {str(e)}',
            'hackathons': []
        }), 500

@app.route('/api/recommendations/<user_id>', methods=['GET'])
def get_user_recommendations(user_id):
    """Get recommendations for a specific user ID using the recommendation engine"""
    try:
        if not recommendation_engine:
            return jsonify({
                'success': False,
                'message': 'Recommendation engine not available',
                'recommendations': []
            }), 500
        
        num_recommendations = int(request.args.get('limit', 10))
        recommendations = recommendation_engine.get_recommendations(user_id, num_recommendations)
        
        # Format recommendations for frontend
        formatted_recommendations = []
        for rec in recommendations:
            formatted_hackathon = format_hackathon_for_frontend(rec['hackathon'])
            formatted_hackathon['recommendation_score'] = rec['score']
            formatted_hackathon['recommendation_reason'] = rec['recommendation_reason']
            formatted_recommendations.append(formatted_hackathon)
        
        return jsonify({
            'success': True,
            'recommendations': formatted_recommendations,
            'total': len(formatted_recommendations)
        })
        
    except Exception as e:
        logger.error(f"Error in get_user_recommendations: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'recommendations': []
        }), 500

@app.route('/api/hackathon/<hackathon_id>', methods=['GET'])
def get_hackathon(hackathon_id):
    try:
        if not appwrite_client:
            return jsonify({'success': False, 'message': 'Database not available'}), 500
            
        hackathon = appwrite_client.get_hackathon(hackathon_id)
        if hackathon:
            formatted_hackathon = format_hackathon_for_frontend(hackathon)
            return jsonify({'success': True, 'hackathon': formatted_hackathon})
        else:
            return jsonify({'success': False, 'message': 'Hackathon not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_hackathon: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
            raw_response = appwrite_client.get_hackathons(limit=2)
            formatted_hackathons = []
            
            if raw_response and raw_response.get('documents'):
                for hackathon in raw_response['documents'][:2]:
                    formatted_hackathons.append(format_hackathon_for_frontend(hackathon))
            
            return jsonify({
                'success': True,
                'connection_status': is_connected,
                'connection_message': message,
                'raw_response_type': str(type(raw_response)),
                'raw_response_keys': list(raw_response.keys()) if isinstance(raw_response, dict) else [],
                'sample_formatted_hackathons': formatted_hackathons,
                'total_hackathons': len(raw_response.get('documents', [])) if raw_response else 0
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
            '/api/get-personalized-hackathons (POST)',
            '/api/recommendations/<user_id>',
            '/api/hackathon/<hackathon_id>',
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