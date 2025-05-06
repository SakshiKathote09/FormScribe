import unittest
import os
import json
import sys
from pathlib import Path

# Add parent directory to path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))
from adaptive_form_filler.src.main import FormDefinition, FormFiller, MissingFieldError, InvalidFieldTypeError

class TestFormFiller(unittest.TestCase):
    """Test cases for FormFiller class"""

    TEST_DATA_DIR = Path(__file__).parent / "data"
    
    def setUp(self):
        """Set up test data paths"""
        self.pt_form_path = self.TEST_DATA_DIR / "form_pt_visit.json"
        self.sn_form_path = self.TEST_DATA_DIR / "form_sn_visit.json"
        self.pt_eval_form_path = self.TEST_DATA_DIR / "form_pt_evaluation.json"
        self.sample_input_path = self.TEST_DATA_DIR / "sample_input_data.json"
        self.minimal_input_path = self.TEST_DATA_DIR / "minimal_input_data.json"
        
        # Create test data directory if it doesn't exist
        os.makedirs(self.TEST_DATA_DIR, exist_ok=True)
        
        # Create minimal PT evaluation form for testing
        if not os.path.exists(self.pt_eval_form_path):
            with open(self.pt_eval_form_path, 'w') as f:
                json.dump({
                    "form_id": "PT_EVALUATION",
                    "form_name": "Physical Therapy Evaluation",
                    "fields": [
                        {
                            "id": "patient_name",
                            "name": "Patient Name",
                            "type": "string",
                            "required": True
                        },
                        {
                            "id": "visit_date",
                            "name": "Visit Date",
                            "type": "string",
                            "required": True
                        },
                        {
                            "id": "relevant_medical_history",
                            "name": "Relevant Medical History",
                            "type": "string",
                            "required": True
                        },
                        {
                            "id": "prior_level_of_function",
                            "name": "Prior Level of Function",
                            "type": "string",
                            "required": True
                        }
                    ]
                }, f, indent=2)
        
        # Create minimal input data for testing
        if not os.path.exists(self.minimal_input_path):
            with open(self.minimal_input_path, 'w') as f:
                json.dump({
                    "patient_identifier": "Smith, Jane - MRN67890",
                    "date_of_visit": "2025-05-01",
                    "medical_history_notes": "Diabetes, Hypertension",
                    "functioning_level_prior": "Independent with all ADLs",
                    "vital_temp_f": 98.6,
                    "vital_hr": 68,
                    "cardio_symptoms_dizziness": False
                }, f, indent=2)

    def test_load_form_definition(self):
        """Test loading form definition from file"""
        # Test PT form loading
        pt_form = FormDefinition.load(str(self.pt_form_path))
        self.assertEqual(pt_form.form_id, "PT_VISIT")
        self.assertEqual(pt_form.form_name, "Physical Therapy Visit")
        
        # Test SN form loading
        sn_form = FormDefinition.load(str(self.sn_form_path))
        self.assertEqual(sn_form.form_id, "SN_VISIT")
        self.assertEqual(sn_form.form_name, "Skilled Nursing Visit")

    def test_pt_visit_form_filling(self):
        """Test PT Visit form filling with complete data"""
        with open(self.sample_input_path, 'r') as f:
            input_data = json.load(f)
        
        pt_form = FormDefinition.load(str(self.pt_form_path))
        filler = FormFiller(pt_form, input_data)
        result = filler.fill()
        
        # Check that required fields are present
        self.assertEqual(result["patient_name"], "Doe, John - MRN12345")
        self.assertEqual(result["visit_date"], "2025-05-05")
        
        # Check that exercises array is mapped correctly
        self.assertEqual(len(result["exercises_performed"]), 3)
        self.assertEqual(result["exercises_performed"][0]["exercise_name"], "Quad sets")
        self.assertEqual(result["exercises_performed"][0]["sets"], 3)
        self.assertEqual(result["exercises_performed"][0]["reps"], 10)
        
        # Check vitals_pt object
        self.assertEqual(result["vitals_pt"]["hr_prior"], 72)
        self.assertEqual(result["vitals_pt"]["hr_during"], 88)
        self.assertEqual(result["vitals_pt"]["bp_prior"], "130/80")
        self.assertEqual(result["vitals_pt"]["o2_sat_prior"], 97)
        self.assertEqual(result["vitals_pt"]["o2_sat_setting"], "Room Air")

    def test_sn_visit_form_filling(self):
        """Test SN Visit form filling with complete data"""
        with open(self.sample_input_path, 'r') as f:
            input_data = json.load(f)
        
        sn_form = FormDefinition.load(str(self.sn_form_path))
        filler = FormFiller(sn_form, input_data)
        result = filler.fill()
        
        # Check required fields
        self.assertEqual(result["patient_name"], "Doe, John - MRN12345")
        self.assertEqual(result["visit_date"], "2025-05-05")
        self.assertTrue(result["precautions_maintained"])
        
        # Check vitals_sn
        self.assertEqual(result["vitals_sn"]["temperature_f"], 98.7)
        self.assertEqual(result["vitals_sn"]["temp_method"], "Oral")
        self.assertEqual(result["vitals_sn"]["pulse_rate"], 72)
        self.assertEqual(result["vitals_sn"]["pulse_regularity"], "Regular")
        
        # Check cardiovascular_sn
        self.assertFalse(result["cardiovascular_sn"]["wnl"])
        self.assertTrue(result["cardiovascular_sn"]["dizziness"]["is_present"])
        self.assertIn("lightheadedness", result["cardiovascular_sn"]["dizziness"]["details"])
        self.assertEqual(result["cardiovascular_sn"]["heart_sounds_abnormal"], ["Irregular Rhythm"])

    def test_pt_evaluation_form_filling(self):
        """Test PT Evaluation form filling with required fields"""
        with open(self.sample_input_path, 'r') as f:
            input_data = json.load(f)
        
        pt_eval_form = FormDefinition.load(str(self.pt_eval_form_path))
        filler = FormFiller(pt_eval_form, input_data)
        result = filler.fill()
        
        # Check that previously missing fields are now correctly mapped
        self.assertEqual(result["patient_name"], "Doe, John - MRN12345")
        self.assertEqual(result["visit_date"], "2025-05-05")
        self.assertEqual(result["relevant_medical_history"], 
                         "CHF, Hypertension, Osteoarthritis bilateral knees. Status post L TKA 3 weeks ago.")
        self.assertEqual(result["prior_level_of_function"], 
                         "Independent with ambulation and ADLs prior to surgery.")

    def test_missing_required_field(self):
        """Test handling of missing required fields"""
        # Create input data missing required fields
        incomplete_data = {
            "patient_identifier": "Doe, John - MRN12345"
            # Missing visit_date and other required fields
        }
        
        pt_form = FormDefinition.load(str(self.pt_form_path))
        filler = FormFiller(pt_form, incomplete_data)
        
        # Should raise MissingFieldError
        with self.assertRaises(MissingFieldError):
            filler.fill()

    def test_invalid_field_type(self):
        """Test handling of invalid field types"""
        # Create input with wrong data types
        invalid_data = {
            "patient_identifier": "Doe, John - MRN12345",
            "date_of_visit": "2025-05-05",
            "homebound_is_criteria_1_met": "yes",  # Should be boolean
            "homebound_reasoning_criteria_1": True,  # Should be string
            "homebound_is_criteria_2_met": True,
            "homebound_reasoning_criteria_2": "Severe pain"
        }
        
        pt_form = FormDefinition.load(str(self.pt_form_path))
        filler = FormFiller(pt_form, invalid_data)
        
        # Should raise InvalidFieldTypeError
        with self.assertRaises(InvalidFieldTypeError):
            filler.fill()

    def test_minimal_input_data(self):
        """Test with minimal input data"""
        with open(self.minimal_input_path, 'r') as f:
            minimal_data = json.load(f)
        
        # Test with PT evaluation form
        pt_eval_form = FormDefinition.load(str(self.pt_eval_form_path))
        filler = FormFiller(pt_eval_form, minimal_data)
        result = filler.fill()
        
        self.assertEqual(result["patient_name"], "Smith, Jane - MRN67890")
        self.assertEqual(result["visit_date"], "2025-05-01")
        self.assertEqual(result["relevant_medical_history"], "Diabetes, Hypertension")
        self.assertEqual(result["prior_level_of_function"], "Independent with all ADLs")

    def test_aliases_and_transforms(self):
        """Test aliases and transform functions"""
        # Create custom input data to test specific transformations
        transform_test_data = {
            "patient_identifier": "Test Patient",
            "date_of_visit": "2025-01-01",
            "vital_hr": 80,
            "vital_pulse_regular": False,  # Test irregular pulse mapping
            "activities_performed": [
                {"activity": "Walking", "sets_completed": 1, "reps_completed": 5, "notes": "Test note"}
            ]
        }
        
        pt_form = FormDefinition.load(str(self.pt_form_path))
        filler = FormFiller(pt_form, transform_test_data)
        result = filler.fill()
        
        # Test exercise transformation
        self.assertEqual(result["exercises_performed"][0]["exercise_name"], "Walking")
        self.assertEqual(result["exercises_performed"][0]["notes"], "Test note")
        
        # Test vitals transformation
        self.assertEqual(result["vitals_pt"]["hr_prior"], 80)
        
        # Test SN form with irregular pulse
        sn_form = FormDefinition.load(str(self.sn_form_path))
        sn_filler = FormFiller(sn_form, transform_test_data)
        sn_result = sn_filler.fill()
        
        self.assertEqual(sn_result["vitals_sn"]["pulse_regularity"], "Irregular")


if __name__ == "__main__":
    unittest.main(verbosity=2)