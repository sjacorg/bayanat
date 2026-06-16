import os
from typing import Optional
from urllib.parse import urlparse, unquote

from flask import render_template, current_app


def _safe_url_fetcher(url: str):
    """Block external/arbitrary-file resource fetching during PDF rendering
    (BAY-01-025). Untrusted rich-text img[src] would otherwise let WeasyPrint
    make outbound requests (SSRF) or read local files (file:// disclosure).

    Allow only: data: URIs, the app's own static assets (BASE_URL), and local
    files under the app root (the logo and rewritten inline media). Everything
    else is refused, the resource is skipped and PDF generation continues.
    """
    from weasyprint import default_url_fetcher

    parsed = urlparse(url)
    if parsed.scheme == "data":
        return default_url_fetcher(url)
    if parsed.scheme == "file":
        root = os.path.realpath(current_app.root_path)
        path = os.path.realpath(unquote(parsed.path))
        if path == root or path.startswith(root + os.sep):
            return default_url_fetcher(url)
        raise ValueError(f"PDF export: blocked file URL outside app root: {url}")
    if parsed.scheme in ("http", "https"):
        # Match scheme + host exactly. A startswith() prefix check would let
        # https://<base-host>.evil/ through when BASE_URL has no trailing
        # slash (BAY-01-025).
        base = urlparse(current_app.config.get("BASE_URL") or "")
        if base.netloc and parsed.scheme == base.scheme and parsed.netloc == base.netloc:
            return default_url_fetcher(url)
        raise ValueError(f"PDF export: blocked external URL: {url}")
    raise ValueError(f"PDF export: blocked URL scheme: {url}")


class PDFUtil:
    """PDF generation utility class."""

    def __init__(self, model):
        self.model = model

    def generate_pdf(self, output: Optional[str] = None) -> None:
        """
        Generate a PDF from the model data.

        Args:
            - output (str): The path to save the PDF to. If None, the PDF will be returned as a binary string.
        """
        if self.model.__tablename__ == "bulletin":
            html = render_template(
                "pdf/bulletin.html", bulletin=self.model, path=current_app.root_path
            )
        elif self.model.__tablename__ == "actor":
            html = render_template(
                "pdf/actor.html",
                actor=self.model,
                path=current_app.root_path,
            )
        elif self.model.__tablename__ == "incident":
            html = render_template(
                "pdf/incident.html", incident=self.model, path=current_app.root_path
            )

        if output:
            from weasyprint import HTML

            HTML(string=html, url_fetcher=_safe_url_fetcher).write_pdf(output)

    @property
    def filename(self):
        return f"{self.model.__tablename__}-{self.model.id}.pdf"
