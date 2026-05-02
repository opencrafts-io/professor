# Professor

API for providing you with your school information.

---

## Exam Timetable API

### Overview

The Exam Timetable API provides an interface for ingesting and retrieving exam schedules. The API enforces a minimal schema with only essential fields.

---

### Data Contract — Input (Ingestion)

When submitting exam schedule data via the `/exams/ingest/` endpoint, you **must** provide only the following fields:

```json
{
  "institution_id": "string (required, max 100 chars, non-empty)",
  "semester_id": "integer (optional, nullable)",
  "items": [
    {
      "course_code": "string (required, non-empty)",
      "start_time": "ISO 8601 datetime (required)",
      "end_time": "ISO 8601 datetime (required)",
      "venue": "string (required, non-empty)",
      "coordinator": "string (optional)",
      "hrs": "string (required)",
      "raw_data": "object (optional, for institution-specific data)"
    }
  ]
}
```

---

### Data Contract — Output

When retrieving exam schedules, the API returns data in the following standardized format:

```json
{
  "course_code": "string",
  "start_time": "ISO 8601 datetime (UTC)",
  "end_time": "ISO 8601 datetime (UTC)",
  "venue": "string",
  "coordinator": "string",
  "hrs": "string",
  "semester": "integer or null",
  "institution_id": "string",
  "raw_data": "object",
  "created_at": "ISO 8601 datetime",
  "updated_at": "ISO 8601 datetime"
}
```

---

## Endpoints

### Ingest Exam Schedules

```
POST /exams/ingest/
```

Submit a batch of exam schedules for ingestion.

**Request Body:** See [Data Contract — Input](#data-contract--input-ingestion) above.

**Response:**

```json
{
  "message": "Ingestion completed successfully",
  "created_count": 150,
  "updated_count": 25,
  "skipped_count": 0
}
```

**Status Codes:**

| Code | Meaning |
|------|---------|
| `201 Created` | New records were created |
| `200 OK` | Only updates occurred |
| `400 Bad Request` | Invalid request payload |
| `500 Internal Server Error` | Server error during processing |

---

### Get Exams by Course Codes

```
POST /exams/by-codes/
```

Retrieve exam schedules for a list of course codes.

**Request Body:**

```json
{
  "institution_id": "string (required)",
  "course_codes": ["CS101", "CS102", "CS103"]
}
```

**Response:** A list of exam records matching the provided course codes. Each record follows the [Output Data Contract](#data-contract--output) above.
