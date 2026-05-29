"""
FDA openFDA Drug Label API Integration
Retrieves official dosage information for drug safety checking
Free API - No authentication required
"""

import requests
import json
import re
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class FDADosageAPI:
    """
    Interface to the FDA openFDA Drug Label API
    Documentation: https://open.fda.gov/apis/drug/label/
    """
    
    BASE_URL = "https://api.fda.gov/drug/label.json"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PharmacyApp/1.0 (Educational Use Only)'
        })
    
    def search_by_drug_name(self, drug_name: str) -> Optional[Dict]:
        """
        Search for drug label information by drug name
        Returns structured label data or None if not found
        """
        try:
            # Clean and format drug name for search
            clean_name = drug_name.strip().upper()
            
            # Search by brand name OR generic name
            response = self.session.get(
                self.BASE_URL,
                params={
                    'search': f'openfda.brand_name.exact:"{clean_name}" OR openfda.generic_name.exact:"{clean_name}"',
                    'limit': 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    return data['results'][0]
            
            # If exact match fails, try partial match
            response = self.session.get(
                self.BASE_URL,
                params={
                    'search': f'openfda.brand_name:"{clean_name}"',
                    'limit': 1
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    return data['results'][0]
                    
        except requests.exceptions.RequestException as e:
            logger.error(f"FDA API request failed: {e}")
        
        return None
    
    def extract_dosage_info(self, drug_name: str) -> Dict:
        """
        Extract structured dosage information from drug label
        Returns dosage limits and recommendations
        """
        result = {
            'drug_name': drug_name,
            'found': False,
            'dosage_and_administration': None,
            'indications': None,
            'contraindications': None,
            'warnings': None,
            'max_daily_dose': None,
            'recommended_dose': None,
            'dosage_form': None,
            'route': None
        }
        
        label = self.search_by_drug_name(drug_name)
        
        if not label:
            return result
        
        result['found'] = True
        
        # Extract standard label sections using LOINC codes
        # openFDA returns these as arrays of strings
        
        # Dosage and Administration (LOINC 34068-7)
        if label.get('dosage_and_administration'):
            dosage_text = ' '.join(label['dosage_and_administration'])
            result['dosage_and_administration'] = dosage_text[:500]  # Truncate for display
            result = self._parse_dosage_text(dosage_text, result)
        
        # Indications and Usage (LOINC 34067-9)
        if label.get('indications_and_usage'):
            result['indications'] = ' '.join(label['indications_and_usage'])[:300]
        
        # Contraindications (LOINC 34070-3)
        if label.get('contraindications'):
            result['contraindications'] = ' '.join(label['contraindications'])[:300]
        
        # Warnings (LOINC 34071-1)
        if label.get('warnings'):
            result['warnings'] = ' '.join(label['warnings'])[:300]
        
        # Extract from openfda metadata
        if label.get('openfda'):
            openfda = label['openfda']
            if openfda.get('generic_name'):
                result['generic_name'] = openfda['generic_name'][0] if isinstance(openfda['generic_name'], list) else openfda['generic_name']
            if openfda.get('route'):
                result['route'] = openfda['route'][0] if isinstance(openfda['route'], list) else openfda['route']
            if openfda.get('dosage_form'):
                result['dosage_form'] = openfda['dosage_form'][0] if isinstance(openfda['dosage_form'], list) else openfda['dosage_form']
        
        return result
    
    def _parse_dosage_text(self, dosage_text: str, result: Dict) -> Dict:
        """
        Parse unstructured dosage text to extract numeric limits
        Uses pattern matching to find common dosage patterns
        """
        import re
        
        # Pattern for "X mg" or "X mg per day" etc.
        # Look for maximum daily dose patterns
        max_daily_patterns = [
            r'maximum\s+(?:daily|per\s+day|in\s+24\s+hours)?\s+dose\s+(?:is\s+)?(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
            r'not\s+to\s+exceed\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g)\s+per\s+day',
            r'max\s*:\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
            r'daily\s+dose\s+should\s+not\s+exceed\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
            r'do\s+not\s+exceed\s+(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
        ]
        
        for pattern in max_daily_patterns:
            match = re.search(pattern, dosage_text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                unit = match.group(2).lower()
                
                # Convert to mg for comparison
                if unit == 'g':
                    amount *= 1000
                elif unit == 'mcg':
                    amount /= 1000
                
                result['max_daily_dose_mg'] = amount
                break
        
        # Look for typical dose ranges
        dose_patterns = [
            r'usual\s+adult\s+dose\s*:\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
            r'recommended\s+dose\s*(?:is)?\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
            r'initial\s+dose\s*:\s*(\d+(?:\.\d+)?)\s*(mg|mcg|g)',
        ]
        
        for pattern in dose_patterns:
            match = re.search(pattern, dosage_text, re.IGNORECASE)
            if match:
                amount = float(match.group(1))
                unit = match.group(2).lower()
                
                if unit == 'g':
                    amount *= 1000
                elif unit == 'mcg':
                    amount /= 1000
                
                result['recommended_dose_mg'] = amount
                break
        
        return result
    
    def check_dosage_safety(self, drug_name: str, prescribed_dose_mg: float, frequency_per_day: int) -> Dict:
        """
        Check if a prescribed dose is safe based on FDA labeling
        Returns safety assessment with recommendations
        """
        result = {
            'drug_name': drug_name,
            'prescribed_daily_mg': prescribed_dose_mg * frequency_per_day,
            'prescribed_single_mg': prescribed_dose_mg,
            'is_safe': True,
            'severity': None,
            'warnings': [],
            'fda_max_daily': None,
            'fda_recommended': None
        }
        
        dosage_info = self.extract_dosage_info(drug_name)
        
        if not dosage_info['found']:
            result['warnings'].append(f"FDA data not found for {drug_name}. Cannot verify dosage safety.")
            return result
        
        if dosage_info.get('max_daily_dose_mg'):
            result['fda_max_daily'] = dosage_info['max_daily_dose_mg']
            daily_dose = prescribed_dose_mg * frequency_per_day
            
            if daily_dose > dosage_info['max_daily_dose_mg']:
                result['is_safe'] = False
                result['severity'] = 'high'
                result['warnings'].append(
                    f"Daily dose of {daily_dose}mg exceeds FDA maximum of {dosage_info['max_daily_dose_mg']}mg"
                )
        
        if dosage_info.get('recommended_dose_mg'):
            result['fda_recommended'] = dosage_info['recommended_dose_mg']
            
            if prescribed_dose_mg > dosage_info['recommended_dose_mg'] * 1.5:
                if not result.get('severity'):
                    result['severity'] = 'moderate'
                result['warnings'].append(
                    f"Dose ({prescribed_dose_mg}mg) exceeds typical recommended dose of {dosage_info['recommended_dose_mg']}mg"
                )
        
        if dosage_info.get('contraindications'):
            result['contraindications'] = dosage_info['contraindications']
        
        return result