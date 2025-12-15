# Recruiter Outreach Personalization Platform - Architecture

## Overview

**Purpose**: Automate personalized recruiter outreach by enriching LinkedIn profiles with Gemini 3 Vision, then generating tailored emails via LLM.

**Key Insight**: Gemini 3 Vision acts as an "intelligent scraper" that understands LinkedIn profile context (hobbies, interests, values) holistically, replacing brittle CSS selectors.

## High-Level Data Flow

```
LinkedIn Profile URL (user input)
         ↓
  [Playwright Scraper]
    - Screenshot profile
    - Fetch HTML content
         ↓
  [Gemini 3 Vision Agent]
    - Analyze screenshot + HTML
    - Extract: name, (attempt) email, current role/company, outreach hooks, portfolio links, communication style
         ↓
  [Structured JSON Output]
    {
      "name": "...",
      "email": "...",
      "current_role": "...",
      "current_company": "...",
      "unique_hooks": [...],
      "portfolio_links": [...],
      "communication_style": "...",
      "suggested_angles": [...]
    }
         ↓
  [Store in PostgreSQL (JSONB columns)]
         ↓
  [Email Generator Service]
    - Use enriched profile data
    - Call Gemini 3 Pro (text) with personalization context
         ↓
  [Generated Email]
    {
      "subject_line": "...",
      "body": "..."
    }
         ↓
  [Frontend Display]
    - Show recruiter profile + generated email
    - Allow manual editing
    - User manually sends via Gmail/LinkedIn
```

## Core Components

### 1. **Playwright Scraper Service** (`scraper/`)
- **Input**: LinkedIn profile URL
- **Output**: Screenshot (bytes), HTML content (text)
- **Async**: Yes (concurrent profile fetching)
- **Error Handling**: Timeout after 15s, retry once, log failures
- **Storage**: Temporary (disk), cleaned up after Gemini processing

**Key Functions**:
- `screenshot_linkedin(url)` → bytes (PNG screenshot of full profile)
- `fetch_html(url)` → str (raw HTML for context)
- `cleanup()` → None (delete temp files)

---

### 2. **Gemini Vision Agent** (`agents/`)
- **Input**: Screenshot (bytes), HTML (text), LinkedIn URL
- **Output**: Structured JSON (recruiter profile insights)
- **Model**: Gemini 3 Pro Vision
- **Cost**: ~$0.01 per call (included in free tier for MVP)
- **Latency**: 2-3 seconds per profile

**Responsibilities**:
- Build system prompt (few-shot examples, instructions)
- Build user prompt (enrich with HTML context)
- Call Gemini 3 API with multimodal input
- Parse JSON response
- Validate confidence score + completeness
- Return structured `LinkedInProfileInsights` object

**Failure Modes**:
- Parse error → log raw response, mark as unparseable
- Low confidence (<0.5) → flag for manual review
- API timeout → retry with backoff

---

### 3. **Enrichment Service** (`services/`)
- **Responsibility**: Orchestrate scraper + Gemini vision
- **Input**: LinkedIn URL
- **Output**: Saved `RecruiterProfile` in DB (JSONB columns)
- **Idempotency**: Check if URL already enriched; skip if recent (<7 days)

**Workflow**:
1. Validate LinkedIn URL format
2. Screenshot + fetch HTML (Playwright)
3. Call Gemini Vision Agent
4. Store in DB (recruiter, profile, enrichment metadata)
5. Return success + profile ID

---

### 4. **Email Generator Service** (`email/`)
- **Input**: RecruiterProfile (from DB with enriched data)
- **Output**: Generated email (subject + body)
- **Model**: Gemini 3 Pro (text-only)
- **Cost**: ~$0.0005 per email (free tier)
- **Latency**: 1-2 seconds

**Responsibilities**:
- Fetch recruiter profile + hobbies/interests from JSONB
- Build rich system prompt (few-shot examples, tone guide)
- Build user prompt (personalization variables)
- Call Gemini 3 API
- Parse response (Subject + Body)
- Return structured email object

---

### 5. **Database** (`postgres/`)

**Tables**:

```sql
-- Companies: seed data
companies (id, name, domain, industry, added_at)

-- Recruiters: scraped/manual entries
recruiters (
  id, 
  first_name, 
  last_name, 
  email, 
  company_id, 
  linkedin_url, 
  job_title,
  enriched BOOLEAN (tracks if we've processed this)
)

-- Enriched profiles (vision analysis output)
recruiter_profiles (
  id,
  recruiter_id UNIQUE,
  hobbies JSONB,               -- ["hiking", "photography"]
  professional_interests JSONB, -- ["AI", "startups"]
  inferred_values JSONB,       -- ["community", "transparency"]
  communication_style VARCHAR,  -- "casual", "formal", "technical"
  bio_summary TEXT,
  location VARCHAR,
  confidence_score FLOAT,
  enriched_at TIMESTAMP,
  raw_gemini_response TEXT      -- for debugging
)

-- Generated emails (manual tracking)
generated_emails (
  id,
  recruiter_id,
  subject_line TEXT,
  body TEXT,
  personalization_data JSONB,
  status VARCHAR,    -- "draft", "sent_manually", "archived"
  generated_at TIMESTAMP
)
```

---

## Technology Stack

| Layer | Tech | Why |
|-------|------|-----|
| **Backend** | FastAPI + asyncio | Fast MVP, native async for I/O (Gemini waits) |
| **Scraping** | Playwright | 40% faster than Selenium, native async |
| **Vision AI** | Gemini 3 Pro Vision | Multimodal, context-aware, free tier sufficient |
| **Email LLM** | Gemini 3 Pro (text) | Cheap, personalization expert |
| **Database** | PostgreSQL | JSONB for enriched data, full-text search (future) |
| **Frontend** | React + Vite | Fast, simple state management (Zustand) |
| **Deployment** | Out of scope (MVP) | Run locally; decide hosting later |

---

## Design Decisions

### 1. **Gemini Vision for Profile Analysis (not selectors)**
**Rationale**: 
- LinkedIn UI changes frequently → selectors break
- Gemini understands context holistically (hobbies across bio, posts, activity)
- Single API call vs. multiple sequential requests
- Cost effective (~$0.01/profile)

### 2. **Async-First Architecture**
**Rationale**:
- Gemini API calls are I/O-bound (2-3s wait per profile)
- Can fetch 50 profiles in parallel without blocking
- Playwright native async support
- FastAPI built for async workflows

### 3. **JSONB for Enriched Data**
**Rationale**:
- Hobbies/interests are arrays (schema-less)
- Query flexibility (filter by interest using @> operator)
- No ORM impedance mismatch
- Easy to version/update schema without migrations

### 4. **Manual Email Sending (MVP)**
**Rationale**:
- Eliminates deliverability concerns (Gmail filters, bounces)
- Avoids cold-email rate limiting
- User has full control (can edit before sending)
- Simplifies MVP scope (no SMTP/SendGrid setup)
- Can be added later as non-critical feature

### 5. **Separate Services (Scraper vs. Email)**
**Rationale**:
- Decoupled: can enrich profiles async, generate emails on-demand
- Reusable: email generator works for any enriched profile
- Testable: mock Gemini responses independently

---

## Error Handling & Resilience

### Scraper Layer
- **Timeout**: 15s per profile (Playwright)
- **Retry**: Once on timeout, then fail
- **Logging**: All failures logged with URL + error timestamp
- **Cleanup**: Temp files deleted even on failure

### Gemini Vision Layer
- **Parse Error**: Log raw response, mark profile as unparseable
- **Low Confidence**: Flag for manual review (confidence < 0.5)
- **API Timeout**: Retry with exponential backoff (1s, 2s, 4s)
- **Rate Limit**: Wait and retry (Gemini has generous free tier)

### Email Generation
- **Missing Data**: Gracefully fallback (skip hobbies if not found)
- **Token Limit**: Truncate profile bio if too long
- **API Error**: Return error to frontend, user can retry

---

## Free Tier Constraints

**Gemini 3 Pro Vision**:
- 1,500 requests/day (free tier)
- ~$0.01 per call (paid)
- For MVP: ~50 recruiters × 1 enrichment = 50 calls/day ✅

**Gemini 3 Pro (text)**:
- 1,500 requests/day
- ~$0.0005 per email
- For MVP: ~10 emails/day ✅

**PostgreSQL**:
- Run locally or use any hosted Postgres instance. Configure via `DATABASE_URL`.

**Frontend Hosting**:
- Vercel: Free tier, auto-deploy from Git ✅

**Backend Hosting**:
- Out of scope for MVP

---

## Future Enhancements (Post-MVP)

1. **Email Sending Integration**: SendGrid (tracking opens/replies)
2. **Scheduled Scraping Jobs**: APScheduler (hourly LinkedIn scrape)
3. **Duplicate Detection**: Hash emails, deduplicate by company
4. **Analytics**: Track email open rate, reply rate by template
5. **A/B Testing**: Test 2 email variants, track performance
6. **Multi-User**: Auth + per-user campaigns
7. **Webhook Tracking**: Email tracking pixel (SendGrid integration)

---

## Security & Privacy

- **No stored credentials**: User manually sends emails (no SMTP secrets)
- **LinkedIn ToS**: Playwright scraping is technical; respect robots.txt
- **API Keys**: Environment variables (never in code)
- **PII in Logs**: Sanitize email addresses in debug logs
- **Rate Limiting**: Respect Gemini free tier limits

---

## Testing Strategy

- **Unit**: Gemini response parsing (mock responses)
- **Integration**: End-to-end scraper → vision → email (live Gemini, test account)
- **E2E**: Frontend → API → DB → email generation
- **Manual**: Test on 10 real LinkedIn profiles before MVP release

---

## Deployment

Deployment is intentionally out of scope for the MVP. For now, run locally and point `DATABASE_URL` at a reachable Postgres instance.
