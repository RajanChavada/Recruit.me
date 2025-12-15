# Implementation Plan: LinkedIn Profile Enrichment MVP

**Feature**: LinkedIn Profile Enrichment via Gemini 3 Vision + Personalized Email Generation  
**Brief**: See `MVP_BRIEF.md`  
**Status**: Ready for implementation (Phase 1)

---

## High-Level Steps

1. **Backend Setup** (FastAPI + PostgreSQL models)
2. **Playwright Scraper Service** (screenshot + HTML fetch)
3. **Gemini Vision Agent** (multimodal profile analysis)
4. **Enrichment Service** (orchestrates scraper + agent)
5. **API Endpoint** (POST /api/recruiters/enrich)
6. **Email Generator Service** (Gemini 3 Pro text)
7. **API Endpoint** (POST /api/recruiters/{id}/generate-email)
8. **React Frontend** (URL input → profile view → email)
9. **Testing** (unit + integration + E2E)
10. **Deployment** (out of scope for MVP)

---

## Step 1: Backend Setup & Models

### Objective
Create FastAPI project, PostgreSQL models, and config.

### Deliverables
- [ ] `backend/app/main.py` (FastAPI app)
- [ ] `backend/app/config.py` (environment + database setup)
- [ ] `backend/app/models.py` (SQLAlchemy models)
- [ ] `backend/app/schemas.py` (Pydantic DTOs)
- [ ] `backend/requirements.txt` (dependencies)
- [ ] PostgreSQL reachable via `DATABASE_URL` (bring your own DB)
- [ ] `backend/.env.example` (example env vars)

### Models
```python
class Recruiter(Base):
    __tablename__ = "recruiters"
    id: int
    linkedin_url: str (unique)
    first_name: str
    last_name: str
    email: str (optional)
    company_id: int (optional, foreign key)
    enriched: bool (default=False)
    created_at: datetime
    updated_at: datetime

class RecruiterProfile(Base):
    __tablename__ = "recruiter_profiles"
    id: int
    recruiter_id: int (foreign key, unique)
    hobbies: dict (JSONB)  # ["hiking", "photography"]
    professional_interests: dict (JSONB)  # ["AI", "startups"]
    inferred_values: dict (JSONB)  # ["community", "transparency"]
    communication_style: str  # "casual", "formal", "technical"
    bio_summary: str
    location: str
    confidence_score: float (0-1)
    enriched_at: datetime
    raw_gemini_response: str (for debugging)

class GeneratedEmail(Base):
    __tablename__ = "generated_emails"
    id: int
    recruiter_id: int (foreign key)
    subject_line: str
    body: str
    personalization_data: dict (JSONB)
    status: str  # "draft", "sent_manually"
    generated_at: datetime
```

### Dependencies
```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
pydantic
python-dotenv
google-generativeai
playwright
```

### Success Criteria
- [ ] FastAPI app starts: `uvicorn app.main:app --reload`
- [ ] PostgreSQL accessible via `DATABASE_URL`
- [ ] Database created: Tables exist in PostgreSQL
- [ ] API docs available: http://localhost:8000/docs (Swagger)
- [ ] Health check works: `curl http://localhost:8000/api/health` → `{"status": "ok"}`

---

## Step 2: Playwright Scraper Service

### Objective
Create async scraper that captures LinkedIn profile screenshot + HTML.

### Deliverables
- [ ] `backend/app/services/scraper.py`
- [ ] `tests/unit/test_scraper.py`

### Key Functions
```python
class LinkedInScraper:
    async def screenshot_linkedin(url: str) -> bytes:
        """Take screenshot of LinkedIn profile."""
        
    async def fetch_html(url: str) -> str:
        """Fetch raw HTML."""
        
    async def cleanup():
        """Delete temp files."""
```

### Implementation Details
- Use Playwright async API
- Timeout: 15 seconds per profile
- Retry once on timeout
- Log all failures with timestamp + URL
- Store screenshot temporarily, delete after Gemini processes
- Handle non-LinkedIn URLs (validate format)
- Set realistic User-Agent

### Tests
- Mock Playwright browser (don't hit real LinkedIn)
- Test timeout handling (raise exception after 15s)
- Test file cleanup (no orphaned temp files)
- Test invalid URL (raise LinkedInScraperError)

### Success Criteria
- [ ] `screenshot_linkedin()` returns PNG bytes
- [ ] `fetch_html()` returns valid HTML string
- [ ] Timeout after 15s with proper error
- [ ] Temp files cleaned up
- [ ] All unit tests pass: `pytest tests/unit/test_scraper.py`

---

## Step 3: Gemini Vision Agent

### Objective
Create multimodal agent that analyzes LinkedIn profile screenshot + HTML.

### Deliverables
- [ ] `backend/app/agents/linkedin_vision_agent.py`
- [ ] `tests/unit/test_linkedin_vision_agent.py`
- [ ] Refined Gemini prompt (tested in AI Studio first)

### Key Functions
```python
class LinkedInVisionAgent:
    async def analyze(
        screenshot: bytes,
        html: str,
        linkedin_url: str
    ) -> LinkedInProfileInsights:
        """Analyze profile, return structured insights."""
```

### Implementation Details
- Call Gemini 3 Pro Vision API
- Input: base64 screenshot + HTML context + structured prompt
- Output: JSON in the agreed schema (including attempting to extract recruiter email if explicitly visible)
- Parse JSON and validate (error if missing fields)
- Return LinkedInProfileInsights DTO
- Include confidence_score (0-1)
- Log raw Gemini response for debugging
- Handle parse errors gracefully (raise GeminiVisionError)
- Retry once on API timeout

### Gemini Prompt
```
[System]: You are an expert LinkedIn profile analyst.

Return JSON only. No markdown. No commentary.

Extract the fields in this exact schema:
{
  "name": string | null,
  "email": string | null,
  "current_role": string | null,
  "current_company": string | null,
  "unique_hooks": string[],
  "portfolio_links": string[],
  "communication_style": string | null,
  "suggested_angles": string[]
}

Rules:
- If a string is unknown, return null.
- If a list is unknown/empty, return [].
- Email must be explicitly visible in the screenshot or HTML. Do not guess.

[User]: Analyze this LinkedIn profile: [URL]
[Image]: [base64 screenshot]
[Context]: [HTML snippet]
```

### Tests (Mock Gemini Responses)
- Valid response → parsed correctly
- Missing field (e.g., no hobbies) → raises validation error
- Low confidence → still returns result, but marked
- Parse error (invalid JSON) → raises GeminiVisionError
- API timeout → retries and raises on failure

### Success Criteria
- [ ] Prompt tested on 3 real LinkedIn profiles in AI Studio
- [ ] Prompt achieves >70% confidence on realistic profiles
- [ ] `analyze()` returns valid LinkedInProfileInsights
- [ ] JSON parsing robust (handles missing fields gracefully)
- [ ] All unit tests pass: `pytest tests/unit/test_linkedin_vision_agent.py`
- [ ] Error handling follows CONVENTIONS.md

---

## Step 4: Enrichment Service

### Objective
Orchestrate scraper + Gemini agent + database save.

### Deliverables
- [ ] `backend/app/services/enrichment.py`
- [ ] `tests/integration/test_enrichment_service.py`

### Key Functions
```python
class EnrichmentService:
    async def enrich_from_linkedin(url: str) -> RecruiterProfileDTO:
        """
        Full workflow: scrape → analyze → store.
        Returns enriched profile DTO.
        """
```

### Workflow
1. Validate LinkedIn URL format
2. Check if URL already enriched (skip if <7 days old)
3. Call Playwright scraper (screenshot + HTML)
4. Call Gemini Vision Agent
5. Save to PostgreSQL:
   - Create Recruiter entry (if not exists)
   - Create RecruiterProfile entry
6. Clean up temp files
7. Return RecruiterProfileDTO

### Error Handling
- Invalid URL → raise ValueError (400)
- Scraper timeout → raise LinkedInScrapingError (400)
- Gemini parse failure → raise GeminiVisionError (400)
- Database error → raise DatabaseError (500)
- Log all errors with context

### Tests
- Full happy path (mock Playwright + Gemini)
- Integration test with real DB (test PostgreSQL)
- Idempotency (enriching same URL twice skips second)
- Cleanup temp files even on failure

### Success Criteria
- [ ] `enrich_from_linkedin()` completes end-to-end
- [ ] Profile stored in DB with all fields
- [ ] Temp files cleaned up
- [ ] Idempotency works (no duplicates)
- [ ] Integration tests pass: `pytest tests/integration/test_enrichment_service.py -v`

---

## Step 5: API Endpoint (Enrich)

### Objective
Expose enrichment via REST API.

### Deliverables
- [ ] `backend/app/routers/recruiters.py`
- [ ] Tests for endpoint

### Endpoint
```
POST /api/recruiters/enrich
Content-Type: application/json

Request:
{
  "linkedin_url": "https://linkedin.com/in/john-doe"
}

Response (200):
{
  "recruiter_id": 1,
  "name": "John Doe",
  "hobbies": ["hiking", "photography"],
  "professional_interests": ["AI"],
  "inferred_values": ["transparency"],
  "communication_style": "casual",
  "confidence_score": 0.85
}

Response (400):
{
  "detail": "Invalid LinkedIn URL format"
}
```

### Implementation
- Route: POST /api/recruiters/enrich
- Request validation (LinkedIn URL format)
- Call EnrichmentService
- Return DTO (200) or error (400/500)
- Add to FastAPI app in main.py

### Tests
- Valid URL → returns 200 + profile
- Invalid URL → returns 400
- Scraper timeout → returns 400
- Gemini error → returns 400

### Success Criteria
- [ ] Endpoint accessible: `curl -X POST http://localhost:8000/api/recruiters/enrich`
- [ ] All tests pass
- [ ] Documented in Swagger: http://localhost:8000/docs

---

## Step 6: Email Generator Service

### Objective
Generate personalized emails using enriched profile + Gemini 3 Pro.

### Deliverables
- [ ] `backend/app/services/email_generator.py`
- [ ] `tests/unit/test_email_generator.py`

### Key Functions
```python
class EmailGeneratorService:
    async def generate_email(
        recruiter_profile: RecruiterProfileDTO
    ) -> GeneratedEmailDTO:
        """Generate subject + body using Gemini 3 Pro."""
```

### Implementation Details
- Fetch RecruiterProfile from DB (given recruiter_id)
- Build Gemini prompt with personalization context:
  - Hobbies (e.g., "loves hiking")
  - Interests (e.g., "passionate about AI")
  - Communication style (e.g., "casual, warm")
  - Your background (software engineer, interested in ML roles)
- Call Gemini 3 Pro (text model)
- Parse response: extract Subject + Body
- Return GeneratedEmailDTO
- Handle parse errors (fallback to generic email if parse fails)

### Gemini Prompt Example
```
[System]: You are an expert cold outreach email writer.
Write a warm, personalized email that:
1. Opens with a genuine observation about the recipient
2. Mentions one specific hobby/interest
3. Transitions naturally to your background
4. Ends with a low-pressure ask

Keep it 100-150 words.

[User]: 
Recipient: John Doe, Recruiter at TechCorp
Their hobbies: ["hiking", "photography"]
Their interests: ["AI", "startups"]
Communication style: casual

Your background:
- Software engineer at UofT
- Interested in ML roles
- Experience with cloud infrastructure

Write the email.
```

### Tests
- Valid profile → returns email with subject + body
- Missing hobbies → gracefully fallback (use interests only)
- Parse error → return error or fallback email
- Email contains at least one hobby/interest mention

### Success Criteria
- [ ] `generate_email()` returns valid GeneratedEmailDTO
- [ ] Email mentions hobbies or interests from profile
- [ ] Email personalization works (not generic)
- [ ] All tests pass: `pytest tests/unit/test_email_generator.py`

---

## Step 7: API Endpoint (Generate Email)

### Objective
Expose email generation via REST API.

### Deliverables
- [ ] API route in `app/routers/recruiters.py`
- [ ] Tests

### Endpoint
```
POST /api/recruiters/{recruiter_id}/generate-email
Content-Type: application/json

Response (200):
{
  "subject_line": "Love the Alps—let's chat ML at TechCorp",
  "body": "Hey John!\n\nI noticed you love hiking..."
}

Response (404):
{
  "detail": "Recruiter not found"
}
```

### Implementation
- Route: POST /api/recruiters/{recruiter_id}/generate-email
- Fetch recruiter from DB
- Call EmailGeneratorService
- Return email DTO or error
- Optionally save to GeneratedEmail table (for tracking)

### Tests
- Valid recruiter → returns 200 + email
- Non-existent recruiter → returns 404
- Gemini error → returns 500 (or fallback)

### Success Criteria
- [ ] Endpoint accessible
- [ ] Returns personalized email
- [ ] All tests pass

---

## Step 8: React Frontend

### Objective
Build UI: URL input → profile display → email generation.

### Deliverables
- [ ] `frontend/src/App.jsx`
- [ ] `frontend/src/components/EnrichForm.jsx` (URL input)
- [ ] `frontend/src/components/ProfileView.jsx` (display enriched profile)
- [ ] `frontend/src/components/EmailGenerator.jsx` (show generated email)
- [ ] `frontend/src/hooks/useOutreach.js` (API calls)
- [ ] `frontend/src/store/outreachStore.js` (state management)
- [ ] TailwindCSS styling
- [ ] `frontend/.env`

### Pages/Components
1. **EnrichForm**: Input LinkedIn URL, button "Enrich Profile"
2. **ProfileView**: Display name, hobbies, interests, communication style (after enrichment)
3. **EmailGenerator**: Button "Generate Email", then show subject + body
4. **Loading state**: Spinner while Gemini processes
5. **Error handling**: Show friendly error messages

### State Management (Zustand)
```javascript
outreachStore = {
  recruiterUrl: "",
  setRecruiterUrl: (url) => {},
  profile: null,
  setProfile: (p) => {},
  email: null,
  setEmail: (e) => {},
  loading: false,
  setLoading: (l) => {},
  error: null,
  setError: (e) => {}
}
```

### API Calls (useOutreach hook)
```javascript
const {
  enrichProfile: (url) -> POST /api/recruiters/enrich,
  generateEmail: (recruiterId) -> POST /api/recruiters/{id}/generate-email
} = useOutreach()
```

### Flow
1. User enters LinkedIn URL, clicks "Enrich"
2. Frontend calls `POST /api/recruiters/enrich`
3. Show loading spinner while waiting (2-3s)
4. Display profile: hobbies, interests, communication style
5. User clicks "Generate Email"
6. Frontend calls `POST /api/recruiters/{id}/generate-email`
7. Show loading spinner (1-2s)
8. Display email subject + body
9. "Copy to Clipboard" button for email

### Tests
- Form validation (URL format check)
- API call success (mock fetch)
- API call failure (show error message)
- Copy-to-clipboard functionality
- Loading states render correctly

### Success Criteria
- [ ] Frontend runs: `npm run dev`
- [ ] Can input LinkedIn URL
- [ ] Can see enriched profile after enrichment
- [ ] Can generate email
- [ ] Can copy email to clipboard
- [ ] Error messages are user-friendly
- [ ] Mobile-responsive (TailwindCSS)

---

## Step 9: Testing (Unit + Integration + E2E)

### Objective
Ensure all components work together.

### Deliverables
- [ ] All unit tests: `pytest tests/unit/ -v`
- [ ] Integration tests: `pytest tests/integration/ -v`
- [ ] E2E test: `pytest tests/e2e/ -v`
- [ ] Coverage report: `pytest --cov=app`

### Test Suite Summary
- **Unit Tests** (isolated, mocked):
  - Scraper (mock Playwright)
  - Gemini agent (mock API)
  - Email generator (mock Gemini)
  - Schema validation
  
- **Integration Tests** (with test DB):
  - EnrichmentService (scraper + agent + DB)
  - API endpoints
  
- **E2E Tests** (full flow, live Gemini API):
  - LinkedIn URL → profile enriched → email generated
  - Error handling (invalid URL, timeout, etc.)

### Manual Testing
- Test on 10 real LinkedIn recruiters
- Verify hobbies/interests are accurate
- Check email personalization quality
- Ensure no broken links, typos

### Success Criteria
- [ ] All tests pass: `pytest . -v`
- [ ] Coverage >80%: `pytest --cov=app`
- [ ] Manual testing on 10 profiles works
- [ ] No error logs

---

## Step 10: Deployment (Out of Scope)

### Objective
Keep the MVP focused on the local/manual enrichment flow. Deployment can be added later.

---

## Timeline Estimate

| Step | Time | Status |
|------|------|--------|
| 1. Backend Setup | 1h | ⏳ TODO |
| 2. Playwright Scraper | 2h | ⏳ TODO |
| 3. Gemini Vision Agent | 3h | ⏳ TODO |
| 4. Enrichment Service | 2h | ⏳ TODO |
| 5. API Endpoint (Enrich) | 1h | ⏳ TODO |
| 6. Email Generator Service | 2h | ⏳ TODO |
| 7. API Endpoint (Email) | 1h | ⏳ TODO |
| 8. React Frontend | 4h | ⏳ TODO |
| 9. Testing | 3h | ⏳ TODO |
| 10. Deployment | 1h | ⏳ TODO |
| **Total** | **~20h** | |

**Expected completion**: 4-5 days (full-time) or 2-3 weeks (part-time)

---

## Notes & Gotchas

- **Playwright install**: Run `playwright install` after pip install
- **Gemini Vision latency**: 2-3s is normal; don't add aggressive timeouts
- **Free tier limits**: 1,500 calls/day per endpoint (plenty for MVP testing)
- **JSONB in PostgreSQL**: Use `json.loads()` when reading; SQLAlchemy doesn't auto-convert
- **Temp file cleanup**: Critical—don't leave screenshot files behind
- **Email sending**: MVP does NOT send emails; user copies + manually sends
- **Rate limiting**: LinkedIn doesn't explicitly block Playwright on public profiles, but respect robots.txt
- **CORS**: Enable in FastAPI for frontend calls
- **Error messages**: Keep user-friendly; no API key leaks in error logs

---

## Success Metrics

- ✅ MVP complete when user can: URL → Enriched Profile → Generated Email (copied to clipboard)
- ✅ All tests pass
- ✅ Deployment out of scope for MVP
- ✅ Works on 10 real recruiters with >70% confidence
- ✅ Total cost <$1 for 100 profiles
