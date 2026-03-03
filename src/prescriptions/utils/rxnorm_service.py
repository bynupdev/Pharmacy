import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class RxNormService:
    """
    Service for interacting with RxNorm API
    """
    BASE_URL = "https://rxnav.nlm.nih.gov/REST"
    
    def __init__(self):
        logger.info("RxNormService initialized")
    
    def get_drug_by_rxcui(self, rxcui):
        """
        Get drug properties by RxCUI
        Args:
            rxcui: RxNorm Concept Unique Identifier
        Returns:
            dict: Drug properties or None
        """
        try:
            if not rxcui:
                logger.warning("No rxcui provided")
                return None
                
            logger.info(f"Fetching drug info for rxcui: {rxcui}")
            url = f"{self.BASE_URL}/rxcui/{rxcui}/properties"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                properties = data.get('properties', {})
                logger.info(f"Found drug: {properties.get('name')}")
                return properties
            else:
                logger.warning(f"RxNorm API returned {response.status_code} for rxcui {rxcui}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"RxNorm API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_drug_by_rxcui: {e}")
            return None
    
    def get_drug_interactions(self, rxcui):
        """
        Get drug interactions by RxCUI
        Args:
            rxcui: RxNorm Concept Unique Identifier
        Returns:
            list: Interactions or empty list
        """
        try:
            if not rxcui:
                return []
                
            logger.info(f"Fetching interactions for rxcui: {rxcui}")
            url = f"{self.BASE_URL}/interaction/list.json?rxcuis={rxcui}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                interactions = data.get('fullInteractionTypeGroup', [])
                logger.info(f"Found {len(interactions)} interaction groups")
                return interactions
            else:
                logger.warning(f"RxNorm interaction API returned {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"RxNorm interaction API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in get_drug_interactions: {e}")
            return []
    
    def search_by_name(self, name):
        """
        Search for drugs by name
        Args:
            name: Drug name to search for
        Returns:
            list: Matching drugs
        """
        try:
            if not name or len(name) < 2:
                return []
                
            logger.info(f"Searching for drug: {name}")
            url = f"{self.BASE_URL}/drugs?name={name}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                drug_group = data.get('drugGroup', {})
                concepts = []
                
                # Extract all concept groups
                for group in drug_group.get('conceptGroup', []):
                    concepts.extend(group.get('conceptProperties', []))
                
                logger.info(f"Found {len(concepts)} matches")
                return concepts
            else:
                logger.warning(f"RxNorm search API returned {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"RxNorm search API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in search_by_name: {e}")
            return []
    
    def get_spelling_suggestions(self, term):
        """
        Get spelling suggestions for a drug term
        Args:
            term: Search term
        Returns:
            list: Spelling suggestions
        """
        try:
            if not term:
                return []
                
            url = f"{self.BASE_URL}/spellingsuggestions.json?name={term}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                suggestions = data.get('suggestionGroup', {}).get('suggestionList', {}).get('suggestion', [])
                return suggestions
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error getting spelling suggestions: {e}")
            return []
    
    def get_all_related_info(self, rxcui):
        """
        Get all related information for a drug (combines multiple endpoints)
        Args:
            rxcui: RxNorm Concept Unique Identifier
        Returns:
            dict: Complete drug information
        """
        try:
            if not rxcui:
                return {}
                
            info = {
                'properties': self.get_drug_by_rxcui(rxcui),
                'interactions': self.get_drug_interactions(rxcui),
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting all related info: {e}")
            return {}