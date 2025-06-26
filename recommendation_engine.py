import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MultiLabelBinarizer
import re
from typing import List, Dict, Any
from collections import Counter

class HackathonRecommendationEngine:
    def __init__(self, appwrite_client):
        self.client = appwrite_client
        self.tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self.mlb_skills = MultiLabelBinarizer()
        
    def preprocess_skills(self, skills):
        """Convert skills to a standardized format"""
        if isinstance(skills, str):
            skills = [s.strip().lower() for s in skills.split(',')]
        elif isinstance(skills, list):
            skills = [s.strip().lower() for s in skills if s]
        else:
            skills = []
        return skills
    
    def extract_features_from_hackathon(self, hackathon):
        """Extract and combine features from hackathon data"""
        title = hackathon.get('title', '')
        organization = hackathon.get('organization', '')
        prize = hackathon.get('prize', '')
        mode = hackathon.get('mode', '')
        location = hackathon.get('location', '')
        
        # Combine text features
        text_features = f"{title} {organization} {prize} {mode} {location}"
        return text_features.lower()
    
    def calculate_skill_similarity(self, user_skills, hackathon_text):
        """Calculate similarity between user skills and hackathon content"""
        user_skills_set = set(self.preprocess_skills(user_skills))
        hackathon_text_lower = hackathon_text.lower()
        
        if not user_skills_set:
            return 0.0
        
        # Check for skill mentions in hackathon text
        skill_matches = 0
        for skill in user_skills_set:
            if skill in hackathon_text_lower:
                skill_matches += 1
        
        return skill_matches / len(user_skills_set) if user_skills_set else 0.0
    
    def calculate_location_match(self, user_location, hackathon_location):
        """Calculate location compatibility"""
        if not user_location or not hackathon_location:
            return 0.5  # neutral score
        
        user_location = user_location.lower().strip()
        hackathon_location = hackathon_location.lower().strip()
        
        if user_location == hackathon_location:
            return 1.0
        elif 'online' in hackathon_location or 'virtual' in hackathon_location:
            return 0.9
        elif any(word in hackathon_location for word in user_location.split()):
            return 0.7
        else:
            return 0.3
    
    def calculate_mode_match(self, user_mode, hackathon_mode):
        """Calculate mode compatibility (online/offline)"""
        if not user_mode or not hackathon_mode:
            return 0.5
        
        user_mode = user_mode.lower().strip()
        hackathon_mode = hackathon_mode.lower().strip()
        
        if user_mode == hackathon_mode:
            return 1.0
        elif user_mode == 'online' and hackathon_mode in ['online', 'virtual']:
            return 1.0
        elif user_mode == 'offline' and hackathon_mode in ['offline', 'physical']:
            return 1.0
        else:
            return 0.3
    
    def calculate_prize_match(self, user_prize_preference, hackathon_prize):
        """Calculate prize compatibility"""
        if not hackathon_prize:
            return 0.3
        
        hackathon_prize_lower = hackathon_prize.lower()
        
        # Extract prize amount roughly
        if any(word in hackathon_prize_lower for word in ['lakh', 'crore', '₹1,00,000', '₹2,00,000']):
            prize_level = 'high'
        elif any(word in hackathon_prize_lower for word in ['₹50000', '₹25000', '₹10000']):
            prize_level = 'medium'
        else:
            prize_level = 'low'
        
        if not user_prize_preference or user_prize_preference == 'any':
            return 0.7
        elif user_prize_preference == prize_level:
            return 1.0
        else:
            return 0.5
    
    def calculate_content_similarity(self, user_profile, hackathon):
        """Calculate content-based similarity between user profile and hackathon"""
        try:
            # Build user profile text
            user_skills = user_profile.get('skills', [])
            user_location = user_profile.get('location', '')
            user_mode = user_profile.get('mode', '')
            
            user_text = f"{' '.join(user_skills)} {user_location} {user_mode}".strip()
            
            # Build hackathon text
            hackathon_text = self.extract_features_from_hackathon(hackathon)
            
            if not user_text or not hackathon_text:
                return 0.0
            
            # Calculate TF-IDF similarity
            corpus = [user_text.lower(), hackathon_text]
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(corpus)
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return similarity
            
        except Exception as e:
            print(f"Error calculating content similarity: {e}")
            return 0.0
    
    def get_recommendations(self, user_id: str, num_recommendations: int = 10):
        """Generate hackathon recommendations using content-based filtering"""
        print(f"Generating hackathon recommendations for user: {user_id}")
        
        # Get user data
        user_data = self.client.get_user(user_id)
        if not user_data:
            print(f"User {user_id} not found")
            return []
        
        # Get all available hackathons
        hackathons_response = self.client.get_hackathons(limit=500)
        if not hackathons_response or not hackathons_response['documents']:
            print("No hackathons found in database")
            return []
        
        hackathons = hackathons_response['documents']
        print(f"Processing {len(hackathons)} total hackathons")
        
        # Extract user features
        user_skills = user_data.get('skills', [])
        user_location = user_data.get('location', '')
        user_mode_preference = user_data.get('mode_preference', 'online')
        user_prize_preference = user_data.get('prize_preference', 'any')
        
        # Calculate scores for each hackathon
        hackathon_scores = []
        
        for hackathon in hackathons:
            # Skip if hackathon doesn't have required fields
            if not hackathon.get('$id') or not hackathon.get('title'):
                continue
            
            # Calculate individual similarity scores
            skill_score = self.calculate_skill_similarity(
                user_skills, self.extract_features_from_hackathon(hackathon)
            )
            
            location_score = self.calculate_location_match(
                user_location, hackathon.get('location', '')
            )
            
            mode_score = self.calculate_mode_match(
                user_mode_preference, hackathon.get('mode', '')
            )
            
            prize_score = self.calculate_prize_match(
                user_prize_preference, hackathon.get('prize', '')
            )
            
            # Content-based similarity
            content_similarity = self.calculate_content_similarity(user_data, hackathon)
            
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
                'content_similarity': content_similarity,
                'recommendation_reason': self.get_recommendation_reason(
                    skill_score, content_similarity, location_score, mode_score
                )
            })
        
        # Sort by score and return top recommendations
        hackathon_scores.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"Generated {len(hackathon_scores)} hackathon recommendations for user {user_id}")
        
        return hackathon_scores[:num_recommendations]
    
    def get_recommendation_reason(self, skill_score, content_similarity, location_score, mode_score):
        """Generate human-readable recommendation reason"""
        if skill_score > 0.4:
            return "Matches your technical skills"
        elif content_similarity > 0.3:
            return "Similar to your interests and profile"
        elif location_score > 0.7:
            return "Perfect location match"
        elif mode_score > 0.8:
            return "Matches your preferred mode"
        else:
            return "Recommended for you"
    
    def get_filtered_recommendations(self, user_id: str, filters: Dict = None, num_recommendations: int = 10):
        """Get recommendations with additional filters"""
        recommendations = self.get_recommendations(user_id, num_recommendations * 2)
        
        if not filters:
            return recommendations[:num_recommendations]
        
        filtered_recommendations = []
        for rec in recommendations:
            hackathon = rec['hackathon']
            
            # Apply filters
            if filters.get('mode') and hackathon.get('mode') != filters['mode']:
                continue
            if filters.get('location') and filters['location'].lower() not in hackathon.get('location', '').lower():
                continue
            if filters.get('prize_range'):
                hackathon_prize = hackathon.get('prize', '').lower()
                prize_range = filters['prize_range']
                
                if prize_range == 'high' and not any(word in hackathon_prize for word in ['lakh', 'crore', '₹1,00,000']):
                    continue
                elif prize_range == 'medium' and not any(word in hackathon_prize for word in ['₹10000', '₹25000', '₹50000']):
                    continue
                elif prize_range == 'low' and not any(word in hackathon_prize for word in ['₹1000', '₹5000']):
                    continue
            
            filtered_recommendations.append(rec)
            
            if len(filtered_recommendations) >= num_recommendations:
                break
        
        return filtered_recommendations
