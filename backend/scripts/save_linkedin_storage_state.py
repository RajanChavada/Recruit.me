"""One-time LinkedIn login helper.

This script opens a headed Playwright browser so you can log into LinkedIn manually,
then saves Playwright storage state (cookies + localStorage) to disk.

After you capture the storage state, configure the backend to reuse it:
- LINKEDIN_STORAGE_STATE_PATH=.secrets/linkedin_storage_state.json

Notes:
- The storage state contains authentication cookies. Treat it like a password.
- Do NOT commit it to git.
- Some LinkedIn security measures may still block automation. If so, re-run this
  script and complete any additional verification steps in the browser window.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    parser = argparse.ArgumentParser(description="Save a logged-in LinkedIn Playwright storage state")
    parser.add_argument(
        "--output",
        default=os.environ.get("LINKEDIN_STORAGE_STATE_PATH", ".secrets/linkedin_storage_state.json"),
        help="Where to write the storage_state.json (default: %(default)s)",
    )
    parser.add_argument(
        "--login-url",
        default=os.environ.get("LINKEDIN_LOGIN_URL", "https://www.linkedin.com/login"),
        help="LinkedIn login URL to open (default: %(default)s)",
    )
    parser.add_argument(
        "--profile-url",
        default=os.environ.get("LINKEDIN_PROFILE_URL"),
        help="Optional: open a profile URL after login to verify session.",
    )
    args = parser.parse_args()

    output_path = Path(args.output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n=== LinkedIn login (one-time) ===")
    print(f"Login URL:  {args.login_url}")
    print(f"Output:     {output_path}")
    print("\nSteps:")
    print("  1) A Chromium window will open.")
    print("  2) Log in manually (and complete any MFA/verification).")
    print("  3) When you're fully logged in, return to this terminal and press ENTER.")
    print("\nSecurity: This file contains cookies. Do not share or commit it.\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        page.goto(args.login_url, wait_until="domcontentloaded")

        try:
            input("Press ENTER here after you have successfully logged in...")
        except KeyboardInterrupt:
            print("\nCancelled.")
            browser.close()
            return 130

        if args.profile_url:
            print(f"Opening profile URL to verify login: {args.profile_url}")
            page.goto(args.profile_url, wait_until="domcontentloaded")

        context.storage_state(path=str(output_path))
        print(f"\nSaved storage state to: {output_path}")

        browser.close()

    print("\nNext:")
    print("  - Set LINKEDIN_STORAGE_STATE_PATH in backend/.env")
    print("  - Restart the API server")
    print("  - Retry /api/recruiters/enrich")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
