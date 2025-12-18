from app.services.email_inference import generate_email_candidates


def test_generate_email_candidates_first_last_domain():
    cands = generate_email_candidates(name="Rajan Chavada", company="Borealis AI")
    emails = [c.email for c in cands]
    assert "rajan.chavada@borealisai.com" in emails
    assert emails[0] == "rajan.chavada@borealisai.com"


def test_generate_email_candidates_domain_passthrough():
    cands = generate_email_candidates(name="Jane Doe", company="example.com")
    emails = [c.email for c in cands]
    assert "jane.doe@example.com" in emails


def test_generate_email_candidates_rbc_mapping():
    cands = generate_email_candidates(name="Katie McBride", company="RBC")
    emails = [c.email for c in cands]
    assert "katie.mcbride@rbc.com" in emails
