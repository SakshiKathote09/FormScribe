import json
import argparse
import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# --- Exceptions ---
class FormFillerError(Exception): pass
class MissingFieldError(FormFillerError): pass
class InvalidFieldError(FormFillerError): pass

# --- Field Definition ---
class FieldDefinition:
    def __init__(self, definition: Dict[str, Any]):
        self.definition = definition  # 🔧 Store original for later reuse
        self.id = definition["id"]
        self.name = definition.get("name", self.id)
        self.type = definition["type"]
        self.required = definition.get("required", False)
        self.required_if: Optional[Dict[str, Any]] = definition.get("required_if")
        self.visible_if: Optional[Dict[str, Any]] = definition.get("visible_if")
        self.format = definition.get("format")
        self.values = definition.get("values")
        self.must_be_true = "must_be_true" in definition.get("rules", []) if definition.get("rules") else False
        self.transform_map: Optional[Dict[Any, Any]] = definition.get("transform_map")
        self.transform_date = (self.format == "YYYY-MM-DD")

        self.properties: List[FieldDefinition] = []
        self.item_definition: Optional[FieldDefinition] = None
        if self.type == "object":
            for prop_def in definition.get("properties", []):
                self.properties.append(FieldDefinition(prop_def))
        elif self.type == "array":
            item_type = definition.get("item_type")
            if not isinstance(item_type, dict):
                raise ValueError(f"Field '{self.id}' is array but item_type is invalid.")
            self.item_definition = FieldDefinition({**item_type, "id": f"{self.id}_item"})

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
        self.errors: List[Dict[str, Any]] = []

    def fill(self) -> Dict[str, Any]:
        logger.info("Starting form fill")
        data = self._process_fields(self.form.fields)
        logger.info("Finished form fill")
        return {
            "data": data,
            "errors": self.errors
        }

    def _process_fields(self, fields: List[FieldDefinition]) -> Dict[str, Any]:
        output: Dict[str, Any] = {}
        for field in fields:
            logger.debug(f"Processing field: {field.id}")

            if field.visible_if:
                key, expected = next(iter(field.visible_if.items()))
                if self.input_data.get(key) != expected:
                    logger.debug(f"Skipping {field.id}: visible_if condition not met")
                    continue

            value = self._extract_value(field)

            if field.required_if:
                key, expected = next(iter(field.required_if.items()))
                field_required = self.input_data.get(key) == expected
            else:
                field_required = field.required

            if value is None:
                if field_required:
                    self.errors.append({"field": field.id, "error": "missing_required", "message": f"Missing required field '{field.id}'"})
                    logger.error(f"Missing required field '{field.id}'")
                continue

            try:
                if field.type == "object":
                    if not isinstance(value, dict):
                        raise InvalidFieldError("expected object")
                    sub = FormFiller(FormDefinition({"form_id": self.form.form_id, "form_name": self.form.form_name, "fields": [prop.__dict__ for prop in field.properties]}), value)
                    result = sub.fill()
                    self.errors.extend(result["errors"])
                    output[field.id] = result["data"]

                elif field.type == "array":
                    if not isinstance(value, list):
                        raise InvalidFieldError("expected array")
                    items = [self._process_item(field.item_definition, item) for item in value]
                    output[field.id] = items

                else:
                    self._validate(field, value)
                    transformed = self._transform(field, value)
                    output[field.id] = transformed
                    logger.info(f"Filled field: {field.id}")

            except FormFillerError as fe:
                self.errors.append({"field": field.id, "error": type(fe).__name__, "message": str(fe), "value": value})
                logger.error(f"Validation error for {field.id}: {fe}")

        return output

    def _process_item(self, definition: FieldDefinition, item: Any) -> Any:
        if definition.type == "object":
            return FormFiller(FormDefinition({"form_id": self.form.form_id, "form_name": self.form.form_name, "fields": [p.__dict__ for p in definition.properties]}), item).fill()["data"]
        else:
            self._validate(definition, item)
            return self._transform(definition, item)

    def _extract_value(self, field: FieldDefinition) -> Any:
        if field.id in self.input_data:
            return self.input_data[field.id]

        alias = self.alias_map.get(field.id)
        if alias:
            try:
                value = alias(self.input_data) if callable(alias) else self.input_data.get(alias)
                if value is not None:
                    self.input_data[field.id] = value
                    logger.debug(f"Alias injected for {field.id}")
                    return value
            except Exception as e:
                logger.warning(f"Alias function for {field.id} raised: {e}")
        return None

    def _validate(self, field: FieldDefinition, value: Any):
        if field.must_be_true and value is not True:
            raise FormFillerError("must_be_true rule not satisfied")

        if field.type == "string":
            if not isinstance(value, (str, int, float)):
                raise InvalidFieldError("expected string")
            if field.format == "YYYY-MM-DD":
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
                    raise InvalidFieldError("invalid date format, expected YYYY-MM-DD")
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError:
                    raise InvalidFieldError("invalid date")
        elif field.type == "integer":
            if not (isinstance(value, int) or (isinstance(value, str) and value.isdigit())):
                raise InvalidFieldError("expected integer")
        elif field.type == "float":
            try:
                float(value)
            except:
                raise InvalidFieldError("expected float")
        elif field.type == "boolean":
            if not isinstance(value, bool):
                raise InvalidFieldError("expected boolean")
        elif field.type == "enum":
            if not isinstance(value, str):
                raise InvalidFieldError("expected enum string")
            if field.values and value not in field.values:
                raise InvalidFieldError(f"value '{value}' not in enum {field.values}")

    def _transform(self, field: FieldDefinition, value: Any) -> Any:
        if field.transform_map and value in field.transform_map:
            return field.transform_map[value]
        if field.transform_date:
            dt = datetime.strptime(value, "%Y-%m-%d")
            return dt.isoformat()
        if field.type == "integer":
            return int(value)
        if field.type == "float":
            return float(value)
        return value

    def _build_alias_map(self) -> Dict[str, Union[str, callable]]:
        return {
            "patient_name": "patient_identifier",
            "visit_date": "date_of_visit",
            "relevant_medical_history": "medical_history_notes",
            "prior_level_of_function": "functioning_level_prior",
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
            "exercises_performed": lambda data: [
                {
                    "exercise_name": item.get("activity"),
                    "sets": item.get("sets_completed"),
                    "reps": item.get("reps_completed"),
                    "notes": item.get("notes")
                }
                for item in data.get("activities_performed", [])
            ] if "activities_performed" in data else None,
            "vitals_pt": lambda data: {
                "hr_prior": data.get("vital_hr"),
                "hr_during": data.get("vital_hr_during_activity"),
                "hr_post": data.get("vital_hr_post_activity"),
                "bp_prior": data.get("vital_bp_sitting"),
                "bp_prior_position": "Sitting" if data.get("vital_bp_sitting") else None,
                "o2_sat_prior": data.get("vital_o2_sat"),
                "o2_sat_setting": data.get("vital_o2_mode"),
                "pt_vitals_comments": data.get("general_comments")
            } if any(data.get(k) is not None for k in [
                "vital_hr", "vital_hr_during_activity", "vital_hr_post_activity", 
                "vital_bp_sitting", "vital_o2_sat"
            ]) else None
        }

# --- CLI Handler ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--form", required=True, help="Path to form definition JSON")
    parser.add_argument("--input", required=True, help="Path to input JSON data")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    try:
        form_def = FormDefinition.load(args.form)
        with open(args.input) as f:
            input_data = json.load(f)

        filler = FormFiller(form_def, input_data)
        result = filler.fill()

        print(json.dumps(result, indent=2))

    except Exception as e:
        logger.exception("Fatal error running form filler")
        print(f"[FATAL] {e}")

if __name__ == "__main__":
    main()