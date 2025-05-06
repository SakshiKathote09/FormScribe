import json
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from adaptive_form_filler.src.main import FormDefinition, FormFiller

def run_test(form_path: str, input_path: str):
    try:
        print(f"Running test with form: {form_path}")
        form_def = FormDefinition.load(form_path)

        with open(input_path) as f:
            input_data = json.load(f)

        filler = FormFiller(form_def, input_data)
        filled_output = filler.fill()

        print("✅ Filled Output:")
        print(json.dumps(filled_output, indent=2))

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    # Modify paths if necessary to match your structure
    run_test("test/data/form_pt_visit.json", "test/data/sample_input_data.json")
    run_test("test/data/form_pt_evaluation.json", "test/data/sample_input_data.json")
    run_test("test/data/form_sn_visit.json", "test/data/sample_input_data.json")
