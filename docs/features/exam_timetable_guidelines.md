API for providing you with your school information.

---

## Exam Timetable API

```
```
### Introduction & Purpose

The **Exam Timetable API** provides an interface to ingest exam schedule data and serve it directly to the Academia app.

**Who is this for?**
This endpoint is intended for institutional administrators and/or developers who need to enable exam tracking for their students. By following the data contract below, you can ensure your institution's schedules are seamlessly integrated into the Academia mobile.

---

### Data Contract

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

## Endpoint

```
POST /exams/ingest/
```

Submit a batch of exam schedules for ingestion.

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

