# """
# Fixed Drug Interaction Predictor for Django
# Uses the retrained model without data leakage
# """

# import joblib
# import os
# import numpy as np
# from django.conf import settings

# class FixedDrugPredictor:
#     def __init__(self):
#         self.model = None
#         self.encoder_a = None
#         self.encoder_b = None
#         self.scaler = None
#         self.feature_columns = None
#         self.loaded = False
#         self.load_models()
    
#     def load_models(self):
#         """Load the fixed model files"""
#         base_path = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
#         files = {
#             'model': 'drug_interaction_model_fixed.pkl',
#             'encoder_a': 'drug_encoder_a.pkl',
#             'encoder_b': 'drug_encoder_b.pkl',
#             'scaler': 'feature_scaler_fixed.pkl',
#             'features': 'feature_columns_fixed.pkl'
#         }
        
#         try:
#             self.model = joblib.load(os.path.join(base_path, files['model']))
#             self.encoder_a = joblib.load(os.path.join(base_path, files['encoder_a']))
#             self.encoder_b = joblib.load(os.path.join(base_path, files['encoder_b']))
#             self.scaler = joblib.load(os.path.join(base_path, files['scaler']))
#             self.feature_columns = joblib.load(os.path.join(base_path, files['features']))
#             self.loaded = True
#             print("✅ Fixed AI Drug Interaction Model loaded")
#             return True
#         except Exception as e:
#             print(f"⚠️ Error loading fixed model: {e}")
#             return False
    
#     def predict(self, drug1_name, drug2_name):
#         """
#         Predict interaction risk between two drugs
        
#         Returns:
#         {
#             'has_interaction': bool,
#             'risk_level': 'low'/'moderate'/'high',
#             'confidence': float (0-100),
#             'recommendation': str,
#             'color': 'success'/'warning'/'danger'
#         }
#         """
#         if not self.loaded:
#             return self.fallback(drug1_name, drug2_name)
        
#         try:
#             # Check if drugs are in the encoder
#             drug1_known = drug1_name in self.encoder_a.classes_
#             drug2_known = drug2_name in self.encoder_b.classes_
            
#             if not drug1_known or not drug2_known:
#                 return {
#                     'has_interaction': False,
#                     'risk_level': 'unknown',
#                     'confidence': 0,
#                     'recommendation': f"⚠️ {'Drug 1' if not drug1_known else 'Drug 2'} not in AI database. Please verify manually.",
#                     'color': 'warning',
#                     'source': 'unknown_drug'
#                 }
            
#             # Encode drugs
#             d1_enc = self.encoder_a.transform([drug1_name])[0]
#             d2_enc = self.encoder_b.transform([drug2_name])[0]
            
#             # Create features (must match training exactly)
#             features = np.array([[
#                 d1_enc, d2_enc,
#                 len(drug1_name), len(drug2_name),
#                 ord(drug1_name[0]) % 32 if drug1_name else 0,
#                 ord(drug2_name[0]) % 32 if drug2_name else 0,
#                 len(drug1_name.split()), len(drug2_name.split()),
#                 1 if drug1_name == drug2_name else 0,
#                 d1_enc + d2_enc,
#                 d1_enc * d2_enc,
#                 abs(d1_enc - d2_enc)
#             ]], dtype=np.float64)
            
#             # Scale features
#             features = self.scaler.transform(features)
            
#             # Get probability of high risk
#             prob_high = self.model.predict_proba(features)[0][1]
            
#             # Determine risk level
#             if prob_high > 0.6:
#                 risk_level = 'high'
#                 severity = 'high'
#                 recommendation = '🔴 HIGH RISK: Significant drug interaction detected! Consult pharmacist immediately.'
#                 color = 'danger'
#                 has_interaction = True
#             elif prob_high > 0.3:
#                 risk_level = 'moderate'
#                 severity = 'moderate'
#                 recommendation = '🟡 MODERATE RISK: Possible interaction. Monitor patient closely.'
#                 color = 'warning'
#                 has_interaction = True
#             else:
#                 risk_level = 'low'
#                 severity = 'low'
#                 recommendation = '🟢 LOW RISK: No significant interaction expected.'
#                 color = 'success'
#                 has_interaction = False
            
#             return {
#                 'has_interaction': has_interaction,
#                 'risk_level': risk_level,
#                 'severity': severity,
#                 'confidence': round(prob_high * 100, 1),
#                 'recommendation': recommendation,
#                 'color': color,
#                 'source': 'ai_model_fixed',
#                 'drug1': drug1_name,
#                 'drug2': drug2_name
#             }
            
#         except Exception as e:
#             print(f"Prediction error: {e}")
#             return self.fallback(drug1_name, drug2_name)
    
#     def fallback(self, drug1, drug2):
#         return {
#             'has_interaction': False,
#             'risk_level': 'unknown',
#             'confidence': 0,
#             'recommendation': 'Unable to analyze. Please consult pharmacist.',
#             'color': 'secondary',
#             'source': 'fallback',
#             'drug1': drug1,
#             'drug2': drug2
#         }

# # Create singleton instance
# fixed_predictor = FixedDrugPredictor()



# D:\Pharmacy App\venv\src\ai_engine\predictor_fixed.py

"""
Fixed Drug Interaction Predictor for Django
Handles known drugs via AI model, unknown drugs via fallback
"""

import joblib
import os
import numpy as np
from difflib import get_close_matches
from django.conf import settings

class FixedDrugPredictor:
    def __init__(self):
        self.model = None
        self.encoder_a = None
        self.encoder_b = None
        self.scaler = None
        self.feature_columns = None
        self.drug_name_map = None
        self.loaded = False
        self.load_models()
    
    def load_models(self):
        """Load the fixed model files"""
        base_path = getattr(settings, 'BASE_DIR', os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        files = {
            'model': 'drug_interaction_model_fixed.pkl',
            'encoder_a': 'drug_encoder_a.pkl',
            'encoder_b': 'drug_encoder_b.pkl',
            'scaler': 'feature_scaler_fixed.pkl',
            'features': 'feature_columns_fixed.pkl',
            'drug_map': 'drug_name_to_id_mapping.pkl'
        }
        
        try:
            model_path = os.path.join(base_path, files['model'])
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                self.encoder_a = joblib.load(os.path.join(base_path, files['encoder_a']))
                self.encoder_b = joblib.load(os.path.join(base_path, files['encoder_b']))
                self.scaler = joblib.load(os.path.join(base_path, files['scaler']))
                self.feature_columns = joblib.load(os.path.join(base_path, files['features']))
                
                # Load drug name mapping if it exists
                map_path = os.path.join(base_path, files['drug_map'])
                if os.path.exists(map_path):
                    self.drug_name_map = joblib.load(map_path)
                
                self.loaded = True
                print("✅ Fixed AI Drug Interaction Model loaded")
                print(f"   Model knows {len(self.encoder_a.classes_)} unique drugs")
                return True
            else:
                print(f"⚠️ Model file not found: {model_path}")
                return False
        except Exception as e:
            print(f"⚠️ Error loading fixed model: {e}")
            return False
    
    def find_closest_match(self, drug_name, cutoff=0.6):
        """Find closest matching drug name in training data"""
        if not self.encoder_a:
            return None
        
        # Try exact match first (case-insensitive)
        for known_drug in self.encoder_a.classes_:
            if known_drug.lower() == drug_name.lower():
                return known_drug
        
        # Try fuzzy matching
        matches = get_close_matches(drug_name, self.encoder_a.classes_, n=1, cutoff=cutoff)
        if matches:
            return matches[0]
        
        # Try partial match
        for known_drug in self.encoder_a.classes_:
            if drug_name.lower() in known_drug.lower() or known_drug.lower() in drug_name.lower():
                return known_drug
        
        return None
    
    def get_drug_id_from_mapping(self, drug_name):
        """Get drug ID from mapping file"""
        if not self.drug_name_map:
            return None
        
        # Exact match
        if drug_name in self.drug_name_map:
            return self.drug_name_map[drug_name]
        
        # Case-insensitive match
        for key, value in self.drug_name_map.items():
            if key.lower() == drug_name.lower():
                return value
        
        return None
    
    def predict(self, drug1_name, drug2_name):
        """
        Predict interaction risk between two drugs
        Handles unknown drugs via fallback
        """
        # Check if model is loaded
        if not self.loaded:
            return self.fallback_prediction(drug1_name, drug2_name)
        
        # First, try to find matches for both drugs
        drug1_match = self.find_closest_match(drug1_name)
        drug2_match = self.find_closest_match(drug2_name)
        
        # If both drugs are known to the model
        if drug1_match and drug2_match:
            return self.model_predict(drug1_match, drug2_match)
        
        # If one drug is unknown
        if not drug1_match and not drug2_match:
            return {
                'has_interaction': False,
                'risk_level': 'unknown',
                'severity': 'low',
                'confidence': 0,
                'recommendation': f"⚠️ Both '{drug1_name}' and '{drug2_name}' are not in the AI database. Please verify interactions manually.",
                'color': 'warning',
                'source': 'unknown_drugs',
                'drug1': drug1_name,
                'drug2': drug2_name
            }
        
        if not drug1_match:
            return {
                'has_interaction': False,
                'risk_level': 'unknown',
                'severity': 'low',
                'confidence': 0,
                'recommendation': f"⚠️ '{drug1_name}' is not in the AI database. Please verify interactions manually.",
                'color': 'warning',
                'source': 'unknown_drug',
                'drug1': drug1_name,
                'drug2': drug2_name
            }
        
        if not drug2_match:
            return {
                'has_interaction': False,
                'risk_level': 'unknown',
                'severity': 'low',
                'confidence': 0,
                'recommendation': f"⚠️ '{drug2_name}' is not in the AI database. Please verify interactions manually.",
                'color': 'warning',
                'source': 'unknown_drug',
                'drug1': drug1_name,
                'drug2': drug2_name
            }
        
        return self.fallback_prediction(drug1_name, drug2_name)
    
    def model_predict(self, drug1_name, drug2_name):
        """Make prediction using the trained model"""
        try:
            # Encode drugs
            d1_enc = self.encoder_a.transform([drug1_name])[0]
            d2_enc = self.encoder_b.transform([drug2_name])[0]
            
            # Create features (must match training exactly)
            features = np.array([[
                d1_enc, d2_enc,
                len(drug1_name), len(drug2_name),
                ord(drug1_name[0]) % 32 if drug1_name else 0,
                ord(drug2_name[0]) % 32 if drug2_name else 0,
                len(drug1_name.split()), len(drug2_name.split()),
                1 if drug1_name == drug2_name else 0,
                d1_enc + d2_enc,
                d1_enc * d2_enc,
                abs(d1_enc - d2_enc)
            ]], dtype=np.float64)
            
            # Scale features
            features = self.scaler.transform(features)
            
            # Get probability of high risk
            prob_high = self.model.predict_proba(features)[0][1]
            
            # Determine risk level
            if prob_high > 0.6:
                risk_level = 'high'
                severity = 'high'
                has_interaction = True
                recommendation = '🔴 HIGH RISK: Significant drug interaction detected! Consult pharmacist immediately.'
                color = 'danger'
            elif prob_high > 0.3:
                risk_level = 'moderate'
                severity = 'moderate'
                has_interaction = True
                recommendation = '🟡 MODERATE RISK: Possible interaction. Monitor patient closely.'
                color = 'warning'
            else:
                risk_level = 'low'
                severity = 'low'
                has_interaction = False
                recommendation = '🟢 LOW RISK: No significant interaction expected.'
                color = 'success'
            
            return {
                'has_interaction': has_interaction,
                'risk_level': risk_level,
                'severity': severity,
                'confidence': round(prob_high * 100, 1),
                'recommendation': recommendation,
                'color': color,
                'source': 'ai_model',
                'drug1': drug1_name,
                'drug2': drug2_name
            }
            
        except Exception as e:
            print(f"Model prediction error: {e}")
            return self.fallback_prediction(drug1_name, drug2_name)
    
    def fallback_prediction(self, drug1, drug2):
        """Fallback when model fails - uses rule-based engine"""
        try:
            from prescriptions.interaction_engine import DrugInteractionEngine
            engine = DrugInteractionEngine()
            result = engine.check_drug_pair(drug1, drug2)
            
            if result:
                return {
                    'has_interaction': True,
                    'risk_level': result.get('severity', 'moderate'),
                    'severity': result.get('severity', 'moderate'),
                    'confidence': 50.0,
                    'recommendation': result.get('recommendation', 'Please verify interaction manually.'),
                    'color': 'warning',
                    'source': 'rule_engine',
                    'drug1': drug1,
                    'drug2': drug2
                }
            else:
                return {
                    'has_interaction': False,
                    'risk_level': 'low',
                    'severity': 'low',
                    'confidence': 0,
                    'recommendation': 'No known interaction found in rule database. Please verify manually.',
                    'color': 'success',
                    'source': 'rule_engine',
                    'drug1': drug1,
                    'drug2': drug2
                }
        except Exception as e:
            print(f"Fallback error: {e}")
            return {
                'has_interaction': False,
                'risk_level': 'unknown',
                'severity': 'low',
                'confidence': 0,
                'recommendation': 'Unable to analyze interaction. Please consult pharmacist.',
                'color': 'secondary',
                'source': 'error_fallback',
                'drug1': drug1,
                'drug2': drug2
            }
    
    def batch_predict(self, drug_pairs):
        """Predict multiple drug pairs at once"""
        results = []
        for drug1, drug2 in drug_pairs:
            results.append(self.predict(drug1, drug2))
        return results
    
    def is_drug_known(self, drug_name):
        """Check if a drug is known to the model"""
        if not self.loaded:
            return False
        return drug_name in self.encoder_a.classes_ or self.find_closest_match(drug_name) is not None

# Create singleton instance
fixed_predictor = FixedDrugPredictor()