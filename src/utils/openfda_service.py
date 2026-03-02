import requests
import logging
from django.conf import settings
from typing import Optional, Dict, List
import time

logger = logging.getLogger(__name__)

class OpenFDAService:
    """
    Service to interact with OpenFDA Drug Label API
    API Documentation: https://open.fda.gov/apis/drug/label/
    Rate limits: 240 requests per minute (default)
    """
    
    BASE_URL = settings.OPENFDA_API_BASE
    RATE_LIMIT_DELAY = 0.25  # 4 requests per second
    
    @classmethod
    def _make_request(cls, params: Dict) -> Optional[Dict]:
        """
        Make rate-limited request to OpenFDA API
        """
        try:
            time.sleep(cls.RATE_LIMIT_DELAY)  # Rate limiting
            response = requests.get(cls.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                logger.warning("Rate limit hit, waiting longer...")
                time.sleep(2)  # Wait longer and retry
                try:
                    response = requests.get(cls.BASE_URL, params=params, timeout=15)
                    response.raise_for_status()
                    return response.json()
                except:
                    return None
            return None
        except requests.RequestException as e:
            logger.error(f"OpenFDA API error: {e}")
            return None
    
    @classmethod
    def get_drug_warnings(cls, drug_name: str) -> List[Dict]:
        """
        Get warnings for a specific drug
        """
        params = {
            'search': f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
            'limit': 1
        }
        
        data = cls._make_request(params)
        if not data or 'results' not in data or not data['results']:
            return []
        
        result = data['results'][0]
        warnings = []
        
        # Extract various warning sections
        warning_fields = [
            ('warnings', 'Warnings'),
            ('boxed_warning', 'Boxed Warning'),
            ('contraindications', 'Contraindications'),
            ('precautions', 'Precautions'),
            ('adverse_reactions', 'Adverse Reactions'),
            ('drug_interactions', 'Drug Interactions')
        ]
        
        for field, label in warning_fields:
            if field in result:
                warnings.append({
                    'type': label,
                    'description': result[field]
                })
        
        return warnings
    
    @classmethod
    def get_contraindications(cls, drug_name: str) -> List[str]:
        """
        Get contraindications for a drug
        """
        params = {
            'search': f'openfda.brand_name:"{drug_name}" AND _exists_:contraindications',
            'limit': 1
        }
        
        data = cls._make_request(params)
        if data and 'results' in data and data['results']:
            result = data['results'][0]
            if 'contraindications' in result:
                return result['contraindications']
        
        return []
    
    @classmethod
    def get_dosage_info(cls, drug_name: str) -> Optional[Dict]:
        """
        Get dosage information for a drug
        """
        params = {
            'search': f'openfda.brand_name:"{drug_name}" AND _exists_:dosage_and_administration',
            'limit': 1
        }
        
        data = cls._make_request(params)
        if data and 'results' in data and data['results']:
            result = data['results'][0]
            return {
                'dosage': result.get('dosage_and_administration', [''])[0],
                'form': result.get('dosage_form', [''])[0],
                'strength': result.get('active_ingredient', [''])[0]
            }
        
        return None
    
    @classmethod
    def search_drug_interactions(cls, drug1: str, drug2: str) -> Optional[Dict]:
        """
        Search for interactions between two drugs
        """
        # This is a simplified implementation
        # OpenFDA doesn't directly provide drug-drug interactions
        # We can look for warnings that mention both drugs
        params = {
            'search': f'openfda.brand_name:"{drug1}" AND (warnings:"{drug2}" OR drug_interactions:"{drug2}")',
            'limit': 1
        }
        
        data = cls._make_request(params)
        if data and 'results' in data and data['results']:
            result = data['results'][0]
            return {
                'drug1': drug1,
                'drug2': drug2,
                'warnings': result.get('warnings', [''])[0] if 'warnings' in result else '',
                'interactions': result.get('drug_interactions', [''])[0] if 'drug_interactions' in result else ''
            }
        
        return None