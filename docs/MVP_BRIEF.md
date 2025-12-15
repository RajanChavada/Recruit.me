# MVP: LinkedIn Profile Enrichment + Personalized Email Generation

## Brief

### Goal
Build a web app that takes a LinkedIn recruiter profile URL, enriches it with insights (hobbies, interests, values) using Gemini 3 Vision, then generates a personalized outreach email using those insights.

### User Flow
1. User inputs: LinkedIn profile URL (e.g., https://linkedin.com/in/john-doe)
2. Backend scrapes: Screenshot + HTML via Playwright
3. Gemini 3 Vision analyzes: Extracts hobbies, interests, communication style
4. Backend stores: Profile insights in PostgreSQL (JSONB)
5. Frontend displays: Enriched profile summary (hobbies, interests, values)
6. User requests: "Generate email"
7. Backend calls: Gemini 3 Pro (text) with personalization context
8. Frontend shows: Generated email (subject + body)
9. User action: Copy email, manually send via Gmail/LinkedIn (no integration)

### Scope (MVP Only)
- ✅ LinkedIn scraping (Playwright)
- ✅ Gemini 3 Vision enrichment
- ✅ Personalized email generation (Gemini 3 Pro)
- ✅ PostgreSQL storage (JSONB enrichment data)
- ✅ React frontend (URL input → profile view → email generation)
- ❌ Email sending integration (user sends manually)
- ❌ Scheduled scraping jobs (manual trigger for MVP)
- ❌ Authentication (single-user for MVP)
- ❌ Campaign tracking (future)
- ❌ Duplicate detection (future)

### Success Criteria
- [ ] User can input LinkedIn URL → see enriched profile (hobbies, interests, values)
- [ ] Profile enrichment works for 10 different real recruiters with >70% confidence
- [ ] Generated emails feel personalized (mention hobbies/interests from profile)
- [ ] No errors on happy path (valid LinkedIn URL)
- [ ] Graceful error handling (invalid URL, scraping timeout, Gemini parse failure)
- [ ] Runs locally (deployment out of scope for MVP)
- [ ] Total E2E time: <15 seconds per profile
- [ ] Costs <$1 to process 100 recruiters (free tier Gemini usage)

### Data Inputs
- LinkedIn URL (user-provided)

### Data Outputs
```json
{
  "recruiter_name": "John Doe",
  "hobbies": ["hiking", "photography"],
  "professional_interests": ["AI", "startups"],
  "inferred_values": ["community-driven", "transparency"],
  "communication_style": "casual",
  "bio_summary": "...",
  "location": "San Francisco, CA",
  "generated_email": {
    "subject_line": "Love the Alps—let's chat ML at [Company]",
    "body": "Hey John!\n\nI noticed you love hiking—the Alps are incredible! I've been exploring some of the same trails...\n\nI'm also passionate about AI and building at scale. Saw that [Company] is doing some exciting work in this space..."
  }
}
```

### Technical Constraints
- **No cost**: Free tier Gemini API (1,500 calls/day per endpoint)
- **Fast**: Must complete <15s per profile (Gemini is 2-3s bottleneck)
- **Async**: Playwright + Gemini calls must be non-blocking
- **Stateless**: Safe to run locally; no background schedulers in MVP
- **DB**: PostgreSQL with JSONB (via `DATABASE_URL`)
- **No email sending**: User copies email and sends manually
- **Manual trigger only**: No cron jobs (can add later)

### Out of Scope (Post-MVP)
- Bulk scraping (100+ recruiters)
- Scheduled jobs (APScheduler)
- Email sending (SendGrid)
- Authentication (multi-user campaigns)
- Analytics (open rate, reply rate)
- A/B testing email variants
- Webhook tracking

### Acceptance Tests
1. **Input valid LinkedIn URL** → Returns enriched profile with all fields populated
2. **Input invalid URL** → Returns 400 Bad Request with clear error message
3. **Scraper timeout** → Returns 400 with message "Could not load LinkedIn profile"
4. **Gemini parse fails** → Returns 400 with message "Could not analyze profile"
5. **Generate email** → Email mentions at least one hobby/interest from profile
6. **Frontend displays** → Shows recruiter name, hobbies, interests, communication style
7. **Email copy** → User can copy generated email to clipboard

---

## Architecture Diagram (for this feature)

```
┌─────────────────────────────────────────────────────────────┐
│                    React Frontend                            │
│  Input: LinkedIn URL → [Enrich] → Display Profile → Email   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ↓ POST /api/recruiters/enrich
         ┌─────────────────────────────────────────┐
         │    FastAPI Backend (Python)             │
         │  ┌─────────────────────────────────────┐
         │  │ 1. Playwright Scraper               │
         │  │    - screenshot_linkedin(url)       │
         │  │    - fetch_html(url)                │
         │  └────────────┬────────────────────────┘
         │               ↓
         │  ┌─────────────────────────────────────┐
         │  │ 2. Gemini 3 Vision Agent            │
         │  │    - analyze(screenshot, html)      │
         │  │    - Returns: LinkedInProfileDTO    │
         │  └────────────┬────────────────────────┘
         │               ↓
         │  ┌─────────────────────────────────────┐
         │  │ 3. Database (PostgreSQL)            │
         │  │    - Save enriched profile (JSONB)  │
         │  └─────────────────────────────────────┘
         │
         │  ┌─────────────────────────────────────┐
         │  │ 4. Email Generator Service          │
         │  │    - Fetch profile from DB          │
         │  │    - Call Gemini 3 Pro (text)       │
         │  │    - Return: email subject + body   │
         │  └─────────────────────────────────────┘
         └──────────────────────────────────────────┘

Total E2E time: ~6-10s (bottleneck: Gemini Vision 2-3s)
```

---

## Implementation Phases

### Phase 1: Backend Setup (Day 1)
- [ ] FastAPI project scaffold
- [ ] PostgreSQL models (Recruiter, RecruiterProfile)
- [ ] Playwright scraper service (screenshot + HTML)
- [ ] Unit tests for scraper (mock Playwright)

### Phase 2: Gemini Vision Integration (Day 2)
- [ ] Gemini Vision Agent class
- [ ] Test prompt on 3 real LinkedIn profiles (AI Studio)
- [ ] JSON parsing + validation
- [ ] Enrichment service (orchestrates scraper + agent)
- [ ] REST endpoint: POST /api/recruiters/enrich
- [ ] Unit + integration tests

### Phase 3: Email Generation (Day 3)
- [ ] Email generator service (takes enriched profile)
- [ ] Gemini 3 Pro text prompt (few-shot examples)
- [ ] REST endpoint: POST /api/recruiters/{id}/generate-email
- [ ] Tests (mock Gemini response)

### Phase 4: Frontend (Day 4)
- [ ] React component: URL input form
- [ ] Fetch /api/recruiters/enrich + display profile
- [ ] Show hobbies, interests, communication style
- [ ] Fetch /api/recruiters/{id}/generate-email + display
- [ ] Copy-to-clipboard for email
- [ ] Error handling (show friendly messages)

### Phase 5: Deployment & Polish (Day 5)
- [ ] Deployment (out of scope)
- [ ] Test on 10 real LinkedIn profiles
- [ ] Fix any edge cases
- [ ] Write README

---

## Testing Strategy for MVP

### Unit Tests
- Gemini response parsing (mock response)
- Scraper timeout handling
- Email template formatting

### Integration Tests
- Scraper → Gemini → Database (use test DB)
- Email generator uses DB profile (no mocks)

### E2E Tests
- Full flow: LinkedIn URL → profile → email (test DB, real Gemini API)
- Error cases: invalid URL, timeout, parse failure

### Manual Tests
- Test on 10 real recruiters from companies you're applying to
- Verify hobbies/interests are accurate
- Verify email personalization is good

---

## Free Tier Costs

| Service | Free Tier | MVP Usage | Cost |
|---------|-----------|-----------|------|
| Gemini 3 Vision | 1,500 calls/day | 50 profiles/day | FREE ✅ |
| Gemini 3 Pro | 1,500 calls/day | 10 emails/day | FREE ✅ |
| PostgreSQL | Depends on provider | <100MB | FREE/cheap ✅ |
| FastAPI | Local dev/runtime | Runs on-demand | FREE ✅ |
| React (Vercel) | Free tier | Static hosting | FREE ✅ |
| **Total** | | | **$0/month** ✅ |

---

## Known Gotchas (for implementation chats)

1. **Playwright install**: `playwright install` required after `pip install playwright`
2. **LinkedIn ToS**: Public profile scraping is OK; be respectful of rate limits
3. **Gemini Vision latency**: 2-3s is normal; don't add more timeouts
4. **JSONB parsing**: Use `json.loads()` when reading from DB; SQLAlchemy doesn't auto-parse
5. **Temp file cleanup**: Always delete screenshots after Gemini processes them
6. **CSS selectors**: DON'T use selectors on LinkedIn; let Gemini handle it
