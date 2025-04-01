#!/usr/bin/env python3
import json
import sys
import os

def convert_to_batch_format(input_file, output_file=None):
    """
    Convert a raw JSON array of telemetry events to the proper format 
    for batch submission (wrapping in a {"events": [...]} object).
    
    Args:
        input_file: Path to the input JSON file containing an array of events
        output_file: Path for the output file (defaults to input_file with '-formatted' suffix)
    
    Returns:
        Path to the created output file
    """
    if not output_file:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}-formatted{ext}"
    
    try:
        # Read the raw JSON array
        with open(input_file, 'r') as f:
            events = json.load(f)
        
        # Ensure it's an array
        if not isinstance(events, list):
            print(f"Error: Input file {input_file} does not contain a JSON array")
            return None
        
        # Create the properly formatted batch object
        batch = {"events": events}
        
        # Write the formatted JSON
        with open(output_file, 'w') as f:
            json.dump(batch, f, indent=2)
        
        print(f"Converted {len(events)} events from {input_file} to {output_file}")
        print(f"The file is now ready for submission to the /v1/telemetry/batch endpoint")
        return output_file
    
    except json.JSONDecodeError:
        print(f"Error: Could not parse {input_file} as valid JSON")
        return None
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_telemetry_batch.py <input_json_file> [output_json_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = convert_to_batch_format(input_file, output_file)
    sys.exit(0 if result else 1) 