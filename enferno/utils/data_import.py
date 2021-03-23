import hashlib, ntpath, os
import pyexifinfo as exiflib

from enferno.admin.models import Media, Bulletin, Source, Label, Location
from enferno.utils.date_helper import DateHelper

class DataImport():

    # file: Filestorage class
    def __init__(self, file, meta):
        self.file = file
        self.meta = meta

    def process(self):
        # print (request.files)
        old_filename = ntpath.basename(self.file.filename)
        title = os.path.splitext(old_filename)[0]
        filename = Media.generate_file_name(old_filename)
        filepath = (Media.media_dir / filename).as_posix()
        self.file.save(filepath)
        # get md5 hash
        f = open(filepath, 'rb').read()
        print('File upload success')
        etag = hashlib.md5(f).hexdigest()
        # get mime type
        # mime = magic.Magic(mime=True)
        # mime_type = mime.from_file(filepath)

        print('Hash generated :: {}'.format(etag))
        info = exiflib.get_json(filepath)[0]
        print(info.get('EXIF:CreateDate'))
        # bundle title with json info
        info['bulletinTitle'] = title
        info['filename'] = filename
        info['etag'] = etag

        print('Meta data parse success')
        self.create_bulletin(info)
        return info

    def create_bulletin(self, info):
        """
        creates bulletin from file and its meta data
        :return: created bulletin
        """
        bulletin = Bulletin()
        # mapping
        bulletin.title = info.get('bulletinTitle')
        bulletin.status = 'Machine Created'
        bulletin.comments = 'Created by ETL '
        create = info.get('EXIF:CreateDate')
        if create:
            bulletin.documentation_date = DateHelper.file_date_parse(create)
            print('doc date set success' + bulletin.documentation_date)
        refs = []
        refs.append(info.get('EXIF:SerialNumber'))

        media = Media()
        media.title = bulletin.title
        media.media_file = info.get('filename')
        media.media_file_type = info.get('File:MIMEType')
        media.etag = info.get('etag')

        bulletin.medias.append(media)

        # add additional meta data
        sources = self.meta.get('sources')
        if sources:
            ids = [s.get('id') for s in sources]
            bulletin.sources = Source.query.filter(Source.id.in_(ids)).all()

        labels = self.meta.get('labels')
        if labels:
            ids = [l.get('id') for l in labels]
            bulletin.labels = Label.query.filter(Label.id.in_(ids)).all()

        locations = self.meta.get('locations')
        if locations:
            ids = [l.get('id') for l in labels]
            bulletin.locations = Location.query.filter(Location.id.in_(ids)).all()

        mrefs = self.meta.get('refs')

        if mrefs:
            refs = refs + mrefs
        bulletin.ref = refs

        bulletin.save()
        bulletin.create_revision()




