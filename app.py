# hackathon_app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from hackathon_appwrite_client import HackathonAppwriteClient
from hackathon_recommendation_engine import HackathonRecommendationEngine
import os
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=['*'])  # Allow all origins for deployment

# Initialize clients
appwrite_client = HackathonAppwriteClient()
recommendation_engine = HackathonRecommendationEngine(appwrite_client)

@app.route('/')
def home():
    logger.info("Home route accessed")
    return jsonify({
        'message': 'Hackathon Recommendation API',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'test': '/api/test',
            'recommendations': '/api/recommendations/<user_id>',
            'personalized_hackathons': '/api/get-personalized-hackathons',
            'search_hackathons': '/api/search-hackathons',
            'hackathon_details': '/api/hackathon/<hackathon_id>'
        }
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    logger.info("Health check accessed")
    return jsonify({'status': 'healthy', 'message': 'Hackathon Recommendation API is running'})

@app.route('/api/test', methods=['GET'])
def test_route():
    logger.info("Test route accessed")
    # Test Appwrite connection
    is_connected, message = appwrite_client.test_connection()
    return jsonify({
        'success': True, 
        'message': 'Test route working!',
        'appwrite_connection': is_connected,
        'appwrite_message': message
    })

@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
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
        hackathon = appwrite_client.get_hackathon(hackathon_id)
        if hackathon:
            return jsonify({'success': True, 'hackathon': hackathon})
        else:
            return jsonify({'success': False, 'message': 'Hackathon not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_hackathon: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recommendations/<user_id>', methods=['GET'])
def get_recommendations(user_id):
    try:
        logger.info(f"Getting recommendations for user: {user_id}")
        
        # Get query parameters
        num_recommendations = int(request.args.get('limit', 10))
        mode = request.args.get('mode')
        location = request.args.get('location')
        prize_range = request.args.get('prize_range')
        
        # Build filters
        filters = {}
        if mode:
            filters['mode'] = mode
        if location:
            filters['location'] = location
        if prize_range:
            filters['prize_range'] = prize_range
        
        # Get recommendations
        if filters:
            recommendations = recommendation_engine.get_filtered_recommendations(
                user_id, filters, num_recommendations
            )
        else:
            recommendations = recommendation_engine.get_recommendations(
                user_id, num_recommendations
            )
        
        # Format response
        formatted_recommendations = []
        for rec in recommendations:
            hackathon = rec['hackathon']
            formatted_recommendations.append({
                'hackathon': {
                    'id': hackathon.get('$id'),
                    'title': hackathon.get('title'),
                    'organization': hackathon.get('organization'),
                    'prize': hackathon.get('prize'),
                    'mode': hackathon.get('mode'),
                    'location': hackathon.get('location'),
                    'registration_deadline': hackathon.get('registration_deadline'),
                    'submission_deadline': hackathon.get('submission_deadline'),
                    'start_date': hackathon.get('start_date'),
                    'participation_link': hackathon.get('participation_link')
                },
                'matchScore': round(rec['score'] * 100, 2),
                'matchBreakdown': {
                    'skillMatch': round(rec['skill_score'] * 100, 2),
                    'locationMatch': round(rec['location_score'] * 100, 2),
                    'prizeMatch': round(rec['prize_score'] * 100, 2),
                    'contentSimilarity': round(rec['content_similarity'] * 100, 2),
                    'modeMatch': round(rec['mode_score'] * 100, 2)
                },
                'recommendationReason': rec['recommendation_reason']
            })
        
        return jsonify({
            'success': True,
            'recommendations': formatted_recommendations,
            'total': len(formatted_recommendations),
            'userId': user_id
        })
        
    except Exception as e:
        logger.error(f"Error in get_recommendations: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/get-personalized-hackathons', methods=['POST'])
def get_personalized_hackathons():
    try:
        data = request.get_json()
        logger.info(f"Getting personalized hackathons with data: {data}")
        
        # Extract parameters from request
        user_id = data.get('user_id')  # If user is logged in
        skills = data.get('skills', [])
        location = data.get('location', 'flexible')
        mode = data.get('mode', 'online')
        prize_preference = data.get('prize_preference', 'any')
        
        # If user_id provided, use enhanced recommendation system
        if user_id:
            recommendations = recommendation_engine.get_recommendations(user_id, 20)
            
            # Format hackathons for frontend
            formatted_hackathons = []
            for rec in recommendations:
                hackathon = rec['hackathon']
                formatted_hackathons.append({
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
                    'logo': f"https://logo.clearbit.com/{hackathon.get('organization', '').replace(' ', '').lower()}.com",
                    'source': 'HackathonHub',
                    'matchScore': round(rec['score'] * 100, 2),
                    'recommendationReason': rec['recommendation_reason']
                })
            
            return jsonify({
                'success': True,
                'hackathons': formatted_hackathons,
                'total': len(formatted_hackathons),
                'personalized': True
            })
        
        # If no user_id, use basic filtering
        else:
            # Create a mock user profile for the recommendation engine
            mock_user_data = {
                'skills': skills,
                'location': location,
                'mode': mode,
                'prize_preference': prize_preference,
            }
            
            # Get all hackathons first
            hackathons_response = appwrite_client.get_hackathons(limit=500)
            if not hackathons_response or not hackathons_response.get('documents'):
                return jsonify({
                    'success': False,
                    'message': 'No hackathons found',
                    'hackathons': []
                })
            
            hackathons = hackathons_response['documents']
            
            # Calculate scores for each hackathon using the recommendation engine logic
            hackathon_scores = []
            
            for hackathon in hackathons:
                if not hackathon.get('$id'):
                    continue
                if not hackathon.get('title'):
                    continue
                
                # Filter by mode if specified
                if mode != 'all' and hackathon.get('mode', '').lower() != mode.lower():
                    continue
                
                # Calculate similarity scores
                skill_score = recommendation_engine.calculate_skill_similarity(
                    skills, hackathon.get('title', '') + ' ' + hackathon.get('organization', '')
                )
                
                location_score = recommendation_engine.calculate_location_match(
                    location, hackathon.get('location', '')
                )
                
                mode_score = recommendation_engine.calculate_mode_match(
                    mode, hackathon.get('mode', '')
                )
                
                prize_score = recommendation_engine.calculate_prize_match(
                    prize_preference, hackathon.get('prize', '')
                )
                
                # Content similarity
                content_similarity = recommendation_engine.calculate_content_similarity(mock_user_data, hackathon)
                
                # Weighted final score
                final_score = (
                    skill_score * 0.3 +
                    content_similarity * 0.25 +
                    location_score * 0.2 +
                    mode_score * 0.15 +
                    prize_score * 0.1
                )
                
                hackathon_scores.append({
                    'hackathon': hackathon,
                    'score': final_score,
                    'skill_score': skill_score,
                    'location_score': location_score,
                    'mode_score': mode_score,
                    'prize_score': prize_score,
                    'content_similarity': content_similarity
                })
            
            # Sort by score
            hackathon_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Format hackathons for frontend
            formatted_hackathons = []
            for rec in hackathon_scores[:20]:  # Return top 20
                hackathon = rec['hackathon']
                formatted_hackathons.append({
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
                    'logo': f"https://logo.clearbit.com/{hackathon.get('organization', '').replace(' ', '').lower()}.com",
                    'source': 'HackathonHub',
                    'matchScore': round(rec['score'] * 100, 2)
                })
            
            return jsonify({
                'success': True,
                'hackathons': formatted_hackathons,
                'total': len(formatted_hackathons),
                'personalized': False
            })
        
    except Exception as e:
        logger.error(f"Error in get_personalized_hackathons: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'hackathons': []}), 500

@app.route('/api/search-hackathons', methods=['GET'])
def search_hackathons():
    try:
        # Get query parameters
        query = request.args.get('q', '')
        location = request.args.get('location', 'all')
        mode = request.args.get('mode', 'all')
        prize_range = request.args.get('prize_range', 'all')
        limit = int(request.args.get('limit', 50))
        
        logger.info(f"Searching hackathons with query: {query}, location: {location}, mode: {mode}")
        
        # Get hackathons from database with filters
        if location != 'all' or mode != 'all':
            hackathons_response = appwrite_client.get_hackathons_by_filters(
                location=location if location != 'all' else None,
                mode=mode if mode != 'all' else None
            )
        else:
            hackathons_response = appwrite_client.get_hackathons(limit=limit * 2)
        
        if not hackathons_response or not hackathons_response.get('documents'):
            return jsonify({
                'success': False,
                'message': 'No hackathons found',
                'hackathons': []
            })
        
        hackathons = hackathons_response['documents']
        filtered_hackathons = []
        
        for hackathon in hackathons:
            if not hackathon.get('$id'):
                continue
            if not hackathon.get('title'):
                continue
            
            # Text search in title and organization
            if query:
                hackathon_text = f"{hackathon.get('title', '')} {hackathon.get('organization', '')}".lower()
                if query.lower() not in hackathon_text:
                    continue
            
            # Prize range filter
            if prize_range != 'all':
                hackathon_prize = hackathon.get('prize', '').lower()
                if prize_range == 'high' and not any(word in hackathon_prize for word in ['₹50000', '₹1,00,000', '₹2,00,000', 'lakh', 'crore']):
                    continue
                elif prize_range == 'medium' and not any(word in hackathon_prize for word in ['₹10000', '₹25000', '₹50000']):
                    continue
                elif prize_range == 'low' and not any(word in hackathon_prize for word in ['₹1000', '₹5000', '₹10000']):
                    continue
            
            # Format hackathon for response
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
                'logo': f"https://logo.clearbit.com/{hackathon.get('organization', '').replace(' ', '').lower()}.com",
                'source': 'HackathonHub'
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
        logger.error(f"Error in search_hackathons: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'hackathons': []}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))  # Different port from job API
    app.run(host='0.0.0.0', port=port, debug=True)