"""Configurable custom careers page adapter."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

from pydantic import BaseModel, ConfigDict

from job_aggregator.app.adapters.base import (
    AdapterContext,
    AdapterFetchMode,
    AdapterResult,
    BaseJobAdapter,
)
from job_aggregator.app.fetchers.browser import BrowserFetcher
from job_aggregator.app.fetchers.http import FetchError, HttpFetcher


class CustomPageConfig(BaseModel):
    """Configuration for simple static careers pages."""

    company_name: str
    listing_url: str
    item_selector: str = ".job"
    title_selector: str = ".title"
    url_selector: str = ".title"
    location_selector: str | None = ".location"
    team_selector: str | None = ".team"
    employment_type_selector: str | None = ".employment"
    description_selector: str | None = ".description"
    browser_fallback: bool = False

    model_config = ConfigDict(extra="forbid")


class HtmlNode:
    """Tiny DOM node for fixture-friendly selector extraction."""

    def __init__(
        self,
        tag: str,
        attrs: dict[str, str] | None = None,
        *,
        parent: HtmlNode | None = None,
    ) -> None:
        self.tag = tag
        self.attrs = attrs or {}
        self.parent = parent
        self.children: list[HtmlNode] = []
        self._text: list[str] = []

    def append_text(self, value: str) -> None:
        self._text.append(value)

    def text(self) -> str:
        parts = list(self._text)
        for child in self.children:
            parts.append(child.text())
        return " ".join(part.strip() for part in parts if part.strip()).strip()

    def href(self) -> str | None:
        return self.attrs.get("href")

    def matches(self, selector: str) -> bool:
        if selector.startswith("."):
            wanted = selector[1:]
            return wanted in self.attrs.get("class", "").split()
        if selector.startswith("#"):
            return self.attrs.get("id") == selector[1:]
        return self.tag == selector

    def find_all(self, selector: str) -> list[HtmlNode]:
        matches = [self] if self.matches(selector) else []
        for child in self.children:
            matches.extend(child.find_all(selector))
        return matches

    def select_one(self, selector: str | None) -> HtmlNode | None:
        if selector is None:
            return None
        matches = self.find_all(selector)
        return matches[0] if matches else None


class _SimpleHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.root = HtmlNode("document")
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = HtmlNode(tag, {key: value or "" for key, value in attrs}, parent=self._stack[-1])
        self._stack[-1].children.append(node)
        self._stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].append_text(data)


def parse_html(html: str) -> HtmlNode:
    """Parse HTML into a tiny DOM tree."""

    parser = _SimpleHtmlParser()
    parser.feed(html)
    return parser.root


def _node_text(node: HtmlNode | None) -> str | None:
    if node is None:
        return None
    return node.text() or None


class CustomPageAdapter(BaseJobAdapter):
    """Adapter boundary for simple configurable careers pages."""

    name = "custom_page"
    fetch_mode = AdapterFetchMode.HYBRID
    source_scope = "custom_page_config"

    def __init__(
        self,
        *,
        config: CustomPageConfig | None = None,
        fetcher: HttpFetcher | None = None,
        browser_fetcher: BrowserFetcher | None = None,
    ) -> None:
        self.config = config
        self.fetcher = fetcher
        self.browser_fetcher = browser_fetcher

    async def fetch_jobs(self, context: AdapterContext | None = None) -> AdapterResult:
        """Fetch and parse a configured static careers page."""

        config = self._config_from_context(context)
        if config is None:
            return self.result(
                errors=[
                    self.error(
                        stage="configure",
                        message="Custom page adapter requires config or context options.",
                    )
                ]
            )

        try:
            if self.fetcher is not None:
                html = await self.fetcher.get_text(config.listing_url)
            else:
                async with HttpFetcher() as fetcher:
                    html = await fetcher.get_text(config.listing_url)
        except FetchError as exc:
            if not config.browser_fallback:
                return self.result(
                    errors=[
                        self.error(
                            stage="fetch",
                            target_url=config.listing_url,
                            error_type=exc.__class__.__name__,
                            message=str(exc),
                        )
                    ]
                )
            browser = self.browser_fetcher or BrowserFetcher()
            html = await browser.fetch_text(config.listing_url)

        try:
            jobs = self.parse_html(html, config=config)
        except ValueError as exc:
            return self.result(
                errors=[
                    self.error(
                        stage="parse",
                        target_url=config.listing_url,
                        error_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                ]
            )
        return self.result(jobs=jobs)

    def _config_from_context(self, context: AdapterContext | None) -> CustomPageConfig | None:
        if self.config is not None:
            return self.config
        if context and context.options:
            return CustomPageConfig.model_validate(context.options)
        return None

    def parse_html(self, html: str, *, config: CustomPageConfig) -> list:
        """Parse configured HTML into raw job postings."""

        root = parse_html(html)
        item_nodes = root.find_all(config.item_selector)
        if not item_nodes:
            raise ValueError(f"No job nodes matched selector {config.item_selector!r}")

        jobs = []
        for index, node in enumerate(item_nodes, start=1):
            title_node = node.select_one(config.title_selector)
            url_node = node.select_one(config.url_selector)
            title = _node_text(title_node)
            href = url_node.href() if url_node else None
            if not title or not href:
                raise ValueError("Each job node must include title text and a URL.")
            jobs.append(
                self.raw_job(
                    source_job_id=node.attrs.get("data-id") or href,
                    source_url=urljoin(config.listing_url, href),
                    title=title,
                    company_name=config.company_name,
                    team_name=_node_text(node.select_one(config.team_selector)),
                    location_text=_node_text(node.select_one(config.location_selector)),
                    employment_type_text=_node_text(
                        node.select_one(config.employment_type_selector)
                    ),
                    description_text=_node_text(node.select_one(config.description_selector)),
                    raw_payload={"index": index, "href": href},
                )
            )
        return jobs
