import pytest

import sys
import types

# Stub the optional Google SDK dependencies so unit tests don't require
# external packages just to exercise JSON parsing logic.
google_mod = types.ModuleType("google")
generativeai_mod = types.ModuleType("google.generativeai")
genai_mod = types.ModuleType("google.genai")
genai_types_mod = types.ModuleType("google.genai.types")
genai_errors_mod = types.ModuleType("google.genai.errors")
def _configure(*args, **kwargs):
    return None

class _GenerativeModel:
    def __init__(self, *args, **kwargs):
        pass

generativeai_mod.configure = _configure
generativeai_mod.GenerativeModel = _GenerativeModel
google_mod.generativeai = generativeai_mod

# Minimal stubs used by LinkedInVisionAgent.__init__ and _call_model.
class _Client:
    def __init__(self, *args, **kwargs):
        self.models = types.SimpleNamespace(generate_content=lambda *a, **k: types.SimpleNamespace(text="{}"))


class _GenerateContentConfig:
    def __init__(self, *args, **kwargs):
        pass


class _Part:
    @staticmethod
    def from_text(text: str):
        return {"text": text}

    @staticmethod
    def from_bytes(*, data: bytes, mime_type: str):
        return {"data": data, "mime_type": mime_type}


class _Content:
    def __init__(self, *args, **kwargs):
        pass


genai_mod.Client = _Client
genai_types_mod.GenerateContentConfig = _GenerateContentConfig
genai_types_mod.Part = _Part
genai_types_mod.Content = _Content


class _APIError(Exception):
    pass


genai_errors_mod.APIError = _APIError
genai_mod.types = genai_types_mod
google_mod.genai = genai_mod
sys.modules.setdefault("google", google_mod)
sys.modules.setdefault("google.generativeai", generativeai_mod)
sys.modules.setdefault("google.genai", genai_mod)
sys.modules.setdefault("google.genai.types", genai_types_mod)
sys.modules.setdefault("google.genai.errors", genai_errors_mod)

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
