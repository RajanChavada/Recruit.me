import pytest

from app.exceptions import InvalidLinkedInUrlError
from app.utils import validate_linkedin_profile_url


def test_validate_linkedin_profile_url_accepts_profile_url():
    url = "https://www.linkedin.com/in/john-doe-123/"
    assert validate_linkedin_profile_url(url) == url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not-a-url",
        "https://linkedin.com/company/foo",
        "https://linkedin.com/jobs/view/123",
        "https://example.com/in/john",
    ],
)
def test_validate_linkedin_profile_url_rejects_invalid(url: str):
    with pytest.raises(InvalidLinkedInUrlError):
        validate_linkedin_profile_url(url)
