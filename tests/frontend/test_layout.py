from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

import pytest
from playwright.sync_api import expect

if TYPE_CHECKING:
    from playwright.sync_api import Locator

    from .conftest import BackendTestApp


@dataclass
class LayoutTest:
    app: BackendTestApp

    total_panels: ClassVar[int] = 3

    def tab_groups(self) -> Locator:
        return self.app.page.locator(".dv-groupview")

    def tab(self, title: str) -> Locator:
        return self.tab_groups().filter(
            has=self.app.page.locator(".dv-tab", has_text=title)
        )

    def visible_tab_groups_count(self) -> int:
        groups = self.tab_groups()
        count = 0
        for i in range(groups.count()):
            box = groups.nth(i).bounding_box()
            if box and box["width"] > 0 and box["height"] > 0:
                count += 1
        return count

    def assert_all_tab_panels_visible(self) -> None:
        expect(self.tab_groups()).to_have_count(self.total_panels)
        assert self.visible_tab_groups_count() == self.total_panels
        expect(self.app.page.locator(".layout-maximize-button")).to_have_count(
            self.total_panels
        )


@pytest.fixture
def layout_test(app: BackendTestApp) -> LayoutTest:
    return LayoutTest(app)


def test_layout_tabs_not_closable(
    app: BackendTestApp, layout_test: LayoutTest
) -> None:
    expect(app.page.locator(".dv-tab")).to_have_count(layout_test.total_panels)
    expect(app.page.locator(".dv-default-tab-action")).to_have_count(0)


def test_layout_maximize_and_restore_state(
    app: BackendTestApp, layout_test: LayoutTest
) -> None:
    # Verify default layout works
    expect(layout_test.tab_groups()).to_have_count(layout_test.total_panels)
    layout_test.assert_all_tab_panels_visible()

    viewer_button = layout_test.tab("Viewer").locator(
        ".layout-maximize-button"
    )
    viewer_button.click()
    expect(viewer_button).to_have_attribute("aria-label", "Restore panel")
    assert layout_test.visible_tab_groups_count() == 1

    viewer_button.click()
    expect(viewer_button).to_have_attribute("aria-label", "Maximize panel")
    layout_test.assert_all_tab_panels_visible()

    app.page.reload()
    layout_test.assert_all_tab_panels_visible()
