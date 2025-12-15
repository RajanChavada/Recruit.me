# Workflows & LLM-Assisted Development

## How to Use This Project with an AI Assistant

### Core Principle
This project is designed to be developed collaboratively with an LLM (Claude, Copilot, etc.). These docs act as your project's "system prompt."

---

## Pre-Chat Checklist

Before starting a chat with an LLM about this project:

- [ ] Read the relevant section of `ARCHITECTURE.md` (which component am I building?)
- [ ] Check `CONVENTIONS.md` for style/error handling expectations
- [ ] Have the feature brief (`docs/features/<name>/brief.md`) ready to reference
- [ ] Mention specific file paths (#file:path/to/file) so the LLM loads that context

---

## Feature Development Workflow

### Phase 1: Planning (Synchronous with LLM)

**Prompt the LLM with**:
```
I want to implement [Feature Name]. Here's the brief:

#file:docs/features/[feature-name]/brief.md

Based on ARCHITECTURE.md and CONVENTIONS.md:
1. Where does this fit in the architecture?
2. What new tables/models do I need?
3. What's the step-by-step implementation plan?

Output as: docs/features/[feature-name]/plan.md
```

**LLM creates** `plan.md` with:
- Step-by-step implementation plan
- Data model changes
- API endpoints needed
- Test cases to write

**You review** plan.md, iterate until satisfied.

---

### Phase 2: Implementation (Iterative)

**Prompt 1: Generate Code**
```
Now implement Step 1 from the plan.

#file:docs/features/[feature-name]/plan.md
#file:app/models.py (current state)
#file:app/services/[service].py (where to add code)

Requirements:
- Follow CONVENTIONS.md for naming/error handling
- Type hints required
- Add docstrings
- Include tests

Generate the code for Step 1.
```

**LLM generates** code scaffolds/full implementations.

**You review**, edit, test locally.

**Prompt 2: Refine**
```
I got an error when testing:

[paste error traceback]

The issue is in [service/file]. Here's what I tried:

[paste code]

What's wrong and how do I fix it?
```

**LLM debugs** and explains.

Repeat until component works.

---

### Phase 3: Integration (End-to-End Test)

**Prompt**:
```
Feature implementation is done (Step 1-3 complete). Now let's test the full flow.

#file:docs/features/[feature-name]/plan.md
#file:app/main.py (main app)

Write an E2E test that:
1. [From the plan's acceptance criteria]
2. [From the plan's acceptance criteria]

Include both happy path and error cases.
```

**LLM generates** `tests/e2e/test_[feature].py`

**You run**:
```bash
pytest tests/e2e/test_[feature].py -v
```

---

### Phase 4: Documentation & Closeout

**After passing E2E test**:

1. Update `plan.md` → Mark steps as ✅ Done
2. Create `notes.md` with:
   - What went well
   - What was tricky (gotchas for next dev)
   - Decisions made (why did we do X instead of Y?)
3. Update main `README.md` if user-facing feature

---

## Common Workflows

### "Build a new service"

```
1. Read ARCHITECTURE.md → understand where it fits
2. Create `app/services/[service_name].py` file
3. Ask LLM to scaffold the class (init, key methods)
4. Add methods one-by-one with LLM
5. Write tests alongside
6. Integrate into `app/main.py`
```

### "Debug a failing test"

```
1. Run test, capture full error
2. Paste error + test code + service code into chat
3. Ask: "Why is [assertion] failing?" + "How do I fix it?"
4. Implement fix
5. Re-run test
```

### "Optimize performance"

```
1. Identify bottleneck (e.g., "Gemini calls are slow")
2. Ask LLM: "How can I parallelize [component]?"
3. LLM suggests async/concurrency patterns
4. Implement with LLM guidance
5. Benchmark before/after
```

### "Add new API endpoint"

```
1. Read ARCHITECTURE.md for endpoint conventions
2. Ask LLM: "Add endpoint POST /api/[resource]/[action]"
3. LLM generates router + handler + request/response models
4. Wire into main app
5. Test with curl or Postman
```

---

## Chat Structure (to avoid context bloat)

### ❌ Bad: One giant chat
- Start with "build the whole project"
- Keep adding features
- Chat context grows, LLM gets confused
- Takes 1-2 hours in one chat

### ✅ Good: Separate chats per concern
- **Chat 1**: Planning (architecture, schema, high-level plan)
- **Chat 2**: Scraper service (implement & test)
- **Chat 3**: Gemini vision agent (implement & test)
- **Chat 4**: API endpoints (implement & test)
- **Chat 5**: Frontend integration (if building UI)

Each chat: 15-45 minutes, focused, easy to iterate.

**In each chat, start with**:
```
Continuing from: [Previous chat summary]

Working on: [Feature name]

Relevant docs:
#file:ARCHITECTURE.md
#file:CONVENTIONS.md
#file:docs/features/[name]/brief.md
#file:docs/features/[name]/plan.md
```

---

## Files to Always Reference

### Before ANY coding chat
- `ARCHITECTURE.md` (high-level design)
- `CONVENTIONS.md` (code style, error handling)

### Before implementing a feature
- `docs/features/[feature]/brief.md` (requirements)
- `docs/features/[feature]/plan.md` (step-by-step)
- `docs/features/[feature]/notes.md` (gotchas from previous dev)

### When debugging
- Stack trace + relevant file (use #file: mention)
- Error handling section of CONVENTIONS.md
- Relevant service file

---

## When to Ask the LLM vs. Google

### Ask LLM:
- Architecture/design questions
- Code generation + refactoring
- Test writing
- Debugging errors
- Integration patterns

### Google/Docs:
- API reference (Gemini, Playwright, FastAPI)
- Library version-specific issues
- Performance tuning for specific libraries
- Environment setup (if stuck)

---

## Prompt Templates You Can Reuse

### Template 1: Generate a Service
```
Create a new service class called [ServiceName] in app/services/[service_name].py

Requirements:
- Handles: [brief description]
- Inputs: [type]
- Outputs: [type]
- Key methods: [list]

Use async/await, add type hints, and include docstrings.
Follow CONVENTIONS.md for error handling.
Include [N] unit tests in tests/unit/test_[service_name].py.
```

### Template 2: Integrate into API
```
Add a new API endpoint to app/main.py:

Route: [POST/GET] /api/[resource]/[action]
Request: { [fields] }
Response: { [fields] }
Business logic: [description]

Return appropriate HTTP codes (200, 400, 500).
Follow CONVENTIONS.md for error responses.
```

### Template 3: Debug
```
Getting this error when I [run/test X]:

[paste full stack trace]

The test code is:
[paste test]

The service code is:
#file:app/services/[service].py

What's wrong and how do I fix it?
```

### Template 4: Write Tests
```
Write comprehensive tests for [Component] in tests/[unit|integration]/test_[component].py

Test cases:
1. [happy path description]
2. [edge case]
3. [error case]

Mock dependencies as needed. Follow pytest patterns from CONVENTIONS.md.
```

---

## Checkpoints Before Each Phase

### Before Phase 2 (Implementation)
- [ ] `plan.md` is clear and approved
- [ ] You understand each step
- [ ] You know what tests to write

### Before Phase 3 (Integration)
- [ ] All unit tests pass
- [ ] All code follows CONVENTIONS.md
- [ ] All docstrings are complete

### Before Phase 4 (Documentation)
- [ ] E2E test passes
- [ ] Feature works end-to-end
- [ ] No lingering warnings in logs

### Before Merging to `main`
- [ ] All tests pass (`pytest .`)
- [ ] Code formatted (`black .`)
- [ ] Linted (`pylint app/`)
- [ ] README.md updated (if user-facing)
- [ ] `plan.md` and `notes.md` updated

---

## Example: Full Feature Development Cycle

### Feature: LinkedIn Profile Enrichment via Gemini Vision

**Chat 1: Planning**
```
Read #file:docs/features/linkedin-vision-enrichment/brief.md
Read #file:ARCHITECTURE.md

What's the implementation plan? Output as plan.md.
```
→ LLM creates detailed step-by-step plan

**Chat 2: Scraper Service**
```
Continuing from Chat 1, let's build the scraper.

Implement Step 1 from plan:
#file:docs/features/linkedin-vision-enrichment/plan.md

Create app/services/scraper.py with:
- screenshot_linkedin(url)
- fetch_html(url)
- Full docstrings + type hints + error handling
- Include unit tests
```
→ LLM generates scraper service + tests
→ You test locally: `pytest tests/unit/test_scraper.py`

**Chat 3: Gemini Vision Agent**
```
Now implement the Gemini vision component (Step 2).

Create app/agents/linkedin_vision_agent.py with:
- analyze_profile(screenshot, html)
- Parse JSON response into LinkedInProfileDTO
- Error handling for parse failures
- Full tests

#file:CONVENTIONS.md for error handling style
```
→ LLM generates agent + tests
→ You test: `pytest tests/unit/test_linkedin_vision_agent.py`

**Chat 4: Enrichment Service + API**
```
Wire it together (Step 3 + 4).

Create app/services/enrichment_service.py that:
- Calls scraper → Gemini agent → DB save
- Handles failures gracefully
- Returns LinkedInProfileDTO

Add API endpoint in app/main.py:
POST /api/recruiters/enrich { linkedin_url }

Full tests + docstrings.
```
→ LLM generates service + endpoint + tests
→ You test end-to-end

**Chat 5: Frontend (optional)**
```
Create React component to call this API.

Component should:
- Input: LinkedIn URL
- Display: Extracted profile (hobbies, interests, etc.)
- Button: Generate email

Use Zustand for state, TailwindCSS for styling.
```
→ LLM generates React component
→ You wire into main app

---

## Anti-Patterns to Avoid

### ❌ Don't
- Ask for "the entire project" in one chat
- Forget to provide file context (#file:...)
- Skip reading plan.md before coding
- Ignore CONVENTIONS.md (then have to refactor)
- Leave old chats running (start fresh chats per feature)

### ✅ Do
- Break work into focused features
- Reference specific files in prompts
- Read docs before starting
- Follow conventions from the start
- Use separate chats for separate features
