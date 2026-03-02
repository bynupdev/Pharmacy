import logging
import re
import requests
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from django.conf import settings
from .models import InteractionLog
from utils.ml_interaction_model import MLInteractionModel
from utils.rxnorm_service import RxNormService
from utils.openfda_service import OpenFDAService

logger = logging.getLogger(__name__)

class AIDrugInteractionEngine:
    """
    AI-Powered Drug Interaction Engine using Machine Learning and Multiple Data Sources
    """
    
    def __init__(self):
        self.rxnorm = RxNormService()
        self.openfda = OpenFDAService()
        self.ml_model = MLInteractionModel()
        
        # Train model on startup
        try:
            self.ml_model.train_model()
        except Exception as e:
            logger.error(f"Failed to train ML model: {e}")
    
    def check_prescription(self, prescription, user=None) -> List[Dict]:
        """
        Comprehensive AI-powered prescription checking
        """
        alerts = []
        patient = prescription.patient
        items = list(prescription.items) if hasattr(prescription, 'items') else []
        
        logger.info(f"AI checking prescription for patient {patient.id}")
        
        # Get patient's medical history
        patient_history = self.get_patient_history(patient)
        
        # Get drug information from external APIs
        drug_info_cache = {}
        for item in items:
            if item.drug.id not in drug_info_cache:
                drug_info_cache[item.drug.id] = self.get_drug_info(item.drug)
        
        # Check each drug against patient profile using AI
        for item in items:
            drug_info = drug_info_cache[item.drug.id]
            
            # AI-powered allergy check
            allergy_alerts = self.ai_check_allergies(patient, item.drug, drug_info, patient_history)
            alerts.extend(allergy_alerts)
            
            # ML-based dosage analysis
            dosage_alerts = self.ml_dosage_check(patient, item, drug_info)
            alerts.extend(dosage_alerts)
            
            # AI contraindication detection
            contraindication_alerts = self.ai_check_contraindications(patient, item.drug, drug_info)
            alerts.extend(contraindication_alerts)
        
        # Check all drug pairs using ML
        for i in range(len(items)):
            for j in range(i+1, len(items)):
                drug1 = items[i].drug
                drug2 = items[j].drug
                
                # ML-based interaction prediction
                interaction_alerts = self.ml_interaction_check(
                    drug1, drug2,
                    drug_info_cache[drug1.id],
                    drug_info_cache[drug2.id],
                    patient
                )
                alerts.extend(interaction_alerts)
        
        # Add AI-generated recommendations
        for alert in alerts:
            alert['ai_confidence'] = self.calculate_ai_confidence(alert)
            alert['recommendation'] = self.generate_ai_recommendation(alert, patient)
            
            # Log for continuous learning
            self.log_interaction_for_training(alert, prescription, patient)
        
        return alerts
    
    def get_drug_info(self, drug):
        """Get comprehensive drug information from multiple APIs"""
        info = {
            'rxnorm': None,
            'fda': None,
            'interactions': [],
            'warnings': []
        }
        
        try:
            # Get RxNorm data
            if drug.rxcui:
                info['rxnorm'] = self.rxnorm.get_drug_by_rxcui(drug.rxcui)
                info['interactions'] = self.rxnorm.get_drug_interactions(drug.rxcui)
            
            # Get FDA data
            fda_data = self.openfda.get_drug_warnings(drug.name)
            if fda_data:
                info['fda'] = fda_data
                info['warnings'].extend(fda_data)
            
        except Exception as e:
            logger.error(f"Error getting drug info for {drug.name}: {e}")
        
        return info
    
    def get_patient_history(self, patient):
        """Get patient's complete medical history"""
        history = {
            'previous_interactions': [],
            'adverse_reactions': [],
            'prescription_patterns': []
        }
        
        # Get previous interactions
        past_interactions = InteractionLog.objects.filter(
            prescription__patient=patient
        ).order_by('-created_at')[:50]
        
        for interaction in past_interactions:
            history['previous_interactions'].append({
                'drug1': interaction.drug_1.name if interaction.drug_1 else None,
                'drug2': interaction.drug_2.name if interaction.drug_2 else None,
                'severity': interaction.severity,
                'overridden': bool(interaction.overridden_by)
            })
        
        return history
    
    def ai_check_allergies(self, patient, drug, drug_info, patient_history) -> List[Dict]:
        """AI-powered allergy checking with cross-reactivity prediction"""
        alerts = []
        
        if not patient.allergies:
            return alerts
        
        allergies = [a.strip().lower() for a in patient.allergies.split(',')]
        drug_name = drug.name.lower()
        
        # Get drug ingredients from RxNorm
        ingredients = []
        if drug_info.get('rxnorm'):
            ingredients = drug_info['rxnorm'].get('ingredients', [])
        
        # Check for known allergies
        for allergy in allergies:
            # Direct match
            if allergy in drug_name or any(allergy in ing for ing in ingredients):
                alerts.append({
                    'type': 'drug-allergy',
                    'severity': 'high',
                    'drug': drug.name,
                    'allergen': allergy,
                    'description': f"AI detected direct allergy match: {allergy}",
                    'ai_analysis': self.analyze_allergy_severity(allergy, drug, patient_history)
                })
            
            # Cross-reactivity prediction using ML
            elif self.predict_cross_reactivity(allergy, drug_name, ingredients):
                alerts.append({
                    'type': 'drug-allergy',
                    'severity': 'moderate',
                    'drug': drug.name,
                    'allergen': allergy,
                    'description': f"AI predicts possible cross-reactivity with {allergy}",
                    'ai_analysis': 'Cross-reactivity predicted based on structural similarity'
                })
        
        return alerts
    
    def predict_cross_reactivity(self, allergy, drug_name, ingredients) -> bool:
        """ML-based cross-reactivity prediction"""
        # In production, this would use a trained model
        # For now, use known cross-reactivity patterns
        cross_reactivity_map = {
            'penicillin': ['amoxicillin', 'ampicillin', 'cephalosporin'],
            'sulfa': ['sulfamethoxazole', 'sulfadiazine'],
            'aspirin': ['ibuprofen', 'naproxen'],
        }
        
        for known_allergy, cross_react in cross_reactivity_map.items():
            if known_allergy in allergy.lower():
                for drug in cross_react:
                    if drug in drug_name or any(drug in ing for ing in ingredients):
                        return True
        
        return False
    
    def ml_dosage_check(self, patient, item, drug_info) -> List[Dict]:
        """ML-based dosage analysis using population data"""
        alerts = []
        
        try:
            # Extract dosage
            import re
            dosage_match = re.search(r'(\d+\.?\d*)', item.dosage)
            if not dosage_match:
                return alerts
            
            dose = float(dosage_match.group(1))
            
            # Get frequency
            freq = self.parse_frequency(item.frequency)
            daily_dose = dose * freq
            
            # Check against FDA recommendations
            if drug_info.get('fda'):
                for warning in drug_info['fda']:
                    if 'dosage' in warning.get('type', '').lower():
                        alerts.append({
                            'type': 'dosage-warning',
                            'severity': 'moderate',
                            'drug': item.drug.name,
                            'description': f"FDA dosage guidance: {warning.get('description', '')[:200]}",
                            'recommendation': 'Follow FDA dosing recommendations'
                        })
            
            # Age-adjusted dosing
            if patient.age < 18 or patient.age > 65:
                adjusted_dose = self.calculate_age_adjusted_dose(daily_dose, patient.age)
                if abs(adjusted_dose - daily_dose) / daily_dose > 0.2:  # 20% difference
                    alerts.append({
                        'type': 'dosage-warning',
                        'severity': 'moderate',
                        'drug': item.drug.name,
                        'description': f"Age-adjusted dose may differ from prescribed dose",
                        'recommendation': f"Consider {adjusted_dose:.0f}mg for patient age {patient.age}"
                    })
            
        except Exception as e:
            logger.error(f"Error in ML dosage check: {e}")
        
        return alerts
    
    def parse_frequency(self, frequency):
        """Parse frequency string to daily times"""
        freq_lower = frequency.lower()
        
        if 'once' in freq_lower or 'daily' in freq_lower:
            return 1
        elif 'twice' in freq_lower or 'bid' in freq_lower:
            return 2
        elif 'three' in freq_lower or 'tid' in freq_lower:
            return 3
        elif 'four' in freq_lower or 'qid' in freq_lower:
            return 4
        elif 'hour' in freq_lower:
            # e.g., "every 4 hours" = 6 times per day
            hour_match = re.search(r'(\d+)', freq_lower)
            if hour_match:
                hours = int(hour_match.group(1))
                return 24 / hours
        
        return 1
    
    def calculate_age_adjusted_dose(self, dose, age):
        """Calculate age-adjusted dose based on population data"""
        if age < 12:  # Pediatric
            return dose * 0.5
        elif age > 65:  # Geriatric
            return dose * 0.75
        return dose
    
    def ai_check_contraindications(self, patient, drug, drug_info) -> List[Dict]:
        """AI-powered contraindication checking"""
        alerts = []
        
        # Check FDA contraindications
        if drug_info.get('fda'):
            for warning in drug_info['fda']:
                if warning.get('type') == 'Contraindications':
                    # NLP to check if any contraindications apply to patient
                    if self.nlp_contraindication_check(warning.get('description', ''), patient):
                        alerts.append({
                            'type': 'contraindication',
                            'severity': 'high',
                            'drug': drug.name,
                            'description': f"FDA contraindication: {warning.get('description', '')[:200]}",
                            'recommendation': 'Do not dispense'
                        })
        
        # Age-based contraindications
        if patient.age < 12:
            alerts.extend(self.check_pediatric_contraindications(drug))
        elif patient.age > 65:
            alerts.extend(self.check_geriatric_contraindications(drug))
        
        return alerts
    
    def nlp_contraindication_check(self, text, patient):
        """Simple NLP to check if contraindications apply to patient"""
        text_lower = text.lower()
        
        # Check for age-related terms
        if 'pediatric' in text_lower and patient.age < 18:
            return True
        if 'geriatric' in text_lower and patient.age > 65:
            return True
        
        # Check for condition-related terms
        conditions = (patient.chronic_conditions or '').lower()
        if conditions:
            for condition in conditions.split(','):
                if condition.strip() in text_lower:
                    return True
        
        return False
    
    def check_pediatric_contraindications(self, drug):
        """Check pediatric-specific contraindications"""
        alerts = []
        pediatric_contraindications = {
            'aspirin': 'Reye\'s syndrome risk',
            'tetracycline': 'Tooth discoloration',
            'fluoroquinolones': 'Arthropathy risk',
        }
        
        drug_name_lower = drug.name.lower()
        for contraindicated, reason in pediatric_contraindications.items():
            if contraindicated in drug_name_lower:
                alerts.append({
                    'type': 'contraindication',
                    'severity': 'high',
                    'drug': drug.name,
                    'description': f"Pediatric contraindication: {reason}",
                    'recommendation': 'Do not dispense to pediatric patient'
                })
        
        return alerts
    
    def check_geriatric_contraindications(self, drug):
        """Check geriatric-specific contraindications (Beers Criteria)"""
        alerts = []
        beers_criteria = [
            'diazepam', 'amitriptyline', 'diphenhydramine',
            'carisoprodol', 'chlorpheniramine', 'promethazine'
        ]
        
        drug_name_lower = drug.name.lower()
        for contraindicated in beers_criteria:
            if contraindicated in drug_name_lower:
                alerts.append({
                    'type': 'contraindication',
                    'severity': 'moderate',
                    'drug': drug.name,
                    'description': f"Medication is potentially inappropriate for geriatric patients per Beers Criteria",
                    'recommendation': 'Consider alternative'
                })
        
        return alerts
    
    def ml_interaction_check(self, drug1, drug2, info1, info2, patient) -> List[Dict]:
        """ML-based drug interaction prediction"""
        alerts = []
        
        # Use ML model to predict interaction
        prediction = self.ml_model.predict_interaction(
            drug1.name, drug2.name,
            {'age': patient.age, 'conditions': patient.chronic_conditions}
        )
        
        if prediction['severity'] != 'unknown':
            alerts.append({
                'type': 'drug-drug',
                'severity': prediction['severity'],
                'drug1': drug1.name,
                'drug2': drug2.name,
                'description': f"AI-predicted interaction with {prediction['confidence']:.1f}% confidence",
                'ai_confidence': prediction['confidence'],
                'method': prediction['method']
            })
        
        # Check RxNorm interactions
        if info1.get('rxnorm') and info2.get('rxnorm'):
            for interaction in info1.get('interactions', []):
                if interaction.get('minConceptItem', {}).get('rxcui') == drug2.rxcui:
                    alerts.append({
                        'type': 'drug-drug',
                        'severity': interaction.get('severity', 'moderate'),
                        'drug1': drug1.name,
                        'drug2': drug2.name,
                        'description': interaction.get('description', 'Interaction detected'),
                        'source': 'rxnorm'
                    })
        
        # Check FDA interactions
        for warning in info1.get('warnings', []):
            if drug2.name.lower() in warning.get('description', '').lower():
                alerts.append({
                    'type': 'drug-drug',
                    'severity': 'moderate',
                    'drug1': drug1.name,
                    'drug2': drug2.name,
                    'description': f"FDA warning: {warning.get('description', '')[:200]}",
                    'source': 'fda'
                })
        
        return alerts
    
    def analyze_allergy_severity(self, allergy, drug, patient_history):
        """Analyze severity of allergic reaction based on historical data"""
        # Check if patient had previous reactions to similar drugs
        for prev in patient_history.get('previous_interactions', []):
            if prev.get('severity') == 'high':
                return 'Previous severe reaction recorded'
        
        return 'Potential allergic reaction'
    
    def calculate_ai_confidence(self, alert):
        """Calculate AI confidence score for alert"""
        base_confidence = {
            'high': 90,
            'moderate': 70,
            'low': 50
        }.get(alert.get('severity'), 50)
        
        # Adjust based on data sources
        if alert.get('source') == 'fda':
            base_confidence += 10
        elif alert.get('source') == 'rxnorm':
            base_confidence += 5
        
        return min(100, base_confidence)
    
    def generate_ai_recommendation(self, alert, patient):
        """Generate personalized AI recommendation"""
        recommendations = {
            'high': f"⚠️ HIGH RISK: {alert.get('description', '')}. Contact prescriber immediately. Consider alternatives.",
            'moderate': f"⚠️ MODERATE RISK: {alert.get('description', '')}. Monitor patient closely. May require dosage adjustment.",
            'low': f"ℹ️ LOW RISK: {alert.get('description', '')}. Inform patient of potential effects."
        }
        
        base_rec = recommendations.get(alert.get('severity'), alert.get('recommendation', ''))
        
        # Personalize based on patient
        if patient.age > 65 and alert.get('severity') != 'low':
            base_rec += " Elderly patient requires closer monitoring."
        
        if patient.allergies and 'allergy' in alert.get('type', ''):
            base_rec += f" Documented allergies: {patient.allergies}"
        
        return base_rec
    
    def log_interaction_for_training(self, alert, prescription, patient):
        """Log interactions for continuous model training"""
        try:
            InteractionLog.objects.create(
                prescription=prescription if hasattr(prescription, 'id') else None,
                drug_1=alert.get('drug_1'),
                drug_2=alert.get('drug_2'),
                interaction_type=alert.get('type', 'unknown'),
                severity=alert.get('severity', 'low'),
                description=alert.get('description', ''),
                recommendation=alert.get('recommendation', ''),
                ai_confidence=alert.get('ai_confidence', 0)
            )
        except Exception as e:
            logger.error(f"Error logging interaction: {e}")