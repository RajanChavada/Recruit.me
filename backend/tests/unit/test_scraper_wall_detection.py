import pytest

from app.services.scraper import _is_likely_linkedin_wall


@pytest.mark.parametrize(
    "html, expected_wall",
    [
        ("<html><body>Sign in to LinkedIn</body></html>", True),
        ("<html><body>Security verification</body></html>", True),
        ("<html><body>captcha</body></html>", True),
        (
            "<html><body><div class='pv-top-card'>Profile</div><div>Experience</div></body></html>",
            False,
        ),
    ],
)
def test_is_likely_linkedin_wall(html: str, expected_wall: bool):
    is_wall, _reason = _is_likely_linkedin_wall(html)
    assert is_wall is expected_wall
