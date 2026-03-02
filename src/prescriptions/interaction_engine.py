# import logging
# from typing import List, Dict, Tuple, Optional
# from datetime import date
# from django.contrib.auth.models import User
# from patients.models import Patient
# from inventory.models import Drug
# from prescriptions.models import Prescription, PrescriptionItem, InteractionLog
# from utils.rxnorm_service import RxNormService
# from utils.openfda_service import OpenFDAService

# logger = logging.getLogger(__name__)

# class DrugInteractionEngine:
#     """
#     AI-powered drug interaction checking engine
#     Combines rule-based checks, database lookups, and API calls
#     """
    
#     # Severe interaction pairs (rule-based)
#     SEVERE_INTERACTIONS = [
#         ('warfarin', 'aspirin'),
#         ('warfarin', 'ibuprofen'),
#         ('methotrexate', 'aspirin'),
#         ('lithium', 'thiazide'),
#         ('digoxin', 'verapamil'),
#         ('theophylline', 'ciprofloxacin'),
#         ('phenytoin', 'warfarin'),
#         ('clopidogrel', 'omeprazole'),
#         ('simvastatin', 'clarithromycin'),
#         ('sildenafil', 'nitrates'),
#     ]
    
#     # Moderate interaction pairs
#     MODERATE_INTERACTIONS = [
#         ('metformin', 'contrast_dye'),
#         ('lisinopril', 'potassium'),
#         ('levothyroxine', 'calcium'),
#         ('albuterol', 'beta_blockers'),
#         ('fluoxetine', 'tramadol'),
#     ]
    
#     # Age-based dosage limits (simplified)
#     AGE_DOSAGE_LIMITS = {
#         'pediatric': {'max_age': 12, 'factor': 0.5},
#         'adult': {'min_age': 18, 'max_age': 65, 'factor': 1.0},
#         'geriatric': {'min_age': 65, 'factor': 0.75}
#     }
    
#     def __init__(self):
#         self.rxnorm = RxNormService()
#         self.openfda = OpenFDAService()
    
#     def check_prescription(self, prescription: Prescription, user: Optional[User] = None) -> List[Dict]:
#         """
#         Main entry point for checking all interactions in a prescription
#         Returns list of interaction alerts
#         """
#         alerts = []
#         items = prescription.items.select_related('drug').all()
        
#         if len(items) < 1:
#             return alerts
        
#         # Check each drug against patient profile
#         for item in items:
#             # Drug-allergy checks
#             allergy_alerts = self.check_allergies(prescription.patient, item.drug)
#             alerts.extend(allergy_alerts)
            
#             # Dosage warnings
#             dosage_alerts = self.check_dosage(prescription.patient, item)
#             alerts.extend(dosage_alerts)
            
#             # Age-based contraindications
#             age_alerts = self.check_age_contraindications(prescription.patient, item.drug)
#             alerts.extend(age_alerts)
        
#         # Check drug-drug interactions (pairs)
#         for i in range(len(items)):
#             for j in range(i+1, len(items)):
#                 drug1 = items[i].drug
#                 drug2 = items[j].drug
                
#                 interaction_alerts = self.check_drug_interaction(drug1, drug2)
#                 alerts.extend(interaction_alerts)
        
#         # Add risk scores
#         for alert in alerts:
#             alert['risk_score'] = self.calculate_risk_score(alert)
        
#         # Log interactions if user provided
#         if user:
#             self.log_interactions(prescription, alerts, user)
        
#         return alerts
    
#     def check_allergies(self, patient: Patient, drug: Drug) -> List[Dict]:
#         """
#         Check if drug conflicts with patient allergies
#         """
#         alerts = []
        
#         if not patient.allergies:
#             return alerts
        
#         # Parse patient allergies
#         allergies = [a.strip().lower() for a in patient.allergies.split(',')]
        
#         # Check drug name against allergies
#         drug_name_lower = drug.name.lower()
#         generic_name_lower = drug.generic_name.lower()
        
#         # Get related ingredients from RxNorm
#         related_ingredients = []
#         if drug.rxcui:
#             related_ingredients = self.rxnorm.get_related_ingredients(drug.rxcui)
        
#         for allergy in allergies:
#             # Direct match
#             if allergy in drug_name_lower or allergy in generic_name_lower:
#                 alerts.append({
#                     'type': 'drug-allergy',
#                     'severity': 'high',
#                     'drug': drug.name,
#                     'allergen': allergy,
#                     'description': f"Patient is allergic to {allergy}, which is present in {drug.name}",
#                     'recommendation': "Do not dispense. Consider alternative medication."
#                 })
            
#             # Related ingredients check
#             for ingredient in related_ingredients:
#                 if allergy in ingredient.lower():
#                     alerts.append({
#                         'type': 'drug-allergy',
#                         'severity': 'high',
#                         'drug': drug.name,
#                         'allergen': allergy,
#                         'description': f"Patient is allergic to {allergy}, which is related to {drug.name}",
#                         'recommendation': "Verify with prescribing physician before dispensing."
#                     })
        
#         return alerts
    
#     def check_dosage(self, patient: Patient, item: PrescriptionItem) -> List[Dict]:
#         """
#         Check for dosage warnings
#         """
#         alerts = []
        
#         # Parse dosage quantity
#         try:
#             # Extract numeric part from dosage (e.g., "1 tablet" -> 1)
#             dosage_parts = item.dosage.split()
#             if dosage_parts and dosage_parts[0].isdigit():
#                 quantity = int(dosage_parts[0])
#             else:
#                 return alerts
#         except:
#             return alerts
        
#         # Simple overdose check (quantity > 2 tablets per dose)
#         if quantity > 2:
#             alerts.append({
#                 'type': 'dosage-warning',
#                 'severity': 'moderate',
#                 'drug': item.drug.name,
#                 'description': f"High dosage: {item.dosage} {item.frequency}",
#                 'recommendation': "Verify dosage with prescribing physician."
#             })
        
#         # Check against age-based limits
#         if patient.age < 12:  # Pediatric
#             if quantity > 1:
#                 alerts.append({
#                     'type': 'dosage-warning',
#                     'severity': 'high',
#                     'drug': item.drug.name,
#                     'description': f"Pediatric dosage may be too high: {item.dosage}",
#                     'recommendation': "Consult pediatric dosage guidelines."
#                 })
#         elif patient.age > 65:  # Geriatric
#             # Check OpenFDA for geriatric dosing
#             dosage_info = self.openfda.get_dosage_info(item.drug.name)
#             if dosage_info and 'geriatric' in dosage_info.get('dosage', '').lower():
#                 # Already handled in label
#                 pass
        
#         return alerts
    
#     def check_age_contraindications(self, patient: Patient, drug: Drug) -> List[Dict]:
#         """
#         Check if drug is contraindicated for patient's age
#         """
#         alerts = []
        
#         # Get contraindications from OpenFDA
#         contraindications = self.openfda.get_contraindications(drug.name)
        
#         for contra in contraindications:
#             contra_lower = contra.lower()
            
#             # Check for age-related contraindications
#             if 'pediatric' in contra_lower and patient.age < 18:
#                 alerts.append({
#                     'type': 'contraindication',
#                     'severity': 'high',
#                     'drug': drug.name,
#                     'description': f"Drug is contraindicated in pediatric patients: {contra[:100]}...",
#                     'recommendation': "Do not dispense for this patient."
#                 })
#             elif 'geriatric' in contra_lower and patient.age > 65:
#                 alerts.append({
#                     'type': 'contraindication',
#                     'severity': 'moderate',
#                     'drug': drug.name,
#                     'description': f"Use with caution in geriatric patients: {contra[:100]}...",
#                     'recommendation': "Consider reduced dosage or alternative."
#                 })
        
#         return alerts
    
#     def check_drug_interaction(self, drug1: Drug, drug2: Drug) -> List[Dict]:
#         """
#         Check for interactions between two drugs
#         Combines rule-based and API-based checks
#         """
#         alerts = []
        
#         # Rule-based check for severe interactions
#         drug1_name_lower = drug1.name.lower()
#         drug2_name_lower = drug2.name.lower()
        
#         for severe_pair in self.SEVERE_INTERACTIONS:
#             if (severe_pair[0] in drug1_name_lower and severe_pair[1] in drug2_name_lower) or \
#                (severe_pair[0] in drug2_name_lower and severe_pair[1] in drug1_name_lower):
#                 alerts.append({
#                     'type': 'drug-drug',
#                     'severity': 'high',
#                     'drug1': drug1.name,
#                     'drug2': drug2.name,
#                     'description': f"Severe interaction between {drug1.name} and {drug2.name}",
#                     'recommendation': "Avoid concurrent use. Consider alternative therapy."
#                 })
#                 return alerts
        
#         # Check moderate interactions
#         for moderate_pair in self.MODERATE_INTERACTIONS:
#             if (moderate_pair[0] in drug1_name_lower and moderate_pair[1] in drug2_name_lower) or \
#                (moderate_pair[0] in drug2_name_lower and moderate_pair[1] in drug1_name_lower):
#                 alerts.append({
#                     'type': 'drug-drug',
#                     'severity': 'moderate',
#                     'drug1': drug1.name,
#                     'drug2': drug2.name,
#                     'description': f"Moderate interaction between {drug1.name} and {drug2.name}",
#                     'recommendation': "Monitor patient closely or adjust dosage."
#                 })
#                 return alerts
        
#         # API-based check using RxNorm
#         if drug1.rxcui and drug2.rxcui:
#             interactions = self.rxnorm.get_drug_interactions(drug1.rxcui)
#             for interaction in interactions:
#                 if interaction.get('minConceptItem', {}).get('rxcui') == drug2.rxcui:
#                     severity = interaction.get('severity', 'unknown')
#                     alerts.append({
#                         'type': 'drug-drug',
#                         'severity': severity.lower() if severity in ['high', 'moderate', 'low'] else 'moderate',
#                         'drug1': drug1.name,
#                         'drug2': drug2.name,
#                         'description': interaction.get('description', f"Interaction between {drug1.name} and {drug2.name}"),
#                         'recommendation': "Review interaction details with physician."
#                     })
        
#         # Check OpenFDA for interactions
#         if not alerts:
#             fda_interaction = self.openfda.search_drug_interactions(drug1.name, drug2.name)
#             if fda_interaction and fda_interaction.get('interactions'):
#                 alerts.append({
#                     'type': 'drug-drug',
#                     'severity': 'moderate',
#                     'drug1': drug1.name,
#                     'drug2': drug2.name,
#                     'description': f"FDA warning: {fda_interaction['interactions'][:200]}...",
#                     'recommendation': "Review FDA labeling information."
#                 })
        
#         return alerts
    
#     def calculate_risk_score(self, alert: Dict) -> int:
#         """
#         Calculate numeric risk score (1-100)
#         """
#         severity_scores = {
#             'high': 80,
#             'moderate': 50,
#             'low': 20
#         }
        
#         base_score = severity_scores.get(alert.get('severity', 'low'), 20)
        
#         # Adjust based on interaction type
#         type_multipliers = {
#             'drug-drug': 1.2,
#             'drug-allergy': 1.5,
#             'contraindication': 1.3,
#             'dosage-warning': 0.8
#         }
        
#         multiplier = type_multipliers.get(alert.get('type', ''), 1.0)
        
#         return min(100, int(base_score * multiplier))
    
#     def log_interactions(self, prescription: Prescription, alerts: List[Dict], user: User):
#         """
#         Log all detected interactions to database
#         """
#         for alert in alerts:
#             InteractionLog.objects.create(
#                 prescription=prescription,
#                 drug_1=Drug.objects.filter(name=alert.get('drug', alert.get('drug1', ''))).first(),
#                 drug_2=Drug.objects.filter(name=alert.get('drug2', '')).first() if alert.get('drug2') else None,
#                 interaction_type=alert['type'],
#                 severity=alert['severity'],
#                 description=alert['description'],
#                 recommendation=alert.get('recommendation', 'Consult healthcare provider')
#             )
    
#     def override_interaction(self, log_id: int, user: User, reason: str):
#         """
#         Allow pharmacist to override an interaction alert
#         """
#         try:
#             log = InteractionLog.objects.get(id=log_id)
#             log.overridden_by = user
#             log.overridden_at = date.today()
#             log.override_reason = reason
#             log.save()
            
#             logger.info(f"Interaction {log_id} overridden by {user.username}: {reason}")
#             return True
#         except InteractionLog.DoesNotExist:
#             logger.error(f"Interaction log {log_id} not found")
#             return False


import logging
from typing import List, Dict, Tuple, Optional
from datetime import date
from django.contrib.auth.models import User
from patients.models import Patient
from inventory.models import Drug
from prescriptions.models import Prescription, PrescriptionItem, InteractionLog

logger = logging.getLogger(__name__)

class DrugInteractionEngine:
    """
    AI-powered drug interaction checking engine
    Combines rule-based checks, database lookups, and API calls
    """
    
    # Severe interaction pairs (rule-based)
    SEVERE_INTERACTIONS = [
        ('warfarin', 'aspirin'),
        ('warfarin', 'ibuprofen'),
        ('methotrexate', 'aspirin'),
        ('lithium', 'thiazide'),
        ('digoxin', 'verapamil'),
        ('theophylline', 'ciprofloxacin'),
        ('phenytoin', 'warfarin'),
        ('clopidogrel', 'omeprazole'),
        ('simvastatin', 'clarithromycin'),
        ('sildenafil', 'nitrates'),
    ]
    
    # Moderate interaction pairs
    MODERATE_INTERACTIONS = [
        ('metformin', 'contrast_dye'),
        ('lisinopril', 'potassium'),
        ('levothyroxine', 'calcium'),
        ('albuterol', 'beta_blockers'),
        ('fluoxetine', 'tramadol'),
    ]
    
    def __init__(self):
        pass
    
    def check_prescription(self, prescription, user=None) -> List[Dict]:
        """
        Main entry point for checking all interactions in a prescription
        Returns list of interaction alerts
        """
        alerts = []
        
        # Get patient and items
        patient = prescription.patient
        items = prescription.items if hasattr(prescription, 'items') else []
        
        if len(items) < 1:
            return alerts
        
        # Check each drug against patient profile
        for item in items:
            # Drug-allergy checks
            allergy_alerts = self.check_allergies(patient, item.drug)
            alerts.extend(allergy_alerts)
            
            # Dosage warnings
            dosage_alerts = self.check_dosage(patient, item)
            alerts.extend(dosage_alerts)
            
            # Age-based contraindications
            age_alerts = self.check_age_contraindications(patient, item.drug)
            alerts.extend(age_alerts)
        
        # Check drug-drug interactions (pairs)
        items_list = list(items)
        for i in range(len(items_list)):
            for j in range(i+1, len(items_list)):
                drug1 = items_list[i].drug
                drug2 = items_list[j].drug
                
                interaction_alerts = self.check_drug_interaction(drug1, drug2)
                alerts.extend(interaction_alerts)
        
        # Add risk scores
        for alert in alerts:
            alert['risk_score'] = self.calculate_risk_score(alert)
        
        return alerts
    
    def check_allergies(self, patient: Patient, drug: Drug) -> List[Dict]:
        """Check if drug conflicts with patient allergies"""
        alerts = []
        
        if not patient.allergies:
            return alerts
        
        # Parse patient allergies
        allergies = [a.strip().lower() for a in patient.allergies.split(',')]
        
        # Check drug name against allergies
        drug_name_lower = drug.name.lower()
        generic_name_lower = drug.generic_name.lower()
        
        for allergy in allergies:
            # Direct match
            if allergy and (allergy in drug_name_lower or allergy in generic_name_lower):
                alerts.append({
                    'type': 'drug-allergy',
                    'severity': 'high',
                    'drug': drug.name,
                    'allergen': allergy,
                    'description': f"Patient is allergic to {allergy}, which is present in {drug.name}",
                    'recommendation': "Do not dispense. Consider alternative medication."
                })
        
        return alerts
    
    def check_dosage(self, patient: Patient, item) -> List[Dict]:
        """Check for dosage warnings"""
        alerts = []
        
        # Parse dosage quantity
        try:
            # Extract numeric part from dosage (e.g., "1 tablet" -> 1)
            dosage_parts = item.dosage.split()
            if dosage_parts and dosage_parts[0].isdigit():
                quantity = int(dosage_parts[0])
            else:
                return alerts
        except:
            return alerts
        
        # Simple overdose check (quantity > 2 tablets per dose)
        if quantity > 2:
            alerts.append({
                'type': 'dosage-warning',
                'severity': 'moderate',
                'drug': item.drug.name,
                'description': f"High dosage: {item.dosage} {item.frequency}",
                'recommendation': "Verify dosage with prescribing physician."
            })
        
        # Check against age-based limits
        if patient.age < 12:  # Pediatric
            if quantity > 1:
                alerts.append({
                    'type': 'dosage-warning',
                    'severity': 'high',
                    'drug': item.drug.name,
                    'description': f"Pediatric dosage may be too high: {item.dosage}",
                    'recommendation': "Consult pediatric dosage guidelines."
                })
        
        return alerts
    
    def check_age_contraindications(self, patient: Patient, drug: Drug) -> List[Dict]:
        """Check if drug is contraindicated for patient's age"""
        alerts = []
        
        # Simple age-based contraindications
        if patient.age < 18 and any(word in drug.name.lower() for word in ['aspirin', 'ibuprofen']):
            alerts.append({
                'type': 'contraindication',
                'severity': 'moderate',
                'drug': drug.name,
                'description': f"Use with caution in pediatric patients: {drug.name}",
                'recommendation': "Consider reduced dosage or alternative."
            })
        
        return alerts
    
    def check_drug_interaction(self, drug1: Drug, drug2: Drug) -> List[Dict]:
        """Check for interactions between two drugs"""
        alerts = []
        
        # Rule-based check for severe interactions
        drug1_name_lower = drug1.name.lower()
        drug2_name_lower = drug2.name.lower()
        
        for severe_pair in self.SEVERE_INTERACTIONS:
            if (severe_pair[0] in drug1_name_lower and severe_pair[1] in drug2_name_lower) or \
               (severe_pair[0] in drug2_name_lower and severe_pair[1] in drug1_name_lower):
                alerts.append({
                    'type': 'drug-drug',
                    'severity': 'high',
                    'drug1': drug1.name,
                    'drug2': drug2.name,
                    'description': f"Severe interaction between {drug1.name} and {drug2.name}",
                    'recommendation': "Avoid concurrent use. Consider alternative therapy."
                })
                return alerts
        
        # Check moderate interactions
        for moderate_pair in self.MODERATE_INTERACTIONS:
            if (moderate_pair[0] in drug1_name_lower and moderate_pair[1] in drug2_name_lower) or \
               (moderate_pair[0] in drug2_name_lower and moderate_pair[1] in drug1_name_lower):
                alerts.append({
                    'type': 'drug-drug',
                    'severity': 'moderate',
                    'drug1': drug1.name,
                    'drug2': drug2.name,
                    'description': f"Moderate interaction between {drug1.name} and {drug2.name}",
                    'recommendation': "Monitor patient closely or adjust dosage."
                })
                return alerts
        
        return alerts
    
    def calculate_risk_score(self, alert: Dict) -> int:
        """Calculate numeric risk score (1-100)"""
        severity_scores = {
            'high': 80,
            'moderate': 50,
            'low': 20
        }
        
        base_score = severity_scores.get(alert.get('severity', 'low'), 20)
        
        # Adjust based on interaction type
        type_multipliers = {
            'drug-drug': 1.2,
            'drug-allergy': 1.5,
            'contraindication': 1.3,
            'dosage-warning': 0.8
        }
        
        multiplier = type_multipliers.get(alert.get('type', ''), 1.0)
        
        return min(100, int(base_score * multiplier))