# import numpy as np
# import pandas as pd
# import pickle
# import os
# import logging
# from sklearn.ensemble import RandomForestClassifier
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import classification_report
# import requests
# from datetime import datetime
# import json

# logger = logging.getLogger(__name__)

# class MLInteractionModel:
#     """
#     Machine Learning model for predicting drug interactions
#     Trains on historical interaction data and FDA adverse event reports
#     """
    
#     def __init__(self, model_path=None):
#         self.model = None
#         self.vectorizer = TfidfVectorizer(max_features=1000)
#         self.drug_embedding_cache = {}
        
#         if model_path and os.path.exists(model_path):
#             self.load_model(model_path)
#         else:
#             self.build_knowledge_base()
    
#     def build_knowledge_base(self):
#         """Build knowledge base from multiple data sources"""
#         self.knowledge_base = {
#             'interactions': self.load_fda_interactions(),
#             'contraindications': self.load_fda_contraindications(),
#             'adverse_events': self.load_fda_adverse_events(),
#             'chemical_structures': self.load_pubchem_data(),
#             'clinical_studies': self.load_clinical_trials_data()
#         }
#         logger.info(f"Knowledge base built with {len(self.knowledge_base['interactions'])} interactions")
    
#     def load_fda_interactions(self):
#         """Load drug interaction data from OpenFDA"""
#         interactions = []
#         try:
#             # Query OpenFDA for drug interaction labels
#             base_url = "https://api.fda.gov/drug/label.json"
#             params = {
#                 'search': '_exists_:drug_interactions',
#                 'limit': 100
#             }
            
#             response = requests.get(base_url, params=params, timeout=10)
#             if response.status_code == 200:
#                 data = response.json()
#                 for result in data.get('results', []):
#                     if 'drug_interactions' in result:
#                         interactions.append({
#                             'drug_name': result.get('openfda', {}).get('brand_name', [''])[0],
#                             'interactions': result['drug_interactions'],
#                             'severity': self.extract_severity(result['drug_interactions'])
#                         })
#             logger.info(f"Loaded {len(interactions)} FDA interactions")
#         except Exception as e:
#             logger.error(f"Error loading FDA data: {e}")
        
#         return interactions
    
#     def load_fda_adverse_events(self):
#         """Load adverse event reports from FDA"""
#         events = []
#         try:
#             base_url = "https://api.fda.gov/drug/event.json"
#             params = {
#                 'search': 'patient.drug.drugcharacterization:1',
#                 'limit': 100
#             }
            
#             response = requests.get(base_url, params=params, timeout=10)
#             if response.status_code == 200:
#                 data = response.json()
#                 for result in data.get('results', []):
#                     if 'patient' in result and 'drug' in result['patient']:
#                         for drug in result['patient']['drug'][:3]:
#                             events.append({
#                                 'drug': drug.get('medicinalproduct', ''),
#                                 'reactions': [r.get('reactionmeddrapt', '') for r in result['patient'].get('reaction', [])],
#                                 'serious': result.get('serious', 0)
#                             })
#             logger.info(f"Loaded {len(events)} adverse events")
#         except Exception as e:
#             logger.error(f"Error loading adverse events: {e}")
        
#         return events
    
#     def load_pubchem_data(self):
#         """Load chemical structure data from PubChem"""
#         structures = {}
#         # In production, you'd query PubChem API
#         # For now, using sample data
#         sample_structures = {
#             'warfarin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
#             'aspirin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
#             'ibuprofen': 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
#         }
#         return sample_structures
    
#     def load_clinical_trials_data(self):
#         """Load clinical trial data"""
#         trials = []
#         try:
#             base_url = "https://clinicaltrials.gov/api/query/study_fields"
#             # This is a simplified example
#             trials = [
#                 {'drug1': 'warfarin', 'drug2': 'aspirin', 'interaction': 'severe'},
#                 {'drug1': 'metformin', 'drug2': 'insulin', 'interaction': 'moderate'},
#             ]
#         except Exception as e:
#             logger.error(f"Error loading clinical trials: {e}")
        
#         return trials
    
#     def extract_severity(self, interaction_text):
#         """Extract severity level from interaction text using NLP"""
#         text = interaction_text.lower()
#         if any(word in text for word in ['contraindicated', 'do not use', 'avoid', 'severe']):
#             return 'high'
#         elif any(word in text for word in ['caution', 'monitor', 'adjust', 'moderate']):
#             return 'moderate'
#         else:
#             return 'low'
    
#     def train_model(self):
#         """Train ML model on interaction data"""
#         # Prepare training data
#         X = []
#         y = []
        
#         # Convert interactions to features
#         for interaction in self.knowledge_base['interactions']:
#             features = self.extract_features(
#                 interaction.get('drug_name', ''),
#                 interaction.get('interactions', '')
#             )
#             X.append(features)
#             y.append(self.severity_to_numeric(interaction.get('severity', 'low')))
        
#         if len(X) < 10:
#             logger.warning("Insufficient training data")
#             return
        
#         # Vectorize text features
#         X_vectorized = self.vectorizer.fit_transform(X)
        
#         # Train model
#         self.model = RandomForestClassifier(n_estimators=100, random_state=42)
#         self.model.fit(X_vectorized, y)
        
#         logger.info(f"Model trained on {len(X)} samples")
    
#     def extract_features(self, drug_name, interaction_text):
#         """Extract features for ML prediction"""
#         features = f"{drug_name} {interaction_text}"
#         return features
    
#     def severity_to_numeric(self, severity):
#         """Convert severity to numeric value"""
#         mapping = {'low': 0, 'moderate': 1, 'high': 2}
#         return mapping.get(severity, 0)
    
#     def predict_interaction(self, drug1_name, drug2_name, patient_data=None):
#         """
#         Predict interaction between two drugs using ML model
#         """
#         if not self.model:
#             return self.rule_based_prediction(drug1_name, drug2_name, patient_data)
        
#         # Create feature vector
#         features = self.extract_features(drug1_name, drug2_name)
#         features_vectorized = self.vectorizer.transform([features])
        
#         # Get prediction and probability
#         prediction = self.model.predict(features_vectorized)[0]
#         probabilities = self.model.predict_proba(features_vectorized)[0]
        
#         severity = ['low', 'moderate', 'high'][prediction]
#         confidence = max(probabilities) * 100
        
#         return {
#             'severity': severity,
#             'confidence': confidence,
#             'probability': dict(zip(['low', 'moderate', 'high'], probabilities)),
#             'method': 'ml_prediction'
#         }
    
#     def rule_based_prediction(self, drug1_name, drug2_name, patient_data=None):
#         """Fallback rule-based prediction"""
#         drug1_lower = drug1_name.lower()
#         drug2_lower = drug2_name.lower()
        
#         # Check knowledge base
#         for interaction in self.knowledge_base['interactions']:
#             if drug1_lower in interaction.get('drug_name', '').lower():
#                 return {
#                     'severity': interaction.get('severity', 'moderate'),
#                     'description': interaction.get('interactions', '')[:200],
#                     'confidence': 70,
#                     'method': 'knowledge_base'
#                 }
        
#         # Chemical structure similarity
#         if drug1_lower in self.knowledge_base['chemical_structures'] and \
#            drug2_lower in self.knowledge_base['chemical_structures']:
#             return {
#                 'severity': 'moderate',
#                 'description': 'Structural similarity detected, possible interaction',
#                 'confidence': 60,
#                 'method': 'chemical_similarity'
#             }
        
#         return {
#             'severity': 'unknown',
#             'description': 'No interaction data available',
#             'confidence': 0,
#             'method': 'no_data'
#         }
    
#     def save_model(self, path):
#         """Save trained model to disk"""
#         with open(path, 'wb') as f:
#             pickle.dump({
#                 'model': self.model,
#                 'vectorizer': self.vectorizer,
#                 'knowledge_base': self.knowledge_base
#             }, f)
#         logger.info(f"Model saved to {path}")
    
#     def load_model(self, path):
#         """Load trained model from disk"""
#         with open(path, 'rb') as f:
#             data = pickle.load(f)
#             self.model = data['model']
#             self.vectorizer = data['vectorizer']
#             self.knowledge_base = data['knowledge_base']
#         logger.info(f"Model loaded from {path}")


import numpy as np
import pandas as pd
import pickle
import os
import logging
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import requests
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class MLInteractionModel:
    """
    Machine Learning model for predicting drug interactions
    Trains on historical interaction data and FDA adverse event reports
    """
    
    def __init__(self, model_path=None):
        self.model = None
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.drug_embedding_cache = {}
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        else:
            self.build_knowledge_base()
    
    def build_knowledge_base(self):
        """Build knowledge base from multiple data sources"""
        self.knowledge_base = {
            'interactions': self.load_fda_interactions(),
            'contraindications': self.load_fda_contraindications(),  # Now this will work
            'adverse_events': self.load_fda_adverse_events(),
            'chemical_structures': self.load_pubchem_data(),
            'clinical_studies': self.load_clinical_trials_data()
        }
        logger.info(f"Knowledge base built with {len(self.knowledge_base['interactions'])} interactions")
    
    # ADD THIS MISSING METHOD
    def load_fda_contraindications(self):
        """
        Load FDA contraindications data
        Contraindications are specific situations where a drug should not be used
        """
        contraindications = []
        try:
            # Query OpenFDA for contraindications
            base_url = "https://api.fda.gov/drug/label.json"
            params = {
                'search': '_exists_:contraindications',
                'limit': 100
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for result in data.get('results', []):
                    if 'contraindications' in result:
                        # Handle both string and list responses
                        contraindication_text = result['contraindications']
                        if isinstance(contraindication_text, list):
                            contraindication_text = ' '.join(contraindication_text)
                        
                        contraindications.append({
                            'drug_name': result.get('openfda', {}).get('brand_name', [''])[0],
                            'contraindications': contraindication_text,
                            'severity': 'high'  # Contraindications are always high severity
                        })
            logger.info(f"Loaded {len(contraindications)} FDA contraindications")
        except Exception as e:
            logger.error(f"Error loading FDA contraindications: {e}")
        
        return contraindications
    
    def load_fda_interactions(self):
        """Load drug interaction data from OpenFDA"""
        interactions = []
        try:
            # Query OpenFDA for drug interaction labels
            base_url = "https://api.fda.gov/drug/label.json"
            params = {
                'search': '_exists_:drug_interactions',
                'limit': 100
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for result in data.get('results', []):
                    if 'drug_interactions' in result:
                        # Handle both string and list responses
                        interaction_text = result['drug_interactions']
                        if isinstance(interaction_text, list):
                            interaction_text = ' '.join(interaction_text)
                        
                        interactions.append({
                            'drug_name': result.get('openfda', {}).get('brand_name', [''])[0],
                            'interactions': interaction_text,
                            'severity': self.extract_severity(interaction_text)  # Now passing string
                        })
            logger.info(f"Loaded {len(interactions)} FDA interactions")
        except Exception as e:
            logger.error(f"Error loading FDA data: {e}")
        
        return interactions
    
    def load_fda_adverse_events(self):
        """Load adverse event reports from FDA"""
        events = []
        try:
            base_url = "https://api.fda.gov/drug/event.json"
            params = {
                'search': 'patient.drug.drugcharacterization:1',
                'limit': 100
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for result in data.get('results', []):
                    if 'patient' in result and 'drug' in result['patient']:
                        for drug in result['patient']['drug'][:3]:
                            # Handle reactions list properly
                            reactions = []
                            for r in result['patient'].get('reaction', []):
                                reaction = r.get('reactionmeddrapt', '')
                                if reaction:  # Only add if not empty
                                    reactions.append(reaction)
                            
                            events.append({
                                'drug': drug.get('medicinalproduct', ''),
                                'reactions': reactions,
                                'serious': result.get('serious', 0)
                            })
            logger.info(f"Loaded {len(events)} adverse events")
        except Exception as e:
            logger.error(f"Error loading adverse events: {e}")
        
        return events
    
    def load_pubchem_data(self):
        """Load chemical structure data from PubChem"""
        structures = {}
        # In production, you'd query PubChem API
        # For now, using sample data
        sample_structures = {
            'warfarin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
            'aspirin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
            'ibuprofen': 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
        }
        return sample_structures
    
    def load_clinical_trials_data(self):
        """Load clinical trial data"""
        trials = []
        try:
            # This is a simplified example
            trials = [
                {'drug1': 'warfarin', 'drug2': 'aspirin', 'interaction': 'severe'},
                {'drug1': 'metformin', 'drug2': 'insulin', 'interaction': 'moderate'},
            ]
        except Exception as e:
            logger.error(f"Error loading clinical trials: {e}")
        
        return trials
    
    def extract_severity(self, interaction_text):
        """Extract severity level from interaction text using NLP"""
        # Add type checking to prevent the 'list' object error
        if interaction_text is None:
            return 'low'
        
        # Convert to string if it's not already
        if not isinstance(interaction_text, str):
            if isinstance(interaction_text, list):
                # Join list items into a single string
                interaction_text = ' '.join([str(item) for item in interaction_text if item])
            else:
                # Convert other types to string
                interaction_text = str(interaction_text)
        
        text = interaction_text.lower()
        if any(word in text for word in ['contraindicated', 'do not use', 'avoid', 'severe']):
            return 'high'
        elif any(word in text for word in ['caution', 'monitor', 'adjust', 'moderate']):
            return 'moderate'
        else:
            return 'low'
    
    def train_model(self):
        """Train ML model on interaction data"""
        # Prepare training data
        X = []
        y = []
        
        # Convert interactions to features
        for interaction in self.knowledge_base['interactions']:
            features = self.extract_features(
                interaction.get('drug_name', ''),
                interaction.get('interactions', '')
            )
            X.append(features)
            y.append(self.severity_to_numeric(interaction.get('severity', 'low')))
        
        if len(X) < 10:
            logger.warning("Insufficient training data")
            return
        
        # Vectorize text features
        X_vectorized = self.vectorizer.fit_transform(X)
        
        # Train model
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_vectorized, y)
        
        logger.info(f"Model trained on {len(X)} samples")
    
    def extract_features(self, drug_name, interaction_text):
        """Extract features for ML prediction"""
        # Ensure both inputs are strings
        drug_name = str(drug_name) if drug_name else ''
        interaction_text = str(interaction_text) if interaction_text else ''
        features = f"{drug_name} {interaction_text}"
        return features
    
    def severity_to_numeric(self, severity):
        """Convert severity to numeric value"""
        mapping = {'low': 0, 'moderate': 1, 'high': 2}
        return mapping.get(severity, 0)
    
    def predict_interaction(self, drug1_name, drug2_name, patient_data=None):
        """
        Predict interaction between two drugs using ML model
        """
        if not self.model:
            return self.rule_based_prediction(drug1_name, drug2_name, patient_data)
        
        # Create feature vector
        features = self.extract_features(drug1_name, drug2_name)
        features_vectorized = self.vectorizer.transform([features])
        
        # Get prediction and probability
        prediction = self.model.predict(features_vectorized)[0]
        probabilities = self.model.predict_proba(features_vectorized)[0]
        
        severity = ['low', 'moderate', 'high'][prediction]
        confidence = max(probabilities) * 100
        
        return {
            'severity': severity,
            'confidence': confidence,
            'probability': dict(zip(['low', 'moderate', 'high'], probabilities)),
            'method': 'ml_prediction'
        }
    
    def rule_based_prediction(self, drug1_name, drug2_name, patient_data=None):
        """Fallback rule-based prediction"""
        # Add null checks
        drug1_lower = drug1_name.lower() if drug1_name else ''
        drug2_lower = drug2_name.lower() if drug2_name else ''
        
        # Check knowledge base
        for interaction in self.knowledge_base['interactions']:
            drug_name = interaction.get('drug_name', '')
            if drug_name and drug1_lower in drug_name.lower():
                return {
                    'severity': interaction.get('severity', 'moderate'),
                    'description': interaction.get('interactions', '')[:200],
                    'confidence': 70,
                    'method': 'knowledge_base'
                }
        
        # Chemical structure similarity
        if drug1_lower in self.knowledge_base['chemical_structures'] and \
           drug2_lower in self.knowledge_base['chemical_structures']:
            return {
                'severity': 'moderate',
                'description': 'Structural similarity detected, possible interaction',
                'confidence': 60,
                'method': 'chemical_similarity'
            }
        
        return {
            'severity': 'unknown',
            'description': 'No interaction data available',
            'confidence': 0,
            'method': 'no_data'
        }
    
    def save_model(self, path):
        """Save trained model to disk"""
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'vectorizer': self.vectorizer,
                'knowledge_base': self.knowledge_base
            }, f)
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path):
        """Load trained model from disk"""
        with open(path, 'rb') as f:
            data = pickle.load(f)
            self.model = data['model']
            self.vectorizer = data['vectorizer']
            self.knowledge_base = data['knowledge_base']
        logger.info(f"Model loaded from {path}")