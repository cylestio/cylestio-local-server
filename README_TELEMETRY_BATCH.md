# Telemetry Batch Submission Guide

This guide explains how to submit telemetry event batches to the Cylestio Local Server API.

## Required Format

The API expects batches in the following format:

```json
{
  "events": [
    {
      "schema_version": "1.0",
      "timestamp": "2023-06-01T12:00:00Z",
      "trace_id": "trace-123456",
      "span_id": "span-123456",
      "name": "llm.request",
      "level": "INFO",
      "agent_id": "my-agent",
      "attributes": {
        "llm.request.model": "gpt-4",
        "llm.request.tokens": 150,
        "status": "success"
      }
    },
    // More events...
  ]
}
```

**Note:** The key point is that the batch must be a JSON object with an `events` key containing an array of events, not just a plain JSON array.

## Utility Scripts

Two utility scripts are provided to help with batch submission:

### 1. `convert_telemetry_batch.py`

This script converts a raw JSON array of events to the proper format for batch submission.

```bash
# Basic usage
./convert_telemetry_batch.py your_events_array.json

# Specify output file
./convert_telemetry_batch.py your_events_array.json formatted_batch.json
```

The script will create a properly formatted JSON file that includes the `events` wrapper.

### 2. `submit_batch.py`

This script submits a properly formatted batch file to the API.

```bash
# Basic usage (default API URL: http://localhost:8002)
./submit_batch.py formatted_batch.json

# Specify API URL
./submit_batch.py formatted_batch.json http://api.example.com
```

## Combined Usage

You can also use both scripts together in a pipeline:

```bash
# Convert and then submit
./convert_telemetry_batch.py your_events_array.json formatted_batch.json && ./submit_batch.py formatted_batch.json
```

## API Response Format

A successful batch submission will return a 201 Created response with the following structure:

```json
{
  "success": true,
  "total": 10,
  "processed": 10,
  "failed": 0,
  "details": null
}
```

If some events fail to process, the response will include details about the failures:

```json
{
  "success": false,
  "total": 10,
  "processed": 8,
  "failed": 2,
  "details": [
    {
      "index": 2,
      "error": "Invalid event format",
      "event_name": "problematic.event"
    },
    {
      "index": 5,
      "error": "Missing required field",
      "event_name": "another.problem"
    }
  ]
}
``` 