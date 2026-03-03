import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenFDAService:
    """
    Service for interacting with OpenFDA API
    """
    BASE_URL = "https://api.fda.gov/drug"
    
    def get_drug_warnings(self, drug_name):
        """
        Get FDA warnings for a drug
        Args:
            drug_name: Name of the drug
        Returns:
            list: Warnings or empty list
        """
        try:
            if not drug_name:
                return []
                
            # Search for the drug in the labeling endpoint
            url = f"{self.BASE_URL}/label.json"
            params = {
                'search': f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
                'limit': 1
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                warnings = []
                if results:
                    result = results[0]
                    
                    # Extract relevant warning sections
                    if result.get('warnings'):
                        warnings.append({
                            'type': 'warning',
                            'description': result['warnings'][0]
                        })
                    
                    if result.get('boxed_warnings'):
                        warnings.append({
                            'type': 'boxed_warning',
                            'description': result['boxed_warnings'][0]
                        })
                    
                    if result.get('contraindications'):
                        warnings.append({
                            'type': 'contraindication',
                            'description': result['contraindications'][0]
                        })
                
                return warnings
            else:
                logger.warning(f"OpenFDA API returned {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            logger.error(f"OpenFDA API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in OpenFDAService.get_drug_warnings: {e}")
            return []
    
    def get_adverse_events(self, drug_name):
        """
        Get adverse events for a drug
        Args:
            drug_name: Name of the drug
        Returns:
            dict: Adverse event statistics
        """
        try:
            if not drug_name:
                return {}
                
            url = f"{self.BASE_URL}/event.json"
            params = {
                'search': f'patient.drug.medicinalproduct:"{drug_name}"',
                'count': 'patient.reaction.reactionmeddrapt.exact'
            }
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'total_events': data.get('meta', {}).get('results', {}).get('total', 0),
                    'common_reactions': data.get('results', [])[:5]
                }
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting adverse events: {e}")
            return {}