from flask import render_template
from weasyprint import HTML, CSS

class PDFUtil:
    def __init__(self, model):
        self.model = model

    def generate_pdf(self, output=None):
        if self.model.__tablename__ == 'bulletin':
            html = render_template('pdf/bulletin.html', bulletin=self.model)
        elif self.model.__tablename__ == 'actor':
            html = render_template('pdf/actor.html', actor=self.model)
        elif self.model.__tablename__ == 'incident':
            html = render_template('pdf/incident.html', incident=self.model)

        if output:
            pdf = HTML(string=html).write_pdf(output)


    @property
    def filename(self):
        return f'{self.model.__tablename__}-{self.model.id}.pdf'
