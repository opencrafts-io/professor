# AI Study Tools

Professor turns a student's own lecture notes into study material. A student
uploads a document, asks for one or more outputs, and polls a job until the
artifacts are ready.

## What it generates

- **Summaries**: a titled, sectioned summary of the document.
- **Questions**: practice questions in three formats, flashcards,
  multiple choice, and open ended.
- **Podcasts**: a two-host audio conversation (MP3) that walks through the
  document's key ideas.
- **Study plans**: a prioritized topic list built from several documents at
  once, with suggested minutes per topic and a citation of which document
  each topic comes from.
- **Suggested sessions**: a study plan converted into concrete calendar
  sessions, shaped so the Academia frontend can forward them to Keep Up's
  agenda API as they are.

## How it works

1. **Upload.** `POST api/notes/` accepts PDF, Word, PowerPoint, and Excel
   files. The file type is verified by magic bytes, not just the extension.
2. **Generate.** `POST api/notes/{id}/generate/` queues a background job.
   Multiple outputs can be bundled into one request, which is cheaper than
   requesting them one at a time because they share a single model call.
3. **Poll.** `GET api/notes/jobs/{job_id}/` reports `pending`,
   `processing`, `done`, or `failed`. Failures carry a stable
   `failure_code` so the client can distinguish a retryable provider
   problem from a permanently unreadable file.
4. **Fetch.** Each artifact has its own endpoint, for example
   `GET api/notes/{id}/summary/`.

Documents are converted to Markdown once and cached on the note, so repeat
generations skip the conversion cost. Scanned PDFs with no extractable text
fall back to being read natively by the model.

## Access and limits

- Every endpoint requires the platform's standard bearer token.
- Endpoints additionally require an active AI entitlement; requests without
  one receive `403 entitlement_required`.
- Daily per-user quotas apply to uploads, generation jobs, and podcasts.
  Exceeding one returns `429 quota_exceeded` with the quota name, the limit,
  and today's usage in the error details. Quotas reset at midnight UTC.

## Reliability behavior worth knowing

- Transient model-provider failures are retried automatically with backoff
  before a job is failed, so a `processing` job can take a couple of
  minutes during a provider incident.
- A job stuck in `processing` well past the worker's time limit is marked
  `failed` the next time it is polled, and the generation can simply be
  requested again.
- When a bundled job fails partway (for example audio synthesis fails after
  the summary was saved), the artifacts that completed remain available.
  The artifact endpoints, not the job status, are the source of truth for
  what exists.

See the [AI API reference](ai_api_reference.md) for request and response
shapes, the full error code vocabulary, and examples.
