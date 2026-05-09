# Incident Report: Exam Schedule Ingestion Performance Degradation

## Incident Details

April 20, 2026

### Severity
**High** - Production API endpoint experiencing timeout failures

### Impact
- **Affected Endpoint**: `POST /api/exams/ingest`
- **Affected Users**: Users were not directly affected however it was impossible to upload data in one go
- **Failure Rate**: 100% for payloads containing ~1000 items (in this case Daystar university timetable data)
- **Response Time**: >10 seconds, leading to database worker timeout
- **System Impact**: Exam schedule ingestion requests failed completely

---

## Root Cause Analysis

### Problem Statement
When sending a JSON payload containing approximately 1,000 exam schedule items to the ingestion endpoint, the request would consistently exceed 10 seconds in execution time, ultimately resulting in a database worker timeout and complete request failure.

### Technical Root Causes

#### 1. **Sequential Processing (N+1 Query Pattern)**
- **Issue**: The implementation used `update_or_create()` within a loop, resulting in **two database round-trips per item** (one SELECT query and one INSERT/UPDATE query)
- **Impact**: For 1,000 items, this meant 2,000+ database queries

#### 2. **Long-Running Transactions**
- **Issue**: The entire ingestion process was wrapped in a single `transaction.atomic()` block
- **Impact**: This caused:
  - Lock contention on the `ExamSchedule` table
  - Increased memory overhead
  - Risk of transaction timeout for large datasets

#### 3. **Missing Database Indexes**
- **Issue**: Lookups on `(institution_id, semester, course_code)` were not backed by a composite index
- **Impact**: As the table grew, query execution degraded significantly

---

## Solution Implemented

### Key Optimizations

#### 1. **Bulk Operations**
Refactored `IngestExamScheduleView` to leverage Django ORM's `bulk_create()` and `bulk_update()` methods:

- **Pre-fetch Strategy**: Existing records are now fetched in a **single query** instead of per-item
- **Batch Create**: New records are inserted in batches (batch_size=100)
- **Batch Update**: Updated records are processed in batches with an explicit field list

**Code Implementation**:
```python
# Before: O(n) queries
for item in items:
    obj, created = ExamSchedule.objects.update_or_create(...)

# After: O(1) + O(n/100) queries
existing_exams = ExamSchedule.objects.filter(
    institution_id=institution_id,
    semester_id=semester_id,
    course_code__in=course_codes,  # Single query
)
ExamSchedule.objects.bulk_create(items_to_create, batch_size=100)
ExamSchedule.objects.bulk_update(items_to_update, fields_to_update, batch_size=100)
