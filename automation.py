"""Visible-browser automation for the Party City voice demo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from playwright.sync_api import (
    Browser,
    Error as PlaywrightError,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


PARTY_CITY_HOME = "https://www.partycity.ca/en.html"
PARTY_CITY_CART = "https://www.partycity.ca/en/shopping-cart.html"
SEARCH_TERMS = {"balloon": "balloons", "pinata": "pinata"}
CATEGORY_URLS = {
    "balloon": (
        "https://www.partycity.ca/en/cat/balloons-accessories/"
        "latex-balloons-DC1000010.html"
    ),
    "pinata": (
        "https://www.partycity.ca/en/cat/party-supplies/decorations/"
        "hanging-decorations/pinatas-DC1000068.html"
    ),
}


class AutomationError(RuntimeError):
    """Raised when a requested browser action cannot be completed."""


@dataclass(frozen=True)
class ChangeResult:
    requested_item: str
    removed_item: str | None
    added_item: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "requested_item": self.requested_item,
            "removed_item": self.removed_item,
            "added_item": self.added_item,
        }


class PartyCityAutomation:
    """Owns one visible browser and keeps its cart between commands."""

    def __init__(self, *, headless: bool = False, timeout_ms: int = 20_000) -> None:
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.page: Page | None = None
        self.current_item: str | None = None

    def start_browser(self) -> None:
        if self.page is not None:
            return

        self._playwright = sync_playwright().start()
        launch_args = {"headless": self.headless, "slow_mo": 250 if not self.headless else 0}
        try:
            # Prefer the person's installed Chrome; fall back to Playwright Chromium.
            self._browser = self._playwright.chromium.launch(
                channel="chrome", **launch_args
            )
        except PlaywrightError:
            self._browser = self._playwright.chromium.launch(**launch_args)

        context = self._browser.new_context(
            viewport={"width": 1440, "height": 960},
            locale="en-CA",
        )
        self.page = context.new_page()
        self.page.set_default_timeout(self.timeout_ms)
        # The retail site is script-heavy and can take over a minute to finish
        # its initial navigation even though controls are already rendering.
        self.page.set_default_navigation_timeout(90_000)
        self.page.goto(PARTY_CITY_HOME, wait_until="domcontentloaded")
        self._dismiss_overlays()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()
        self.page = None
        self._browser = None
        self._playwright = None

    def handle_change(self, item: str) -> ChangeResult:
        normalized = item.lower().strip()
        if normalized not in SEARCH_TERMS:
            raise ValueError("Only 'balloon' and 'pinata' are supported.")
        self.start_browser()

        if self.current_item == normalized:
            return ChangeResult(normalized, None, normalized)

        removed = self.current_item
        if removed is not None:
            self.remove_from_cart(removed)

        self.add_to_cart(normalized)
        self.current_item = normalized
        return ChangeResult(normalized, removed, normalized)

    def add_to_cart(self, item: str) -> None:
        page = self._require_page()
        # Party City's public search URL rejects automated browsers with a 403.
        # These are the site's own category/search-result pages for our two
        # intentionally hardcoded demo keywords.
        page.goto(CATEGORY_URLS[item], wait_until="domcontentloaded")

        self._dismiss_overlays()
        quick_add_locator = page.locator(
            "li[data-testid='product-grids'] button[aria-label='Add'], "
            "[data-testid*='product-card'] button[aria-label='Add']"
        )
        try:
            quick_add_locator.first.wait_for(state="visible", timeout=12_000)
        except PlaywrightTimeoutError:
            pass
        quick_add = self._first_visible(
            (
                quick_add_locator,
                page.get_by_role("button", name="Add", exact=True),
            )
        )
        if quick_add is not None:
            quick_add.click()
            self._wait_for_cart_confirmation()
            return

        # Fallback for layouts where the category card does not expose quick-add.
        product_link = self._find_product_link()
        if product_link is None:
            raise AutomationError(f"No Party City search result found for {item}.")

        product_link.click()
        page.wait_for_load_state("domcontentloaded")
        self._dismiss_overlays()

        add_button = self._first_visible(
            (
                page.locator(
                    "button[data-testid*='add-to-cart']"
                    ":not(#add-to-cart-sticky-buy-bar)"
                ),
                page.get_by_role("button", name="Add to Cart", exact=False),
                page.get_by_role("button", name="Add to cart", exact=False),
                page.locator(
                    "button[data-testid*='add-to-cart'], "
                    "button[class*='add-to-cart'], button[id*='addToCart']"
                ),
            )
        )
        if add_button is None:
            raise AutomationError(
                f"Found a {item} product, but its Add to Cart button is unavailable."
            )

        try:
            add_button.click()
        except PlaywrightTimeoutError:
            # The site's sticky buy bar can report itself visible while its CSS
            # places it just outside the viewport. Triggering the same DOM click
            # is reliable in that layout.
            add_button.evaluate("(button) => button.click()")
        self._wait_for_cart_confirmation()

    def remove_from_cart(self, item: str) -> None:
        page = self._require_page()
        self._open_cart()
        self._dismiss_overlays()

        # Prefer the row containing the known product name, then fall back to the
        # first remove control because this demo keeps one automated item at a time.
        row = page.locator(
            "article, li, tr, [data-testid*='cart-item'], [class*='cart-item']"
        ).filter(has_text=SEARCH_TERMS[item]).first
        remove_button = None
        if row.count() > 0:
            remove_button = self._first_visible(
                (
                    row.get_by_role("button", name="Remove", exact=False),
                    row.get_by_role("link", name="Remove", exact=False),
                    row.locator(
                        "button[data-testid*='remove'], button[class*='remove'], "
                        "a[data-testid*='remove'], a[class*='remove']"
                    ),
                )
            )

        if remove_button is None:
            remove_button = self._first_visible(
                (
                    page.get_by_role("button", name="Remove", exact=False),
                    page.get_by_role("link", name="Remove", exact=False),
                    page.locator(
                        "button[data-testid*='remove'], button[class*='remove'], "
                        "a[data-testid*='remove'], a[class*='remove']"
                    ),
                )
            )

        if remove_button is None:
            raise AutomationError(f"Could not find {item} in the cart to remove it.")

        remove_button.click()
        try:
            remove_button.wait_for(state="detached", timeout=8_000)
        except PlaywrightTimeoutError:
            # Some carts redraw in-place and leave the old locator attached.
            page.wait_for_timeout(1_000)

    def _search_from_header(self, term: str) -> bool:
        page = self._require_page()
        self._dismiss_overlays()
        search_box = self._first_visible(
            (
                page.get_by_role("searchbox"),
                page.locator("input[type='search']"),
                page.locator(
                    "input[placeholder*='Search' i], input[aria-label*='Search' i]"
                ),
            )
        )
        if search_box is None:
            return False
        search_box.fill(term)
        search_box.press("Enter")
        page.wait_for_load_state("domcontentloaded")
        return True

    def _find_product_link(self) -> Locator | None:
        page = self._require_page()
        page.wait_for_timeout(1_000)
        return self._first_visible(
            (
                page.locator("a[href*='/pdp/']").filter(has_text="Add"),
                page.locator(
                    "[data-testid*='product'] a[href], "
                    "[data-test*='product'] a[href]"
                ),
                page.locator(
                    "article a[href*='.html'], li[class*='product'] a[href], "
                    "div[class*='product-tile'] a[href]"
                ),
                page.locator("a[href*='/pdp/'], a[href*='/product/']"),
            )
        )

    def _open_cart(self) -> None:
        page = self._require_page()
        cart_link = self._first_visible(
            (
                page.get_by_role("link", name="Cart", exact=False),
                page.get_by_role("button", name="Cart", exact=False),
                page.locator(
                    "a[href*='cart'], button[aria-label*='cart' i], "
                    "[data-testid*='cart']"
                ),
            )
        )
        if cart_link is None:
            page.goto(PARTY_CITY_CART, wait_until="domcontentloaded")
            return
        cart_link.click()
        page.wait_for_load_state("domcontentloaded")

    def _wait_for_cart_confirmation(self) -> None:
        page = self._require_page()
        try:
            page.get_by_text("added to", exact=False).first.wait_for(
                state="visible", timeout=8_000
            )
        except PlaywrightTimeoutError:
            # Sites often update only the cart badge; allow that asynchronous
            # update to settle before accepting another command.
            page.wait_for_timeout(2_000)

    def _dismiss_overlays(self) -> None:
        page = self._require_page()
        for locator in (
            page.get_by_role("button", name="Accept", exact=False),
            page.get_by_role("button", name="Close", exact=True),
            page.get_by_role("button", name="No Thanks", exact=False),
        ):
            try:
                if locator.first.is_visible(timeout=600):
                    locator.first.click(timeout=1_500)
            except PlaywrightError:
                pass

    @staticmethod
    def _first_visible(locators: Iterable[Locator]) -> Locator | None:
        for locator in locators:
            try:
                # Responsive Party City markup often contains hidden mobile and
                # desktop copies of the same control.
                for index in range(min(locator.count(), 10)):
                    candidate = locator.nth(index)
                    if candidate.is_visible(timeout=2_000):
                        return candidate
            except PlaywrightError:
                continue
        return None

    def _require_page(self) -> Page:
        if self.page is None:
            raise AutomationError("Browser has not been started.")
        return self.page


def automation_from_environment() -> PartyCityAutomation:
    return PartyCityAutomation(
        headless=os.environ.get("HEADLESS", "").lower() in {"1", "true", "yes"}
    )
