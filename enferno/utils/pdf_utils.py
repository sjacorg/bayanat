from typing import Optional
from flask import render_template
from weasyprint import HTML
from flask import current_app


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
            pdf = HTML(string=html).write_pdf(output)

    @property
    def filename(self):
        return f"{self.model.__tablename__}-{self.model.id}.pdf"
