"""
Fixed Drug Interaction Predictor for Django
Uses the retrained model without data leakage
"""

import joblib
import os
import numpy as np
from django.conf import settings

class FixedDrugPredictor:
    def __init__(self):
        self.model = None
        self.encoder_a = None
        self.encoder_b = None
        self.scaler = None
        self.feature_columns = None
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
            'features': 'feature_columns_fixed.pkl'
        }
        
        try:
            self.model = joblib.load(os.path.join(base_path, files['model']))
            self.encoder_a = joblib.load(os.path.join(base_path, files['encoder_a']))
            self.encoder_b = joblib.load(os.path.join(base_path, files['encoder_b']))
            self.scaler = joblib.load(os.path.join(base_path, files['scaler']))
            self.feature_columns = joblib.load(os.path.join(base_path, files['features']))
            self.loaded = True
            print("✅ Fixed AI Drug Interaction Model loaded")
            return True
        except Exception as e:
            print(f"⚠️ Error loading fixed model: {e}")
            return False
    
    def predict(self, drug1_name, drug2_name):
        """
        Predict interaction risk between two drugs
        
        Returns:
        {
            'has_interaction': bool,
            'risk_level': 'low'/'moderate'/'high',
            'confidence': float (0-100),
            'recommendation': str,
            'color': 'success'/'warning'/'danger'
        }
        """
        if not self.loaded:
            return self.fallback(drug1_name, drug2_name)
        
        try:
            # Check if drugs are in the encoder
            drug1_known = drug1_name in self.encoder_a.classes_
            drug2_known = drug2_name in self.encoder_b.classes_
            
            if not drug1_known or not drug2_known:
                return {
                    'has_interaction': False,
                    'risk_level': 'unknown',
                    'confidence': 0,
                    'recommendation': f"⚠️ {'Drug 1' if not drug1_known else 'Drug 2'} not in AI database. Please verify manually.",
                    'color': 'warning',
                    'source': 'unknown_drug'
                }
            
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
                recommendation = '🔴 HIGH RISK: Significant drug interaction detected! Consult pharmacist immediately.'
                color = 'danger'
                has_interaction = True
            elif prob_high > 0.3:
                risk_level = 'moderate'
                severity = 'moderate'
                recommendation = '🟡 MODERATE RISK: Possible interaction. Monitor patient closely.'
                color = 'warning'
                has_interaction = True
            else:
                risk_level = 'low'
                severity = 'low'
                recommendation = '🟢 LOW RISK: No significant interaction expected.'
                color = 'success'
                has_interaction = False
            
            return {
                'has_interaction': has_interaction,
                'risk_level': risk_level,
                'severity': severity,
                'confidence': round(prob_high * 100, 1),
                'recommendation': recommendation,
                'color': color,
                'source': 'ai_model_fixed',
                'drug1': drug1_name,
                'drug2': drug2_name
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return self.fallback(drug1_name, drug2_name)
    
    def fallback(self, drug1, drug2):
        return {
            'has_interaction': False,
            'risk_level': 'unknown',
            'confidence': 0,
            'recommendation': 'Unable to analyze. Please consult pharmacist.',
            'color': 'secondary',
            'source': 'fallback',
            'drug1': drug1,
            'drug2': drug2
        }

# Create singleton instance
fixed_predictor = FixedDrugPredictor()