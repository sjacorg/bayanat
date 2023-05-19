import regex
from arabic_reshaper import reshape
from bidi.algorithm import get_display
from fpdf import FPDF

from enferno.admin.models import Bulletin, Media


def n(var):
    # also check if it has arabic

    if var:
        if has_arabic(str(var)):
            return get_display(reshape(str(var)))
        else:
            return str(var)
    return ''


def has_arabic(var):
    arabic_pattern = regex.compile(r'\p{Script=Arabic}(?![\p{N}])')
    return bool(arabic_pattern.search(var))


class PDFUtil(FPDF):
    DEFAULT_FONT = 'dejavu'

    DEFAULT_LINE_HEIGHT = 9

    def __init__(self):
        super().__init__()

    def write_field(self, label, value, html=False):
        """
        Helper method to write a database column to pdf
        :param label: text title of the column
        :param value: value of the column
        :return: none
        """
        if value:
            col_type = value.__class__.__name__
            if col_type == 'datetime':
                value = value.strftime("%B %d, %Y at %H:%M:%S")
            if col_type == 'list':
                value = ', '.join(value)
            if col_type == 'InstrumentedList':
                value = ', '.join([item.title for item in value])
            if col_type == 'int':
                value = str(value)
            
            # Replace inline api links
            if label == 'Description':
                inline_str = "src=\"../api/serve/inline"
                if value.find(inline_str) != -1:
                    inline_dir = "src=\"" + str(Media.inline_dir)
                    value = value.replace(inline_str, inline_dir)

            self.write(PDFUtil.DEFAULT_LINE_HEIGHT, f'{label}    ')

            # preprocess /check if it has Arabic charachters
            if has_arabic(value):
                value = get_display(reshape(value))
            if html:
                self.ln(5)
                self.write_html(value)
            else:
                self.write(PDFUtil.DEFAULT_LINE_HEIGHT, value)

            self.ln(PDFUtil.DEFAULT_LINE_HEIGHT)  # Move to the next line

    def write_main_info(self, bulletin):
        table_data = (
            ('Bulletin ID', 'Origin ID'),
            (n(bulletin.id), n(bulletin.originid)),
            ('Source Link',),
            (n(bulletin.source_link) if bulletin.source_link != 'NA' else '',),
            ('Publish Date', 'Documentation Date'),
            (n(bulletin.publish_date), n(bulletin.documentation_date)),
        )
        with self.table(borders_layout="None", first_row_as_headings=False) as table:
            for data_row in table_data:
                row = table.row()
                for val in data_row:
                    row.cell(n(val))
        self.ln(5)

    def write_event(self, event):
        table_data = (
            ('Title', 'Comments', 'Location'),
            (n(event.title), n(event.comments), n(event.location.title) if event.location else ''),
            ('Type', 'From', 'To', 'Estimated'),
            (n(event.eventtype.title) if event.eventtype else '', n(event.from_date),
             n(event.to_date), n(event.estimated))

        )
        with self.table(first_row_as_headings=False) as table:
            for data_row in table_data:
                row = table.row()
                for val in data_row:
                    row.cell(n(val))
        self.ln(5)

    def write_media(self, media):
        table_data = (
            ('Title', 'Filename', 'Hash'),
            (n(media.title), n(media.media_file), n(media.etag)),
            ('File Type', 'Main', 'Duration'),
            (n(media.media_file_type), n(media.main), n(media.duration))
        )
        with self.table(first_row_as_headings=False) as table:
            for data_row in table_data:
                row = table.row()
                for val in data_row:
                    row.cell(n(val))
        self.ln(5)

    def write_related_items(self, relations, rel_type):
        self.ln(8)
        with self.table(borders_layout="SINGLE_TOP_LINE") as table:
            table.row((f'{rel_type} ID', 'Title'))
            for item in relations:
                table.row((f'{item.get("id")}', f'{item.get("title")}'))

    def header(self):
        self.set_margins(10, 30, 10)
        self.image('enferno/static/img/bayanat-h-v2.png', x=8, y=10, w=40)

    def footer(self):
        self.set_y(-15)

        self.cell(0, PDFUtil.DEFAULT_LINE_HEIGHT, 'Page %s' % self.page_no(), 0, 0, 'C')


class BulletinPDFUtil:
    def __init__(self, bulletin: Bulletin):
        self.bulletin = bulletin
        self.pdf = PDFUtil()
        self.pdf.add_font(family='dejavu', fname='enferno/static/font/DejaVuSansCondensed.ttf')
        self.pdf.add_font(family='dejavu', style='B', fname='enferno/static/font/DejaVuSansCondensed.ttf')
        self.pdf.set_font('dejavu', '', 12)

    def generate_pdf(self):
        self.pdf.add_page()

        self.pdf.write_main_info(self.bulletin)
        self.pdf.ln(8)

        self.pdf.write_field('Original Title', self.bulletin.title)
        self.pdf.write_field('Original Title (ar)', self.bulletin.title_ar)

        self.pdf.write_field('SJAC Title', self.bulletin.sjac_title)
        self.pdf.write_field('SJAC Title (ar)', self.bulletin.sjac_title_ar)

        self.pdf.write_field('Origin ID', self.bulletin.originid)

        self.pdf.write_field('Description', self.bulletin.description, html=True)

        self.pdf.write_field('Labels', self.bulletin.labels)

        self.pdf.write_field('Verfied Labels', self.bulletin.ver_labels)

        self.pdf.write_field('Sources', self.bulletin.sources)

        self.pdf.write_field('Locations', self.bulletin.locations)

        # Events
        self.pdf.ln(8)

        self.pdf.write_html(u'<b>Events</b>')
        self.pdf.ln(8)
        if self.bulletin.events:
            for event in self.bulletin.events:
                self.pdf.write_event(event)

        # Media
        self.pdf.ln(8)

        self.pdf.write_html(u'<b>Media</b>')
        self.pdf.ln(8)
        if self.bulletin.medias:
            for media in self.bulletin.medias:
                self.pdf.write_media(media)

        # Related Bulletins
        if self.bulletin.bulletin_relations:
            self.pdf.ln(8)
            self.pdf.write_html('<b>Related Bulletins</b>')
            self.pdf.write_related_items([r.get('bulletin') for r in self.bulletin.bulletin_relations_dict], 'bulletin')

        # Related Actors
        if self.bulletin.actor_relations:
            self.pdf.ln(8)
            self.pdf.write_html('<b>Related Actors</b>')
            self.pdf.write_related_items([r.get('actor') for r in self.bulletin.actor_relations_dict],
                                         'actor')
        # Related Incidents
        if self.bulletin.incident_relations:
            self.pdf.ln(8)
            self.pdf.write_html('<b>Related Incidents</b>')
            self.pdf.write_related_items([r.get('incident') for r in self.bulletin.incident_relations_dict],
                                         'incident')

    def write_to_pdf(self, filename):
        self.generate_pdf()
        self.pdf.output(dest='F', name=filename)

    @property
    def filename(self):
        return f'bulletin-{self.bulletin.id}.pdf'
