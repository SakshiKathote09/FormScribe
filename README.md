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