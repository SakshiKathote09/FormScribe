import json
import argparse
from typing import Any, Dict, List, Optional, Union


# --- Exceptions ---
class FormFillerError(Exception): pass
class MissingFieldError(FormFillerError): pass
class InvalidFieldTypeError(FormFillerError): pass


# --- Field Definition ---
class FieldDefinition:
    def __init__(self, definition: Dict[str, Any]):
        self.id = definition["id"]
        self.name = definition.get("name", self.id)
        self.type = definition["type"]
        self.required = definition.get("required", False)
        self.format = definition.get("format", None)
        self.properties = []
        self.item_type = definition.get("item_type", None)
        self.item_definition = None
        self.values = definition.get("values", None)  # Add support for enum values

        if self.type == "object":
            self.properties = [FieldDefinition(p) for p in definition.get("properties", [])]
        elif self.type == "array":
            if not isinstance(self.item_type, dict):
                raise ValueError(f"Field '{self.id}' is type array but item_type is not valid.")
            self.item_definition = FieldDefinition({**self.item_type, "id": f"{self.id}_item"})


# --- Form Definition ---
class FormDefinition:
    def __init__(self, definition: Dict[str, Any]):
        self.form_id = definition["form_id"]
        self.form_name = definition["form_name"]
        self.fields = [FieldDefinition(f) for f in definition["fields"]]

    @staticmethod
    def load(path: str) -> 'FormDefinition':
        with open(path, 'r') as f:
            return FormDefinition(json.load(f))


# --- Core Form Filler ---
class FormFiller:
    def __init__(self, form: FormDefinition, input_data: Dict[str, Any]):
        self.form = form
        self.input_data = input_data.copy()
        self.alias_map = self._build_alias_map()

    def fill(self) -> Dict[str, Any]:
        return self._process_fields(self.form.fields)

    def _process_fields(self, fields: List[FieldDefinition]) -> Dict[str, Any]:
        output = {}
        for field in fields:
            value = self._extract_value(field)
            if value is None:
                if field.required:
                    raise MissingFieldError(f"Missing required field: {field.id}")
                continue

            if field.type == "object":
                if not isinstance(value, dict):
                    raise InvalidFieldTypeError(f"Expected object for field {field.id}")
                sub_filler = FormFiller(FormDefinition({
                    "form_id": self.form.form_id,
                    "form_name": self.form.form_name,
                    "fields": [
                        {"id": p.id, "name": p.name, "type": p.type, "required": p.required, "format": p.format,
                         "properties": [prop.__dict__ for prop in p.properties] if p.type == "object" else None,
                         "item_type": p.item_type if p.type == "array" else None,
                         "values": p.values if p.type == "enum" else None} for p in field.properties
                    ]
                }), value)
                output[field.id] = sub_filler.fill()

            elif field.type == "array":
                if not isinstance(value, list):
                    raise InvalidFieldTypeError(f"Expected array for field {field.id}")
                output[field.id] = [self._process_item(field.item_definition, item) for item in value]
            else:
                if not self._validate_type(field.type, value, field.values):
                    raise InvalidFieldTypeError(f"Type mismatch for field {field.id}. Expected {field.type}, got {type(value).__name__}")
                if field.type == "string":
                    output[field.id] = str(value)
                elif field.type == "integer":
                    output[field.id] = int(float(value)) if isinstance(value, str) and value.replace('.', '', 1).isdigit() else int(value)
                elif field.type == "float":
                    output[field.id] = float(value)
                elif field.type == "enum":
                    # For enum types, just use the value as-is (after validation)
                    output[field.id] = value
                else:
                    output[field.id] = value
        return output

    def _process_item(self, definition: FieldDefinition, item: Any) -> Any:
        if definition.type == "object":
            sub_filler = FormFiller(FormDefinition({
                "form_id": self.form.form_id,
                "form_name": self.form.form_name,
                "fields": [
                    {"id": p.id, "name": p.name, "type": p.type, "required": p.required, "format": p.format,
                     "properties": [prop.__dict__ for prop in p.properties] if p.type == "object" else None,
                     "item_type": p.item_type if p.type == "array" else None,
                     "values": p.values if p.type == "enum" else None} for p in definition.properties
                ]
            }), item)
            return sub_filler.fill()
        else:
            return item

    def _extract_value(self, field: FieldDefinition) -> Any:
        value = self.input_data.get(field.id)
        if value is not None:
            return value

        alias = self.alias_map.get(field.id)
        if alias:
            if callable(alias):
                try:
                    value = alias(self.input_data)
                except Exception as e:
                    print(f"[WARN] Alias error for {field.id}: {e}")
            elif isinstance(alias, str):
                value = self.input_data.get(alias)
            if value is not None:
                self.input_data[field.id] = value
                print(f"[DEBUG] Injected alias field: {field.id}")
        return value

    def _validate_type(self, expected_type: str, value: Any, enum_values: Optional[List[str]] = None) -> bool:
        if expected_type == "string":
            return isinstance(value, (str, int, float))
        elif expected_type == "integer":
            return isinstance(value, int) or (isinstance(value, str) and value.replace('.', '', 1).isdigit())
        elif expected_type == "float":
            return isinstance(value, (float, int)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit())
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "object":
            return isinstance(value, dict)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "enum":
            # For enum types, check if the value is a string and optionally if it's in the enum values list
            valid_type = isinstance(value, str)
            if valid_type and enum_values:
                return value in enum_values
            return valid_type
        return False

    def _build_alias_map(self) -> Dict[str, Union[str, callable]]:
        return {
            # Basic field mappings
            "patient_name": "patient_identifier",
            "visit_date": "date_of_visit",
            "precautions_maintained": "precautions_followed",
            
            # Added for PT evaluation form
            "relevant_medical_history": "medical_history_notes",
            "prior_level_of_function": "functioning_level_prior",
            
            # Homebound status mapping
            "homebound_status": lambda data: {
                "criteria_one_met": data.get("homebound_is_criteria_1_met"),
                "criteria_one_details": data.get("homebound_reasoning_criteria_1"),
                "criteria_two_met": data.get("homebound_is_criteria_2_met"),
                "criteria_two_details": data.get("homebound_reasoning_criteria_2")
            } if all(data.get(k) is not None for k in [
                "homebound_is_criteria_1_met",
                "homebound_reasoning_criteria_1",
                "homebound_is_criteria_2_met",
                "homebound_reasoning_criteria_2"
            ]) else None,
            
            # Exercises performed mapping
            "exercises_performed": lambda data: [
                {
                    "exercise_name": item.get("activity"),
                    "sets": item.get("sets_completed"),
                    "reps": item.get("reps_completed"),
                    "notes": item.get("notes")
                } for item in data.get("activities_performed", [])
            ] if "activities_performed" in data else None,
            
            # Vitals SN mapping
            "vitals_sn": lambda data: {
                "temperature_f": data.get("vital_temp_f"),
                "temp_method": data.get("vital_temp_method"),
                "pulse_rate": data.get("vital_hr"),
                "pulse_regularity": "Regular" if data.get("vital_pulse_regular") else "Irregular",
                "pulse_site": data.get("vital_pulse_location"),
                "respiration_rate": data.get("vital_resp_rate"),
                "blood_pressure": data.get("vital_bp_sitting"),
                "bp_position": "Sitting",
                "blood_sugar_mgdl": data.get("vital_bs"),
                "blood_sugar_type": data.get("vital_bs_condition")
            } if any(k in data for k in ["vital_temp_f", "vital_hr", "vital_bs"]) else None,
            
            # Vitals PT mapping
            "vitals_pt": lambda data: {
                "hr_prior": data.get("vital_hr"),
                "hr_during": data.get("vital_hr_during_activity"),
                "hr_post": data.get("vital_hr_post_activity"),
                "bp_prior": data.get("vital_bp_lying"),
                "bp_prior_position": "Lying",
                "o2_sat_prior": data.get("vital_o2_sat"),
                "o2_sat_setting": data.get("vital_o2_mode")
            } if any(data.get(k) is not None for k in [
                "vital_hr", "vital_hr_during_activity", "vital_hr_post_activity",
                "vital_bp_lying", "vital_o2_sat", "vital_o2_mode"
            ]) else None,
            
            # Added for cardiovascular_sn
            "cardiovascular_sn": lambda data: {
                "wnl": not any([
                    data.get("cardio_symptoms_dizziness", False),
                    data.get("cardio_assessment_edema", False),
                    data.get("cardio_observed_heart_sounds")
                ]),
                "dizziness": {
                    "is_present": data.get("cardio_symptoms_dizziness", False),
                    "details": data.get("cardio_dizziness_details", "")
                } if data.get("cardio_symptoms_dizziness", False) else None,
                "heart_sounds_abnormal": data.get("cardio_observed_heart_sounds", []),
                "pacemaker_insertion_date": data.get("cardio_pacemaker_implant_date"),
                "sn_cardio_comments": data.get("cardio_edema_location_desc", "")
            }
        }


# --- CLI Handler ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--form", required=True, help="Path to form definition JSON")
    parser.add_argument("--input", required=True, help="Path to input JSON data")
    args = parser.parse_args()

    try:
        form_def = FormDefinition.load(args.form)
        with open(args.input) as f:
            input_data = json.load(f)

        filler = FormFiller(form_def, input_data)
        filled_output = filler.fill()

        print(json.dumps(filled_output, indent=2))

    except Exception as e:
        print(f"[ERROR] {e}")


if __name__ == "__main__":
    main()