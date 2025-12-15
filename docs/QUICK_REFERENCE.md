# Quick Reference Card

## Files You Just Created (For Your Project)

```
docs/
├── ARCHITECTURE.md          → System design + tech stack
├── CONVENTIONS.md           → Code style + error handling
├── WORKFLOWS.md             → How to use LLM for development
├── MVP_BRIEF.md             → Requirements + scope
├── MVP_PLAN.md              → 10-step implementation plan
├── GETTING_STARTED.md       → Setup + deployment
└── README_SCAFFOLDING.md    → This summary (you're reading it!)
```

## What Each File Does

| File | Purpose | Read When | Time |
|------|---------|-----------|------|
| **ARCHITECTURE.md** | Understand the system design | Before coding anything | 5m |
| **CONVENTIONS.md** | Know code standards | When writing code | Ref. |
| **WORKFLOWS.md** | Learn LLM dev workflow | Before chatting with LLM | 10m |
| **MVP_BRIEF.md** | Understand requirements | At project start | 5m |
| **MVP_PLAN.md** | Follow step-by-step plan | Each coding session | 10m |
| **GETTING_STARTED.md** | Setup & deploy | When building/deploying | 5m |

---

## The Project in 60 Seconds

**Goal**: Build a LinkedIn recruiter enrichment tool

**Flow**:
1. User inputs: LinkedIn URL
2. Backend: Screenshot + analyze with Gemini 3 Vision
3. Backend: Extract hobbies, interests, values (JSON)
4. Frontend: Display enriched profile
5. User clicks: "Generate email"
6. Backend: Call Gemini 3 Pro with personalization
7. Frontend: Show generated email
8. User: Copy email, send manually

**Tech Stack**:
- Backend: FastAPI + Python + PostgreSQL
- Frontend: React + Vite + TailwindCSS
- AI: Gemini 3 Vision + Gemini 3 Pro
- Scraping: Playwright
- Hosting: out of scope for MVP (local dev only)

**Cost**: $0 (free tier for MVP)

**Time**: ~20 hours (4-5 days full-time)

---

## Your Development Workflow

### Before You Build
- [ ] Read ARCHITECTURE.md (understand design)
- [ ] Read MVP_PLAN.md (understand steps)
- [ ] Read CONVENTIONS.md (know standards)
- [ ] Test Gemini prompt in AI Studio (refine prompt)

### When You Build (Each Component)
```
1. Read the step in MVP_PLAN.md
2. Chat with LLM:
   - Reference: ARCHITECTURE.md + CONVENTIONS.md
   - Ask: "Help me build Step X"
   - LLM generates code
3. Test locally
4. Iterate if needed
5. Move to next step
```

### When You Deploy
```
git push origin main
 Deployment is out of scope for the MVP
```

---

## One-Page Prompts

### Prompt for Backend Setup (Step 1)
```
I'm building a LinkedIn recruiter enrichment tool using FastAPI.

Architecture:
#file:ARCHITECTURE.md

Plan (Step 1):
#file:MVP_PLAN.md

Standards:
#file:CONVENTIONS.md

Generate:
1. backend/requirements.txt
2. backend/app/main.py
3. backend/app/config.py
4. backend/app/models.py
5. backend/app/schemas.py
6. (no docker-compose for MVP)
7. backend/.env.example

Include type hints, docstrings, error handling per CONVENTIONS.md.
```

### Prompt for Scraper Service (Step 2)
```
I'm on Step 2: Playwright Scraper.

Details:
#file:MVP_PLAN.md (Step 2 section)

Standards:
#file:CONVENTIONS.md

Create:
1. backend/app/services/scraper.py
   - LinkedInScraper class
   - async screenshot_linkedin(url) → bytes
   - async fetch_html(url) → str
   - Error handling + logging
   
2. tests/unit/test_scraper.py
   - Mock Playwright
   - Test timeout
   - Test cleanup

Include type hints + docstrings.
```

### Prompt for Debugging
```
I'm getting this error:

[paste full error]

Code:
#file:backend/app/services/[service].py

What's wrong and how do I fix it?
```

---

## Gemini Vision Prompt (Use in AI Studio)

Copy this into https://aistudio.google.com when using Gemini 3 Pro Vision:

```
You are an expert LinkedIn profile analyst.

Analyze this LinkedIn profile screenshot and extract a *single JSON object* in the exact schema below.

Rules:
- Output **JSON only** (no markdown/code fences, no commentary).
- If a field is unknown, return null (for strings) or [] (for arrays).
- For email, only output an email if it is explicitly visible in the screenshot/HTML. Do not guess.

Output JSON schema:
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

Field guidance:
- unique_hooks: 3-6 concise, specific hooks that could be used in outreach (awards, side projects, speaking, hiring initiatives, notable posts, etc.)
- portfolio_links: personal site / portfolio / GitHub / blog links mentioned on the profile
- suggested_angles: choose human-readable tags such as: achievement_impressed, recruiter_fit, peer_network
```

---

## Timeline at a Glance

```
DAY 6 (4h)
 React frontend (4h)
    Deployment (out of scope)
DAY 7 (2h)
 E2E testing (1h)

DAY 4 (3h)
├─ Enrichment service (1h)
├─ API endpoints (1h)
└─ Tests (1h)

DAY 5 (4h)
├─ Email generator (2h)
├─ API endpoint (1h)
└─ Tests (1h)

DAY 6 (4h)
├─ React frontend (4h)

DAY 7 (2h)
├─ E2E testing (1h)
└─ Deployment (out of scope)

TOTAL: ~20 hours (1 week full-time)
```

---

## Success Checklist

- [ ] Can input LinkedIn URL in frontend
- [ ] Backend scrapes and enriches profile
- [ ] Frontend shows: name, hobbies, interests, style
- [ ] Can generate personalized email
- [ ] Email mentions hobbies/interests from profile
- [ ] Works on 10 different recruiters with >70% accuracy
- [ ] All tests pass
- [ ] Deployment out of scope
- [ ] Cost: $0

---

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| "No module named playwright" | Run: `playwright install` after pip install |
| Gemini API returns 429 (rate limit) | Free tier: 1,500 calls/day—check usage |
| Screenshot is blank | LinkedIn profile needs to load; increase timeout to 20s |
| Email is generic (not personalized) | Check Gemini prompt; refine in AI Studio first |
| Temp files not deleted | Make sure cleanup() is called even on error (use try/finally) |
| CORS errors in frontend | Enable CORS in FastAPI main.py |
| PostgreSQL connection fails | Check DATABASE_URL in backend/.env and that Postgres is reachable |

---

## LLM Chat Structure (Best Practices)

### ✅ Good: Focused Chats
- **Chat 1**: Planning (architecture + data model)
- **Chat 2**: Backend setup (FastAPI + models)
- **Chat 3**: Scraper service (Playwright)
- **Chat 4**: Gemini vision agent (multimodal AI)
- **Chat 5**: Enrichment + API (orchestration)
- **Chat 6**: Email generation (Gemini text)
- **Chat 7**: Frontend (React)

Each chat: 15-45 minutes, focused on ONE component

### ❌ Bad: Giant Chat
- Ask for "entire project" in one chat
- Add features as you go
- Chat runs for 2-3 hours
- Context bloats, LLM gets confused
- Take 5x longer

---

## Files to Reference in LLM Chats

**Always mention at least 2 of these**:

1. `#file:ARCHITECTURE.md` — High-level design
2. `#file:MVP_PLAN.md` — Current step details
3. `#file:CONVENTIONS.md` — Code standards
4. `#file:app/main.py` — Current code state
5. `#file:tests/unit/test_X.py` — Test examples

Example:
```
I'm building Step 3: Gemini Vision Agent.

#file:MVP_PLAN.md (Step 3 section)
#file:CONVENTIONS.md (error handling)

Create: backend/app/agents/linkedin_vision_agent.py
```

---

## Deployment Commands

### Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev


PostgreSQL: run it however you prefer and set `DATABASE_URL`.
```

Deployment is intentionally out of scope for MVP.

---

## Questions?

**"How do I..."**

| Question | Answer |
|----------|--------|
| ...use this with an LLM? | Read WORKFLOWS.md |
| ...follow the implementation plan? | Read MVP_PLAN.md |
| ...know the code standards? | Read CONVENTIONS.md |
| ...set up locally? | Read GETTING_STARTED.md |
| ...deploy? | Read GETTING_STARTED.md → Deployment |
| ...understand the architecture? | Read ARCHITECTURE.md |

---

## You're Ready!

Everything is documented. Next step:

1. **Read** ARCHITECTURE.md + MVP_BRIEF.md (15m)
2. **Test** Gemini prompt in AI Studio (1h)
3. **Chat** with LLM: "Help me with Step 1"
4. **Build** following MVP_PLAN.md (20h over 4-5 days)
5. (Optional) Add deployment later

Go build! 🚀
