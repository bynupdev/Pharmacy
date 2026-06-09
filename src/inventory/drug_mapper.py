"""
Service to map drug names to training data IDs
Loads once at startup and stays in memory
"""

import joblib
import os
from difflib import get_close_matches
from django.conf import settings

class DrugMappingService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.name_to_id = {}
        self.id_to_name = {}
        self.all_training_names = []
        self._initialized = True
        self._load_mapping()
    
    def _load_mapping(self):
        """Load the training data name-to-ID mapping"""
        import pandas as pd
        
        try:
            # Load training data directly from CSV
            df = pd.read_csv('ddi_pairs_50k.csv')
            
            # Build mapping
            for _, row in df.iterrows():
                name = row['a_name']
                drug_id = row['drug_a_ik14']
                if pd.notna(name) and pd.notna(drug_id):
                    self.name_to_id[name] = drug_id
                    self.id_to_name[drug_id] = name
                    self.all_training_names.append(name)
                
                name = row['b_name']
                drug_id = row['drug_b_ik14']
                if pd.notna(name) and pd.notna(drug_id):
                    self.name_to_id[name] = drug_id
                    self.id_to_name[drug_id] = name
                    self.all_training_names.append(name)
            
            # Remove duplicates
            self.all_training_names = list(set(self.all_training_names))
            print(f"✅ Loaded {len(self.name_to_id)} drug mappings from training data")
            
        except Exception as e:
            print(f"⚠️ Could not load training data: {e}")
    
    def get_training_id(self, drug_name):
        """Get training ID for a drug name"""
        # Exact match
        if drug_name in self.name_to_id:
            return self.name_to_id[drug_name]
        
        # Case-insensitive match
        drug_lower = drug_name.lower()
        for name, drug_id in self.name_to_id.items():
            if name.lower() == drug_lower:
                return drug_id
        
        # Partial match (e.g., "Lipitor" vs "Atorvastatin" won't work)
        # For brand names, you'd need a separate brand-to-generic mapping
        
        return None
    
    def find_closest_match(self, drug_name, cutoff=0.6):
        """Find closest matching drug name in training data"""
        matches = get_close_matches(drug_name, self.all_training_names, n=1, cutoff=cutoff)
        return matches[0] if matches else None

# Singleton instance
drug_mapper = DrugMappingService()