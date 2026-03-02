import requests
import logging
from django.conf import settings
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class RxNormService:
    """
    Service to interact with NIH RxNorm API for drug normalization and interaction data
    API Documentation: https://rxnav.nlm.nih.gov/RxNormAPIREST.html
    """
    
    BASE_URL = settings.RXNORM_API_BASE
    
    @classmethod
    def get_drug_by_name(cls, drug_name: str) -> Optional[Dict]:
        """
        Search for a drug by name and get its RxCUI
        """
        try:
            url = f"{cls.BASE_URL}/drugs"
            params = {'name': drug_name}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'drugGroup' in data and 'conceptGroup' in data['drugGroup']:
                # Extract first matching drug
                for group in data['drugGroup']['conceptGroup']:
                    if 'conceptProperties' in group:
                        return group['conceptProperties'][0]
            return None
        except requests.RequestException as e:
            logger.error(f"RxNorm API error: {e}")
            return None
    
    @classmethod
    def get_related_ingredients(cls, rxcui: str) -> List[str]:
        """
        Get all related ingredients for a given RxCUI
        """
        try:
            url = f"{cls.BASE_URL}/rxcui/{rxcui}/related"
            params = {'relaSource': 'FDA', 'relationship': 'has_ingredient'}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            ingredients = []
            
            if 'relatedGroup' in data and 'conceptGroup' in data['relatedGroup']:
                for group in data['relatedGroup']['conceptGroup']:
                    if 'conceptProperties' in group:
                        for prop in group['conceptProperties']:
                            ingredients.append(prop['name'])
            
            return ingredients
        except requests.RequestException as e:
            logger.error(f"RxNorm API error: {e}")
            return []
    
    @classmethod
    def get_drug_interactions(cls, rxcui: str) -> List[Dict]:
        """
        Get drug interactions for a given RxCUI
        Note: This uses RxNav's interaction API
        """
        try:
            url = f"{cls.BASE_URL}/interaction/list.json"
            params = {'rxcuis': rxcui}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            interactions = []
            
            if 'interactionList' in data:
                for interaction in data['interactionList']:
                    if 'interactionPair' in interaction:
                        interactions.extend(interaction['interactionPair'])
            
            return interactions
        except requests.RequestException as e:
            logger.error(f"RxNorm API error: {e}")
            return []
    
    @classmethod
    def normalize_drug_name(cls, drug_name: str) -> Optional[str]:
        """
        Normalize drug name to standard format
        """
        try:
            url = f"{cls.BASE_URL}/spellingsuggestions"
            params = {'name': drug_name}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'suggestionGroup' in data and 'suggestionList' in data['suggestionGroup']:
                suggestions = data['suggestionGroup']['suggestionList']
                if suggestions and 'suggestion' in suggestions:
                    return suggestions['suggestion'][0] if suggestions['suggestion'] else drug_name
            return drug_name
        except requests.RequestException as e:
            logger.error(f"RxNorm API error: {e}")
            return drug_name