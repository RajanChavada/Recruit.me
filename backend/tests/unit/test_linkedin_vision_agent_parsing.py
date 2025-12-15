import pytest

import sys
import types

# Stub the optional google-generativeai dependency so unit tests don't require
# the external package just to exercise JSON parsing logic.
google_mod = types.ModuleType("google")
generativeai_mod = types.ModuleType("google.generativeai")
def _configure(*args, **kwargs):
    return None

class _GenerativeModel:
    def __init__(self, *args, **kwargs):
        pass

generativeai_mod.configure = _configure
generativeai_mod.GenerativeModel = _GenerativeModel
google_mod.generativeai = generativeai_mod
sys.modules.setdefault("google", google_mod)
sys.modules.setdefault("google.generativeai", generativeai_mod)

from app.agents.linkedin_vision_agent import LinkedInVisionAgent
from app.exceptions import GeminiVisionError


def test_parse_json_strips_code_fences():
    agent = LinkedInVisionAgent(api_key="test", model_name="test")
    raw = """```json
{\"name\":\"Rajan\",\"email\":null,\"email_explicit\":null,\"email_inferred\":\"rajan.chavada@google.com\",\"email_inference_notes\":\"Used first.last@google.com based on name + company\",\"current_role\":null,\"current_company\":\"Google\",\"unique_hooks\":[],\"portfolio_links\":[],\"communication_style\":null,\"suggested_angles\":[]}
```"""
    parsed = agent._parse_json(raw)
    assert parsed["name"] == "Rajan"
    assert parsed["email_inferred"] == "rajan.chavada@google.com"


def test_parse_json_raises_on_invalid_json():
    agent = LinkedInVisionAgent(api_key="test", model_name="test")
    with pytest.raises(GeminiVisionError):
        agent._parse_json("not json")
