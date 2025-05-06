# Adaptive Form Filler

A flexible system for filling standardized forms based on JSON definitions and input data.

## Language & Libraries

- **Language**: Python 3.x
- **Libraries**: Only standard libraries are used:
  - `json`: For parsing JSON files
  - `argparse`: For command-line argument handling
  - `typing`: For type annotations

## How to Run

```bash
 python3 adaptive_form_filler/src/main.py --form <path_to_form_definition.json> --input <path_to_input_data.json>
```

Example:
```bash
python3 adaptive_form_filler/src/main.py --form test/data/form_pt_evaluation.json --input test/data/sample_input_data.json
```

## How to Run Tests

```bash
python3 test/test_form_filler.py
```

### You can quickly review run results in example_runs for sample cases. stdout is enabled for cli runs.

## Design Approach

The system is designed using Object-Oriented principles to support flexible form filling based on JSON definitions:

### Key Components

1. **FieldDefinition**: Represents a single field in a form with properties like type, required status, and format
2. **FormDefinition**: Contains the overall form structure with a collection of field definitions
3. **FormFiller**: Core engine that processes input data against form definitions to generate filled forms

### Design Decisions

- **Strong Type Validation**: Each field undergoes type checking to ensure data integrity
- **Aliasing System**: Supports flexible mapping of input data to form fields through direct mappings and transformation functions
- **Error Handling**: Clear exceptions are raised for missing required fields and type mismatches
- **Modularity**: The code separates concerns between parsing definitions, processing data, and generating output

### Error Handling Approach

The system handles errors in several ways:
- **MissingFieldError**: Thrown when a required field is missing from the input data
- **InvalidFieldTypeError**: Thrown when input data does not match the expected type for a field
- **Debug Logging**: The system logs when fields are injected via aliases for debugging purposes

### Extensibility

The design is extensible in several ways:
- New field types can be added by extending the `_validate_type` method
- Additional processing logic can be incorporated by extending the alias map
- The system supports nested objects and arrays, allowing for complex form structures

## Assumptions

1. Form definitions follow a consistent structure with fields having at minimum an ID and type
2. Input data may have fields that don't perfectly match the form field IDs (handled via aliases)
3. When a field is marked as required, its absence should raise an error rather than produce a partial result
4. Enum values in the form definitions are treated as strings for validation purposes
5. The system focuses on data validation and transformation rather than UI rendering

## 💡 Design Overview

### Core Components

1. **FieldDefinition**  
   Represents a field and its metadata including:
   - ID, type, format
   - Visibility/requirement conditions
   - Nested structure for arrays/objects
   - Rules like `must_be_true`, enum validation, transformations

2. **FormDefinition**  
   Loads and manages the overall form schema composed of fields.

3. **FormFiller**  
   The core engine:
   - Processes input data
   - Validates and transforms fields
   - Handles nested structures (objects and arrays)
   - Injects aliases and custom logic


## 🔍 Key Features

- ✅ **Strong Type Validation** for string, date, enum, int, float, boolean
- 🧠 **Conditional Fields** (`required_if`, `visible_if`)
- 🔁 **Nested Support** for objects and arrays
- 🔄 **Value Transformations** (`transform_map`, ISO date, etc.)
- 🏷️ **Alias Mapping** with static or lambda-based value injection
- 🚨 **Error Collection** instead of hard failure
- 📋 **Modular Structure** for extensibility


## 🔐 Error Handling

- `MissingFieldError`: Required field missing
- `InvalidFieldError`: Field exists but of invalid type/format
- `FormFillerError`: Rule violations (e.g. `must_be_true`)
- Centralized error collection per field with traceable context

## 🔄 Transform & Alias Map Examples

Example mappings:
- `patient_name` ← `patient_identifier`
- `homebound_status` ← computed from four fields
- `exercises_performed` ← transformed from `activities_performed`
- `vitals_pt` ← structured vitals mapping from flat input