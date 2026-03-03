import logging
import re
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from django.conf import settings

logger = logging.getLogger(__name__)

class AIDrugInteractionEngine:
    """
    AI-Powered Drug Interaction Engine - Self-contained version
    """
    
    def __init__(self):
        """Initialize the AI Drug Interaction Engine"""
        logger.info("AIDrugInteractionEngine initialized")
    
    def check_prescription(self, prescription, user=None) -> List[Dict]:
        """
        Comprehensive AI-powered prescription checking
        """
        alerts = []
        
        try:
            patient = prescription.patient
            items = list(prescription.items) if hasattr(prescription, 'items') else []
            
            logger.info(f"AI checking prescription for patient {getattr(patient, 'id', 'unknown')}")
            
            # Get patient's medical history
            patient_history = self.get_patient_history(patient)
            
            # Check each drug against patient profile
            for item in items:
                # Allergy check
                allergy_alerts = self.check_allergies(patient, item.drug)
                alerts.extend(allergy_alerts)
                
                # Dosage analysis
                dosage_alerts = self.check_dosage(patient, item)
                alerts.extend(dosage_alerts)
                
                # Contraindications
                contraindication_alerts = self.check_contraindications(patient, item.drug)
                alerts.extend(contraindication_alerts)
            
            # Check drug pairs
            items_list = list(items)
            for i in range(len(items_list)):
                for j in range(i+1, len(items_list)):
                    drug1 = items_list[i].drug
                    drug2 = items_list[j].drug
                    
                    interaction_alerts = self.check_drug_interaction(drug1, drug2)
                    alerts.extend(interaction_alerts)
            
            # Add recommendations
            for alert in alerts:
                if 'recommendation' not in alert:
                    alert['recommendation'] = self.generate_recommendation(alert, patient)
            
            logger.info(f"Generated {len(alerts)} alerts")
            
        except Exception as e:
            logger.error(f"Error in check_prescription: {e}", exc_info=True)
        
        return alerts
    
    def get_patient_history(self, patient):
        """Get patient's medical history"""
        history = {
            'previous_interactions': [],
            'adverse_reactions': [],
            'prescription_patterns': []
        }
        
        try:
            if patient and hasattr(patient, 'id'):
                # Get previous interactions
                from .models import InteractionLog
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
        except Exception as e:
            logger.error(f"Error getting patient history: {e}")
        
        return history
    
    def check_allergies(self, patient, drug) -> List[Dict]:
        """Check for drug-allergy interactions"""
        alerts = []
        
        try:
            if not patient or not hasattr(patient, 'allergies') or not patient.allergies:
                return alerts
            
            allergies = [a.strip().lower() for a in patient.allergies.split(',')]
            drug_name = drug.name.lower()
            generic_name = drug.generic_name.lower() if hasattr(drug, 'generic_name') else ''
            
            # Known drug families for cross-reactivity
            drug_families = {
                'penicillin': ['amoxicillin', 'ampicillin', 'penicillin', 'amoxil', 'augmentin'],
                'cephalosporin': ['cephalexin', 'cefadroxil', 'cefuroxime', 'cefixime'],
                'sulfa': ['sulfamethoxazole', 'sulfadiazine', 'bactrim', 'septra'],
                'nsaid': ['ibuprofen', 'naproxen', 'diclofenac', 'ketorolac', 'aspirin'],
            }
            
            for allergy in allergies:
                # Direct match
                if allergy and (allergy in drug_name or allergy in generic_name):
                    alerts.append({
                        'type': 'drug-allergy',
                        'severity': 'high',
                        'drug': drug.name,
                        'allergen': allergy,
                        'description': f'Patient is allergic to {allergy}, which matches {drug.name}',
                        'recommendation': 'DO NOT DISPENSE. Choose alternative medication.'
                    })
                    continue
                
                # Check drug families
                for family, drugs in drug_families.items():
                    if allergy == family or allergy in drugs:
                        for family_drug in drugs:
                            if family_drug in drug_name or family_drug in generic_name:
                                alerts.append({
                                    'type': 'drug-allergy',
                                    'severity': 'high',
                                    'drug': drug.name,
                                    'allergen': allergy,
                                    'description': f'Patient is allergic to {allergy} ({family} family). {drug.name} may cause cross-reaction.',
                                    'recommendation': 'DO NOT DISPENSE. Choose alternative from different drug family.'
                                })
                                break
        except Exception as e:
            logger.error(f"Error checking allergies: {e}")
        
        return alerts
    
    def check_dosage(self, patient, item) -> List[Dict]:
        """Check for dosage warnings"""
        alerts = []
        
        try:
            # Check for high quantity
            if hasattr(item, 'quantity') and item.quantity:
                if item.quantity > 100:
                    alerts.append({
                        'type': 'dosage-warning',
                        'severity': 'moderate',
                        'drug': item.drug.name,
                        'description': f'High quantity prescribed: {item.quantity} units',
                        'recommendation': 'Verify prescription with prescriber - unusually high quantity'
                    })
                elif item.quantity > 500:
                    alerts.append({
                        'type': 'dosage-warning',
                        'severity': 'high',
                        'drug': item.drug.name,
                        'description': f'Extremely high quantity: {item.quantity} units',
                        'recommendation': 'CONTACT PRESCRIBER IMMEDIATELY - quantity seems excessive'
                    })
            
            # Check frequency
            if hasattr(item, 'frequency') and item.frequency:
                freq_lower = item.frequency.lower()
                
                # Parse frequency for warnings
                if 'hour' in freq_lower:
                    hour_match = re.search(r'(\d+)', freq_lower)
                    if hour_match:
                        hours = int(hour_match.group(1))
                        if hours < 2:
                            alerts.append({
                                'type': 'dosage-warning',
                                'severity': 'high',
                                'drug': item.drug.name,
                                'description': f'Extremely frequent dosing: every {hours} hours',
                                'recommendation': 'VERIFY WITH PRESCRIBER - this frequency is unusual'
                            })
                        elif hours < 4:
                            alerts.append({
                                'type': 'dosage-warning',
                                'severity': 'moderate',
                                'drug': item.drug.name,
                                'description': f'Very frequent dosing: every {hours} hours',
                                'recommendation': 'Verify frequency is correct'
                            })
                
                # Check for numeric-only frequency (like "40" in your test)
                if freq_lower.isdigit():
                    times = int(freq_lower)
                    if times > 10:
                        alerts.append({
                            'type': 'dosage-warning',
                            'severity': 'high',
                            'drug': item.drug.name,
                            'description': f'Unusual frequency: {times} times daily',
                            'recommendation': 'Verify frequency format - should be text (e.g., "twice daily") not a number'
                        })
            
            # Age-based dosing
            if hasattr(patient, 'age') and patient.age:
                if patient.age < 12 and item.quantity > 30:
                    alerts.append({
                        'type': 'dosage-warning',
                        'severity': 'moderate',
                        'drug': item.drug.name,
                        'description': f'Pediatric patient - high quantity: {item.quantity} units',
                        'recommendation': 'Verify pediatric dosage is appropriate'
                    })
        except Exception as e:
            logger.error(f"Error checking dosage: {e}")
        
        return alerts
    
    def check_contraindications(self, patient, drug) -> List[Dict]:
        """Check for contraindications"""
        alerts = []
        
        try:
            # Age-based contraindications
            if hasattr(patient, 'age') and patient.age:
                drug_lower = drug.name.lower()
                
                # Pediatric contraindications
                if patient.age < 18:
                    pediatric_risk = {
                        'aspirin': 'Reye\'s syndrome risk',
                        'tetracycline': 'Tooth discoloration',
                        'fluoroquinolones': 'Arthropathy risk',
                        'doxycycline': 'Tooth discoloration',
                    }
                    
                    for risk_drug, reason in pediatric_risk.items():
                        if risk_drug in drug_lower:
                            alerts.append({
                                'type': 'contraindication',
                                'severity': 'high',
                                'drug': drug.name,
                                'description': f'Pediatric contraindication: {reason}',
                                'recommendation': 'Do not dispense to pediatric patient'
                            })
                
                # Geriatric contraindications (Beers Criteria)
                elif patient.age > 65:
                    beers_criteria = [
                        'diazepam', 'amitriptyline', 'diphenhydramine',
                        'carisoprodol', 'chlorpheniramine', 'promethazine'
                    ]
                    
                    for risk_drug in beers_criteria:
                        if risk_drug in drug_lower:
                            alerts.append({
                                'type': 'contraindication',
                                'severity': 'moderate',
                                'drug': drug.name,
                                'description': 'Medication potentially inappropriate for elderly (Beers Criteria)',
                                'recommendation': 'Consider alternative with better safety profile'
                            })
        except Exception as e:
            logger.error(f"Error checking contraindications: {e}")
        
        return alerts
    
    def check_drug_interaction(self, drug1, drug2) -> List[Dict]:
        """Check for drug-drug interactions"""
        alerts = []
        
        try:
            drug1_lower = drug1.name.lower()
            drug2_lower = drug2.name.lower()
            
            # Severe interactions (must avoid)
            severe_interactions = [
                ('warfarin', 'aspirin', 'Increased bleeding risk'),
                ('warfarin', 'ibuprofen', 'Increased bleeding risk'),
                ('warfarin', 'amoxicillin', 'Increased INR - bleeding risk'),
                ('methotrexate', 'aspirin', 'Methotrexate toxicity'),
                ('methotrexate', 'amoxicillin', 'Reduced methotrexate excretion - toxicity risk'),
                ('amoxicillin', 'probenecid', 'Increased amoxicillin levels'),
                ('simvastatin', 'clarithromycin', 'Rhabdomyolysis risk'),
                ('sildenafil', 'nitrates', 'Severe hypotension'),
                ('lithium', 'thiazide', 'Lithium toxicity'),
                ('digoxin', 'verapamil', 'Digoxin toxicity'),
            ]
            
            for d1, d2, desc in severe_interactions:
                if (d1 in drug1_lower and d2 in drug2_lower) or (d1 in drug2_lower and d2 in drug1_lower):
                    alerts.append({
                        'type': 'drug-drug',
                        'severity': 'high',
                        'drug1': drug1.name,
                        'drug2': drug2.name,
                        'description': f'SEVERE INTERACTION: {desc}',
                        'recommendation': 'AVOID CONCURRENT USE. Contact prescriber immediately.'
                    })
                    return alerts  # Return after first severe interaction
            
            # Moderate interactions (caution advised)
            moderate_interactions = [
                ('metformin', 'contrast', 'Risk of lactic acidosis with contrast dye'),
                ('lisinopril', 'potassium', 'Hyperkalemia risk'),
                ('levothyroxine', 'calcium', 'Reduced levothyroxine absorption'),
                ('albuterol', 'beta_blocker', 'Reduced bronchodilator effect'),
                ('fluoxetine', 'tramadol', 'Serotonin syndrome risk'),
            ]
            
            for d1, d2, desc in moderate_interactions:
                if (d1 in drug1_lower and d2 in drug2_lower) or (d1 in drug2_lower and d2 in drug1_lower):
                    alerts.append({
                        'type': 'drug-drug',
                        'severity': 'moderate',
                        'drug1': drug1.name,
                        'drug2': drug2.name,
                        'description': f'Moderate interaction: {desc}',
                        'recommendation': 'Monitor patient closely. May require dosage adjustment.'
                    })
        except Exception as e:
            logger.error(f"Error checking drug interaction: {e}")
        
        return alerts
    
    def generate_recommendation(self, alert, patient):
        """Generate recommendation based on alert and patient"""
        severity = alert.get('severity', 'low')
        
        recommendations = {
            'high': '⚠️ HIGH RISK: Contact prescriber immediately. Do not dispense until verified.',
            'moderate': '⚠️ MODERATE RISK: Monitor patient closely. Consider dosage adjustment.',
            'low': 'ℹ️ LOW RISK: Inform patient of potential effects. Routine monitoring advised.'
        }
        
        base_rec = recommendations.get(severity, 'Review prescription carefully.')
        
        # Personalize based on patient
        if hasattr(patient, 'age') and patient.age:
            if patient.age > 65 and severity != 'low':
                base_rec += ' Elderly patient requires closer monitoring.'
            elif patient.age < 12 and severity != 'low':
                base_rec += ' Pediatric patient - verify dosage carefully.'
        
        if hasattr(patient, 'allergies') and patient.allergies and 'allergy' in alert.get('type', ''):
            base_rec += f' Documented allergies: {patient.allergies}'
        
        return base_rec