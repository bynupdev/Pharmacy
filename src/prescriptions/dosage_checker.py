# D:\Pharmacy App\venv\src\prescriptions\dosage_checker.py

import re
from typing import Dict, List, Optional

class DosageChecker:
    """Check prescriptions for dosage issues - UPDATED WITH MORE DRUGS"""
    
    # CRITICAL MAXIMUM DAILY DOSES (mg/day)
    CRITICAL_LIMITS = {
        # Your problematic drugs
        'ATENOLOL': 100,        # Max 100mg/day - severe bradycardia, heart block, death
        'ALLOPURINOL': 800,     # Max 800mg/day - severe skin reactions, liver failure
        
        # Existing drugs
        'AMANTADINE': 400,
        'PARACETAMOL': 4000,
        'ACETAMINOPHEN': 4000,
        'IBUPROFEN': 3200,
        'ASPIRIN': 4000,
        'NAPROXEN': 1000,
        'METFORMIN': 2550,
        'ATORVASTATIN': 80,
        'SIMVASTATIN': 40,
        'LISINOPRIL': 40,
        'AMLODIPINE': 10,
        'WARFARIN': 10,
        'DIGOXIN': 0.5,
        'GABAPENTIN': 3600,
        'THEOPHYLLINE': 600,
        'PHENYTOIN': 400,
        'CARBAMAZEPINE': 1200,
        'VALPROATE': 3000,
        'LITHIUM': 1800,
        'QUETIAPINE': 800,
        'OLANZAPINE': 20,
        'RISPERIDONE': 16,
        'CLOZAPINE': 900,
        'HALOPERIDOL': 100,
        'DIAZEPAM': 40,
        'ALPRAZOLAM': 10,
        'LORAZEPAM': 10,
        'CLONAZEPAM': 20,
        'ZOLPIDEM': 10,
        'TRAMADOL': 400,
        'CODEINE': 360,
        'MORPHINE': 200,
        'OXYCODONE': 80,
        'HYDROCODONE': 60,
        'FENTANYL': 0.2,
        'PROPRANOLOL': 320,
        'METOPROLOL': 400,
        'CARVEDILOL': 100,
        'BISOPROLOL': 20,
        'NADOXOLOL': 320,
        'PINDOLOL': 60,
        
        # Additional safety limits
        'COLCHICINE': 2,        # Max 2mg/day - toxic at higher doses
        'DIGOXIN': 0.5,         # Max 0.5mg/day
        'LITHIUM': 1800,        # Max 1800mg/day
        'THEOPHYLLINE': 600,    # Max 600mg/day
        'WARFARIN': 10,         # Max 10mg/day
        'PHENYTOIN': 400,       # Max 400mg/day
        'CARBAMAZEPINE': 1200,  # Max 1200mg/day
        'VALPROIC': 3000,       # Max 3000mg/day
        'LAMOTRIGINE': 400,     # Max 400mg/day
        'TOPIRAMATE': 400,      # Max 400mg/day
        'LEVETIRACETAM': 3000,  # Max 3000mg/day
    }
    
    # Maximum SINGLE dose (mg)
    MAX_SINGLE_DOSE = {
        'ATENOLOL': 100,        # Max 100mg per dose
        'ALLOPURINOL': 300,     # Max 300mg per dose
        'AMANTADINE': 200,
        'PARACETAMOL': 1000,
        'IBUPROFEN': 800,
        'ASPIRIN': 1000,
        'TRAMADOL': 100,
        'CODEINE': 60,
        'MORPHINE': 30,
        'OXYCODONE': 20,
        'COLCHICINE': 1,
        'DIGOXIN': 0.25,
        'WARFARIN': 5,
    }
    
    def parse_frequency(self, frequency_text: str) -> int:
        """Convert frequency text to number of times per day"""
        freq_lower = frequency_text.lower().strip()
        
        # Common patterns
        if 'once' in freq_lower or 'daily' in freq_lower:
            return 1
        elif 'twice' in freq_lower or 'bid' in freq_lower:
            return 2
        elif 'three' in freq_lower or 'thrice' in freq_lower or 'tid' in freq_lower:
            return 3
        elif 'four' in freq_lower or 'qid' in freq_lower:
            return 4
        elif 'every 4 hours' in freq_lower:
            return 6
        elif 'every 6 hours' in freq_lower:
            return 4
        elif 'every 8 hours' in freq_lower:
            return 3
        elif 'every 12 hours' in freq_lower:
            return 2
        elif 'every hour' in freq_lower:
            return 24
        elif 'every 2 hours' in freq_lower:
            return 12
        elif 'every 3 hours' in freq_lower:
            return 8
        
        # Try to extract from pattern "every X hours"
        hour_match = re.search(r'every\s+(\d+)\s+hour', freq_lower)
        if hour_match:
            hours = int(hour_match.group(1))
            if hours > 0:
                return 24 // hours
        
        return 1
    
    def extract_dose_mg(self, dosage_text: str) -> Optional[float]:
        """Extract dose in mg from dosage text"""
        dosage_lower = dosage_text.lower().strip()
        
        # Extract number
        num_match = re.search(r'(\d+(?:\.\d+)?)', dosage_lower)
        if not num_match:
            return None
        
        dose_value = float(num_match.group(1))
        
        # Check for mg, mcg, g units
        if 'mg' in dosage_lower:
            return dose_value
        elif 'mcg' in dosage_lower or 'microgram' in dosage_lower:
            return dose_value / 1000
        elif 'g' in dosage_lower or 'gram' in dosage_lower:
            return dose_value * 1000
        
        # If no unit specified, assume mg
        return dose_value
    
    def find_matching_drug(self, drug_name: str) -> Optional[str]:
        """Find matching drug in critical limits database"""
        drug_upper = drug_name.upper().strip()
        
        # Direct match
        if drug_upper in self.CRITICAL_LIMITS:
            return drug_upper
        
        # Partial match - look for drug name in our database
        for critical_drug in self.CRITICAL_LIMITS.keys():
            if critical_drug in drug_upper or drug_upper in critical_drug:
                return critical_drug
        
        # Check common variations
        variations = {
            'ATENOLOL': ['ATEN', 'TENORMIN'],
            'ALLOPURINOL': ['ALLOP', 'ZYLOPRIM'],
            'AMANTADINE': ['AMAN', 'SYMMETREL'],
        }
        
        for main_drug, variants in variations.items():
            for variant in variants:
                if variant in drug_upper:
                    return main_drug
        
        return None
    
    def check_prescription_item(self, drug_name: str, dosage_text: str, frequency_text: str, duration_days: int, quantity: int) -> List[Dict]:
        """Check a single prescription item for safety issues"""
        alerts = []
        
        # Find matching drug
        matched_drug = self.find_matching_drug(drug_name)
        
        # Extract dose in mg
        dose_mg = self.extract_dose_mg(dosage_text)
        
        if dose_mg is None:
            alerts.append({
                'type': 'parsing_error',
                'severity': 'warning',
                'description': f"Could not parse dosage for {drug_name}: '{dosage_text}'",
                'recommendation': "Please verify dosage manually."
            })
            return alerts
        
        # Calculate frequency
        times_per_day = self.parse_frequency(frequency_text)
        daily_dose = dose_mg * times_per_day
        
        # CRITICAL: Single dose check
        if matched_drug and matched_drug in self.MAX_SINGLE_DOSE:
            max_single = self.MAX_SINGLE_DOSE[matched_drug]
            if dose_mg > max_single:
                ratio = dose_mg / max_single
                alerts.append({
                    'type': 'single_dose_overdose',
                    'severity': 'critical',
                    'drug': drug_name,
                    'single_dose': dose_mg,
                    'max_single': max_single,
                    'description': f"💀💀💀 SINGLE DOSE OVERDOSE: {dose_mg}mg per dose exceeds maximum safe single dose of {max_single}mg ({ratio:.0f}X higher!)",
                    'recommendation': "DO NOT DISPENSE. This single dose could be fatal. Contact prescriber immediately."
                })
        
        # CRITICAL: Daily dose check
        if matched_drug:
            max_daily = self.CRITICAL_LIMITS[matched_drug]
            
            if daily_dose > max_daily:
                ratio = daily_dose / max_daily
                
                if ratio >= 50:
                    severity = 'critical'
                    description = f"💀💀💀 EXTREME LETHAL OVERDOSE: {daily_dose}mg/day is {ratio:.0f}X the maximum safe dose of {max_daily}mg/day! THIS COULD BE FATAL!"
                    recommendation = "EMERGENCY: Do NOT dispense. This dose could cause cardiac arrest, respiratory failure, or death. Contact prescriber immediately."
                elif ratio >= 10:
                    severity = 'critical'
                    description = f"💀💀💀 SEVERE LETHAL OVERDOSE: {daily_dose}mg/day is {ratio:.0f}X the maximum safe dose of {max_daily}mg/day! LIFE-THREATENING!"
                    recommendation = "DO NOT DISPENSE. This is a life-threatening overdose. Contact prescriber immediately."
                elif ratio >= 5:
                    severity = 'critical'
                    description = f"💀💀 CRITICAL OVERDOSE: {daily_dose}mg/day is {ratio:.1f}X the maximum safe dose of {max_daily}mg/day!"
                    recommendation = "DO NOT DISPENSE. Severe overdose risk. Contact prescriber immediately."
                elif ratio >= 2:
                    severity = 'high'
                    description = f"⚠️ SIGNIFICANT OVERDOSE: {daily_dose}mg/day exceeds maximum safe dose of {max_daily}mg/day by {int((ratio-1)*100)}%"
                    recommendation = "Do not dispense. Contact prescriber to verify dosage."
                else:
                    severity = 'high'
                    description = f"⚠️ OVERDOSE: Daily dose of {daily_dose}mg exceeds maximum of {max_daily}mg/day"
                    recommendation = "Verify dosage with prescriber before dispensing."
                
                alerts.append({
                    'type': 'daily_dose_overdose',
                    'severity': severity,
                    'drug': drug_name,
                    'daily_dose': daily_dose,
                    'max_daily': max_daily,
                    'description': description,
                    'recommendation': recommendation
                })
            elif daily_dose > max_daily * 0.8:
                alerts.append({
                    'type': 'high_dose_warning',
                    'severity': 'warning',
                    'drug': drug_name,
                    'daily_dose': daily_dose,
                    'max_daily': max_daily,
                    'description': f"Daily dose of {daily_dose}mg is approaching the maximum of {max_daily}mg/day ({int((daily_dose/max_daily)*100)}% of limit)",
                    'recommendation': "Consider if dose is appropriate for patient condition."
                })
        else:
            # Drug not in our database - flag for manual review if dose seems high
            if daily_dose > 2000:
                alerts.append({
                    'type': 'unverified_drug',
                    'severity': 'warning',
                    'drug': drug_name,
                    'daily_dose': daily_dose,
                    'description': f"⚠️ UNVERIFIED DRUG: '{drug_name}' at {daily_dose}mg/day. Safety limit not in database.",
                    'recommendation': "Manual verification required. Please check dosing guidelines for this medication."
                })
        
        # Check quantity vs expected
        expected_quantity = times_per_day * duration_days
        if abs(quantity - expected_quantity) > expected_quantity * 0.1:
            alerts.append({
                'type': 'quantity_mismatch',
                'severity': 'warning',
                'drug': drug_name,
                'prescribed_quantity': quantity,
                'expected_quantity': expected_quantity,
                'description': f"Quantity ({quantity}) does not match expected quantity ({expected_quantity}) for the prescribed duration",
                'recommendation': "Verify quantity with prescriber."
            })
        
        return alerts
    
    def check_prescription(self, prescription) -> List[Dict]:
        """Check entire prescription for safety issues"""
        all_alerts = []
        
        for item in prescription.items.all():
            drug_name = item.drug.name
            dosage_text = item.dosage
            frequency_text = item.frequency
            duration_text = item.duration
            
            # Extract duration in days
            duration_match = re.search(r'(\d+)', duration_text)
            duration_days = int(duration_match.group(1)) if duration_match else 7
            
            alerts = self.check_prescription_item(
                drug_name, dosage_text, frequency_text, duration_days, item.quantity
            )
            
            all_alerts.extend(alerts)
        
        return all_alerts


# Create singleton instance
dosage_checker = DosageChecker()