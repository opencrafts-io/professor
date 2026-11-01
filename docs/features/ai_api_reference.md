# AI API Reference

Base path: `api/notes/`. Authentication: the platform's standard bearer
token, the same one used by the other Professor endpoints. All premium
endpoints additionally require an active AI entitlement.

## Conventions

- Pagination is DRF page-number style: `?page=N`, 30 items per page.
- All datetimes are ISO 8601 UTC.
- Every error uses one envelope:

```json
{
  "error": {
    "code": "unsupported_file_type",
    "message": "Only PDF, Word (.docx), PowerPoint (.pptx), and Excel (.xlsx/.xls) files are accepted.",
    "details": {}
  }
}
```

`code` is stable and machine readable. Switch on it, never on `message`.

## Error codes

| HTTP | code | meaning |
|---|---|---|
| 400 | `validation_error` | Bad request body or params; `details` has field errors |
| 400 | `unsupported_file_type` | Extension or magic bytes check failed; `details.supported` lists accepted extensions |
| 400 | `file_too_large` | Over the size cap; the cap is in `details.max_bytes` |
| 401 | `authentication_failed` | Missing or invalid bearer token |
| 403 | `entitlement_required` | No active AI entitlement |
| 403 | `entitlement_unavailable` | Entitlement could not be verified; retry later |
| 404 | `not_found` | Resource does not exist or is not yours |
| 409 | `job_already_running` | A job for this note or plan is already in flight; `details.job_id` is the running job, resume polling it |
| 429 | `quota_exceeded` | A daily or monthly quota was hit; `details` carries `quota`, `limit`, and `used` |
| 500 | `internal_error` | Unexpected server error |

**Job failure codes**, returned inside the job status rather than as HTTP
errors: `file_unreadable`, `conversion_failed`, `llm_provider_error`,
`llm_invalid_output`, `tts_provider_error`, `internal_error`.

## Quotas

Each user has daily and monthly limits. Both are UTC calendar windows:
daily limits reset at midnight UTC, monthly limits on the first of the
month. The defaults are 20 uploads, 10 generation jobs, and 3 podcasts
per day, plus 40 generation jobs and 8 podcasts per month; deployments
can tune them. The `quota` field in the error details names the limit
that was hit, for example `generations_per_day` or `podcasts_per_month`.
Every accepted generation request counts toward the quota, including
requests whose job later fails.

## Notes

### Upload

`POST api/notes/` (multipart form)

Fields: `file` (required; PDF, `.docx`, `.pptx`, `.xlsx`, or `.xls`),
`course_id` (course UUID, optional), `course_label` (free text, optional,
for courses not in the catalog).

Returns `201`:

```json
{
  "id": 41,
  "course_id": null,
  "course_label": "Signals and Systems",
  "original_filename": "lecture3.pdf",
  "size_bytes": 482113,
  "uploaded_at": "2026-09-01T09:30:00Z"
}
```

### List and detail

- `GET api/notes/` returns the caller's notes, paginated, newest first.
- `GET api/notes/{id}/` returns one note plus its available artifacts:

```json
{
  "id": 41,
  "artifacts": {
    "summary": true,
    "questions": ["flashcard"],
    "podcast": false,
    "study_plans": [3]
  }
}
```

- `DELETE api/notes/{id}/` returns `204` and removes the file and all
  derived artifacts.

## Generation

`POST api/notes/{id}/generate/`

```json
{ "outputs": ["summary", "questions"], "question_format": "flashcard" }
```

- `outputs`: any of `summary`, `questions`, `podcast`. Multiple outputs in
  one request share a single model call, so bundling is cheaper than
  separate requests.
- `question_format` is required when `questions` is requested:
  `flashcard`, `mcq`, or `open_ended`.

Extracted document text sent to the model is capped at 300,000
characters, counted across all of a study plan's documents combined. A
document over the cap fails its job with the `conversion_failed` code.

Returns `202` with `{ "job_id": 90 }`, or `409 job_already_running` with
the running job's id in `details.job_id`.

### Job polling

`GET api/notes/jobs/{job_id}/`

```json
{
  "id": 90,
  "note_id": 41,
  "outputs": ["summary", "questions"],
  "status": "processing",
  "failure_code": null,
  "failure_message": null,
  "created_at": "2026-09-01T09:31:00Z",
  "finished_at": null
}
```

`status` moves `pending`, then `processing`, then `done` or `failed`. Poll
every 2 to 3 seconds; generation typically finishes well under a minute.

Reliability notes:

- Transient provider failures are retried with backoff before the job is
  failed with `llm_provider_error`, so a job can legitimately stay
  `processing` for about two minutes during a provider incident.
- A job stuck in `processing` for over 15 minutes is failed with
  `internal_error` on the next poll. Request the generation again.
- Artifacts persist as each one completes. A bundled job that fails late
  can leave earlier artifacts fetchable even though the job reads
  `failed`. Treat the artifact endpoints as the source of truth.

## Artifacts

### Summary

`GET api/notes/{id}/summary/`

```json
{
  "note_id": 41,
  "generated_at": "2026-09-01T09:31:40Z",
  "content": {
    "title": "Fourier Analysis, Lecture 3",
    "sections": [
      { "heading": "Key ideas", "points": ["..."] }
    ],
    "closing_message": "..."
  }
}
```

Returns `404 not_found` until one exists.

### Questions

`GET api/notes/{id}/questions/?format=flashcard` (omit `format` for all sets)

```json
{
  "note_id": 41,
  "sets": [
    {
      "id": 12,
      "format": "flashcard",
      "generated_at": "2026-09-01T09:31:40Z",
      "questions": [ { "front": "...", "back": "..." } ]
    }
  ]
}
```

Question shapes per format:

- `flashcard`: `{ "front", "back" }`
- `mcq`: `{ "question", "choices": ["..."], "answer_index", "explanation" }`
- `open_ended`: `{ "question", "model_answer" }`

### Podcast

`GET api/notes/{id}/podcast/`

```json
{
  "note_id": 41,
  "generated_at": "2026-09-01T09:33:00Z",
  "duration_seconds": 312,
  "audio_url": "https://.../podcast.mp3",
  "script": "..."
}
```

The audio is MP3, mono, with two alternating hosts.

## Study plans

`POST api/notes/study-plans/`

```json
{ "course_id": "<course uuid>", "note_ids": [41, 42, 45] }
```

Returns `202` with `{ "job_id": 91, "study_plan_id": 3 }`. Poll the job as
usual.

`GET api/notes/study-plans/{id}/`

```json
{
  "id": 3,
  "course_id": "<course uuid>",
  "note_ids": [41, 42, 45],
  "status": "done",
  "topics": [
    {
      "name": "Fourier transforms",
      "priority": 1,
      "suggested_minutes": 90,
      "source_note_ids": [41, 45]
    }
  ],
  "generated_at": "2026-10-05T18:12:00Z"
}
```

`source_note_ids` says which of the plan's notes each topic draws from. The
ids are validated server side against the plan's note set, so they are
always real and the UI can link a topic straight to its documents.

`POST api/notes/study-plans/{id}/regenerate/` returns `202` with a new
`job_id` and replaces the plan's topics when it finishes.

## Suggested sessions

`GET api/notes/study-plans/{id}/suggested-sessions/`

Converts a generated plan into concrete study sessions. This endpoint does
no AI work, it is pure scheduling, so it is free to call repeatedly and
responds instantly.

```json
{
  "study_plan_id": 3,
  "sessions": [
    {
      "summary": "Study: Fourier transforms",
      "description": "90-minute focused session (priority 1 in your study plan). Sources: lecture3.pdf.",
      "start_time": "2026-10-14T17:00:00Z",
      "end_time": "2026-10-14T18:30:00Z",
      "timezone": "UTC",
      "topic": "Fourier transforms",
      "source_note_ids": [41]
    }
  ]
}
```

Each session uses the exact field names Keep Up's agenda creation API
accepts, so the frontend can forward an accepted session object as it is,
using the same bearer token. The extra `topic` and `source_note_ids` keys
are Professor metadata and are ignored by Keep Up.

Scheduling rules:

- Sessions start the day after the request at 17:00 UTC, one topic per day
  in priority order, with 15 minute breaks when sessions stack on one day.
- If the plan's course has a term end date, sessions compress to fit
  before it.
- Returns `404` until the plan has topics.

### Exam mode

`?deadline=YYYY-MM-DD` overrides the term end date for students starting
close to an exam. The window starts today (the first session begins at the
next full hour), and when topics must stack, days start at 09:00 UTC
instead of 17:00. A past or malformed date returns
`400 validation_error`. The UI can let the student drag the exam date and
re-fetch live, since the endpoint is free to call.
