# Conventions & Standards

## Code Style & Naming

### Python
- **Style**: PEP 8 (enforced via `black` formatter)
- **Type Hints**: Required for all function signatures
- **Naming**:
  - Functions/variables: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private methods: `_leading_underscore`

**Example**:
```python
async def fetch_linkedin_profile(url: str) -> LinkedInProfileDTO:
    """Docstring explaining purpose, inputs, outputs."""
    pass

class LinkedInVisionAgent:
    """Multi-modal scraper using Gemini 3 Vision."""
    
    async def _extract_hobbies(self, text: str) -> list[str]:
        pass
```

### Database & ORM
- **Model Naming**: Singular (e.g., `Recruiter`, not `Recruiters`)
- **Column Naming**: `snake_case`
- **Timestamps**: All models have `created_at` and `updated_at`
- **IDs**: Primary key always `id` (auto-increment)
- **Foreign Keys**: `parent_id` (e.g., `company_id`)

**Example**:
```python
class Recruiter(Base):
    __tablename__ = "recruiters"
    
    id: int = Column(Integer, primary_key=True)
    first_name: str = Column(String(100), nullable=False)
    linkedin_url: str = Column(String(500), unique=True)
    company_id: int = Column(Integer, ForeignKey("companies.id"))
    enriched: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
```

---

## Error Handling

### Approach
1. **Custom Exceptions**: Define domain-specific exceptions in `exceptions.py`
2. **Logging**: All errors logged with context (URL, timestamp, stack trace)
3. **User-Facing**: Return JSON error responses (no raw tracebacks)
4. **Retry Logic**: Use exponential backoff for external APIs (Gemini, Playwright)

**Example**:
```python
# exceptions.py
class LinkedInScrapingError(Exception):
    """Raised when LinkedIn profile fetch fails."""
    pass

class GeminiVisionError(Exception):
    """Raised when Gemini Vision API call fails."""
    pass

# service.py
try:
    screenshot = await scraper.screenshot(url)
except asyncio.TimeoutError:
    logger.error(f"Timeout scraping {url}", exc_info=True)
    raise LinkedInScrapingError(f"Timeout after 15s: {url}")
```

### HTTP Responses
- **200 OK**: Successful request
- **400 Bad Request**: Invalid input (e.g., malformed LinkedIn URL)
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Unhandled exception (log this)

```python
@router.post("/enrich")
async def enrich_profile(url: str) -> dict:
    if not is_valid_linkedin_url(url):
        raise HTTPException(status_code=400, detail="Invalid LinkedIn URL")
    
    try:
        profile = await enrichment_service.enrich(url)
        return {"status": "ok", "profile": profile}
    except LinkedInScrapingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unhandled error")
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Logging

### Strategy
- **Level**:
  - `DEBUG`: Playwright navigation steps, API request/response bodies
  - `INFO`: Profile enrichment started/completed, email generation
  - `WARNING`: Retries, low confidence scores, missing data
  - `ERROR`: Exceptions, timeouts, parse failures

### Format
```
[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s
```

**Example**:
```python
import logging

logger = logging.getLogger(__name__)

async def enrich_profile(url: str):
    logger.info(f"Starting enrichment for {url}")
    try:
        screenshot = await scraper.screenshot(url)
        logger.debug(f"Screenshot captured: {screenshot.size} bytes")
        
        profile = await gemini_agent.analyze(screenshot)
        logger.info(f"Profile enriched: {profile.name}, confidence={profile.confidence_score}")
        
    except LinkedInScrapingError as e:
        logger.error(f"Failed to scrape {url}: {e}", exc_info=True)
        raise
```

---

## Testing Practices

### Unit Tests
- **Location**: `tests/unit/`
- **Pattern**: Test one function in isolation; mock external dependencies

```python
# tests/unit/test_gemini_agent.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_analyze_vision_response_parsing():
    """Test that Gemini response is parsed into correct JSON structure."""
    agent = LinkedInVisionAgent(api_key="test-key")
    
    # Mock Gemini API response
    mock_response = {
        "name": "John Doe",
        "hobbies": ["hiking"],
        "professional_interests": ["AI"]
    }
    
    with patch.object(agent, '_call_gemini', return_value=json.dumps(mock_response)):
        result = await agent.analyze(screenshot=b"...", html="...")
        
        assert result.name == "John Doe"
        assert "hiking" in result.hobbies
```

### Integration Tests
- **Location**: `tests/integration/`
- **Pattern**: Test service orchestration; use test database and real (or mocked) Gemini API

```python
# tests/integration/test_enrichment_service.py
@pytest.mark.asyncio
async def test_enrich_full_workflow():
    """Test scraper → vision → database save."""
    service = EnrichmentService(db=test_db, gemini_api_key="...")
    
    profile = await service.enrich("https://linkedin.com/in/test")
    
    assert profile.id is not None
    assert profile.hobbies is not None
```

### E2E Tests
- **Location**: `tests/e2e/`
- **Pattern**: Frontend → API → Database; minimal setup

```python
@pytest.mark.asyncio
async def test_enrich_endpoint_returns_email():
    """Test full flow: POST /enrich → GET /email."""
    client = TestClient(app)
    
    resp = client.post("/api/enrich", json={"linkedin_url": "..."})
    assert resp.status_code == 200
    
    recruiter_id = resp.json()["recruiter_id"]
    
    resp = client.post(f"/api/recruiters/{recruiter_id}/generate-email")
    assert resp.status_code == 200
    assert "subject_line" in resp.json()
```

---

## Performance Expectations

### Latency Targets
- **Screenshot + HTML fetch**: 3-5 seconds (Playwright timeout: 15s)
- **Gemini Vision analysis**: 2-3 seconds
- **Email generation**: 1-2 seconds
- **Database save**: <100ms
- **Total end-to-end**: ~6-10 seconds per recruiter (bottleneck: Gemini)

### Throughput Targets
- **Concurrent profiles**: 50+ (thanks to async)
- **Batch enrichment**: 50 recruiters in ~2-3 minutes (parallel)

### Memory Constraints
- **Screenshot in memory**: ~500KB per profile (cleaned up immediately)
- **Total RAM**: keep it small (<256MB is a good target for cheap runtimes)

---

## Security Constraints

### API Keys
- **Storage**: Environment variables only (never hardcoded)
- **Rotation**: Change if accidentally committed
- **Logging**: Never log API key values

```python
# ✅ Good
api_key = os.getenv("GEMINI_API_KEY")

# ❌ Bad
logger.debug(f"Using API key: {api_key}")
```

### LinkedIn ToS
- **Rate Limiting**: Max 5 profiles/minute per IP (to respect LinkedIn)
- **User-Agent**: Use realistic browser string
- **Robots.txt**: Check and respect (public profile pages are OK)

### Database
- **Connection String**: Store in `DATABASE_URL` env var
- **Credentials**: Never in code or logs
- **Backups**: handled by your chosen DB/runtime environment

---

## Documentation Standards

### Docstrings
- **Format**: Google-style docstrings
- **Required for**: All public functions, classes, modules

```python
async def enrich_from_linkedin(url: str) -> RecruiterProfileDTO:
    """
    Enrich a recruiter profile using LinkedIn and Gemini Vision.
    
    Args:
        url: Valid LinkedIn profile URL (e.g., https://linkedin.com/in/...)
    
    Returns:
        RecruiterProfileDTO with enriched hobbies, interests, values.
    
    Raises:
        LinkedInScrapingError: If profile cannot be fetched or timed out.
        GeminiVisionError: If Gemini API call fails.
    
    Example:
        profile = await enrich_from_linkedin("https://linkedin.com/in/john-doe")
        print(profile.hobbies)  # ["hiking", "photography"]
    """
    pass
```

### README Updates
- Update README.md when:
  - Adding new service or module
  - Changing environment variable names
  - Modifying API endpoints
  - Significant architectural change

---

## Git Workflow

### Branch Naming
- Feature: `feature/scraper-optimization`
- Bug fix: `fix/gemini-parsing-error`
- Docs: `docs/architecture-update`

### Commit Messages
```
[TYPE] Brief description (50 chars max)

Optional body explaining why/how (wrap at 72 chars).

Closes #123
```

**Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`

### PR Process
1. Create branch from `main`
2. Make changes + tests
3. Run formatter: `black .` + linter: `pylint`
4. Push and create PR with description
5. Self-review before requesting review
6. Merge after approval

---

## Dependency Management

### Python
- **Package manager**: `pip` + `requirements.txt`
- **Virtual environment**: `python -m venv venv`
- **Pinned versions**: For reproducibility

```bash
# requirements.txt
fastapi==0.109.0
playwright==1.40.0
google-generativeai==0.3.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
python-dotenv==1.0.0
```

### Frontend
- **Package manager**: `npm` + `package.json`
- **Node version**: 18+

---

## Monitoring & Observability (Future)

### Metrics to Track
- Gemini API success rate (target: >95%)
- Scraper timeout rate (target: <2%)
- Average enrichment latency
- Email generation success rate

### Alerting
- Gemini API rate limit hit → pause and retry
- DB connection pool exhausted → scale or optimize queries
- Disk space low → cleanup old temp files

### Logs Retention
- Keep last 30 days of logs
- Archive older logs (future: S3 or GCS)
