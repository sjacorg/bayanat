import hashlib, ntpath, os
import pyexifinfo as exiflib
from enferno.admin.models import Media, Bulletin, Source, Label, Location, Activity
from enferno.user.models import User
from enferno.utils.date_helper import DateHelper
import arrow, shutil


def now():
    return str(arrow.utcnow())

#log_file = '{}.log'.format(uuid.uuid4().hex[:8])
#log = open(log_file, 'a')


class DataImport():

    # file: Filestorage class
    def __init__(self, batch_id, meta, user_id, log):

        self.meta = meta
        self.batch_id = batch_id
        self.user_id = user_id
        self.summary = ''
        self.log = open(log,'a')



    def process(self, file):

        # handle file uploads based on mode of ETL

        print (file)
        if self.meta.get('mode') == 2:
            self.summary += '------------------------------------------------------------------------ \n'
            self.summary += now() + 'file: {}'.format(file.get('file').get('name')) + '\n'


            # check here for duplicate to skip unnecessary code execution
            old_path = file.get('file').get('path')
            # get md5 hash directly from the source file (before copying it)
            f = open(old_path, 'rb').read()
            etag = hashlib.md5(f).hexdigest()

            exists = Media.query.filter(Media.etag == etag).first()

            if exists:
                self.summary += now() + ' File already exists:  {} \n'.format(old_path)
                print('File already exists: {} \n'.format(old_path))
                self.summary += '------------------------------------------------------------------------\n\n'
                self.log.write(self.summary)
                return


            #server side mode, need to copy files and generate etags
            old_filename = file.get('file').get('name')
            title = os.path.splitext(old_filename)[0]
            filename = Media.generate_file_name(old_filename)
            filepath = (Media.media_dir / filename).as_posix()
            shutil.copy(old_path, filepath)
            self.summary  += now() + ' File saved as {}'.format(filename) + '\n'


        elif self.meta.get('mode') == 1:
            self.summary += now() + ' ------ Processing file: {} ------'.format(file.get('filename')) + '\n'
            # we already have the file and the etag
            filename = file.get('filename')
            title = os.path.splitext(filename)[0]
            filepath = (Media.media_dir / filename).as_posix()
            etag = file.get('etag')
            # check here for duplicate to skip unnecessary code execution
            exists = Media.query.filter(Media.etag == etag).first()
            #print (exists)
            if exists:
                self.summary += now() + ' File already exists:  {} \n'.format(filepath)
                try:
                    os.remove(filepath)
                    print('duplicate file cleaned ')
                except OSError:
                    pass
                print ('File already exists: {} \n'.format(filepath))
                self.summary += '------------------------------------------------------------------------\n\n'
                self.log.write(self.summary)
                return "This file already exists"

        # get mime type
        # mime = magic.Magic(mime=True)
        # mime_type = mime.from_file(filepath)

        #print('Hash generated :: {}'.format(etag))
        info = exiflib.get_json(filepath)[0]
        #print(info.get('EXIF:CreateDate'))
        # bundle title with json info
        info['bulletinTitle'] = title
        info['filename'] = filename
        # pass filepath for cleanup purposes
        info['filepath'] = filepath
        info['etag'] = etag
        if self.meta.get('mode') == 2:
            info['old_path'] = old_path

        print('Meta data parse success')
        result =  self.create_bulletin(info)
        return result


    def create_bulletin(self, info):
        """
        creates bulletin from file and its meta data
        :return: created bulletin
        """
        bulletin = Bulletin()
        # mapping
        bulletin.title = info.get('bulletinTitle')
        bulletin.status = 'Machine Created'
        bulletin.comments = 'Created by ETL - {} '.format(self.batch_id)
        create = info.get('EXIF:CreateDate')
        if create:
            create_date = DateHelper.file_date_parse(create)
            if create_date:
                bulletin.documentation_date = create_date

        refs = [str(self.batch_id)]
        serial = info.get('EXIF:SerialNumber')
        if serial:
            refs.append(str(serial))

        media = Media()
        media.title = bulletin.title
        media.media_file = info.get('filename')
        # handle mime type failure
        mime_type = info.get('File:MIMEType')
        if not mime_type:
            self.summary += now() + 'Problem retrieving file mime type !' + '\n'
            print('Problem retrieving file mime type ! \n')
            try:
                os.remove(info.get('filepath'))
                print('unknown file type cleaned ')
            except OSError:
                pass

            self.summary += '------------------------------------------------------------------------\n\n'
            return
        media.media_file_type = mime_type

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

        vlabels = self.meta.get('ver_labels')
        if vlabels:
            ids = [l.get('id') for l in vlabels]
            bulletin.ver_labels = Label.query.filter(Label.id.in_(ids)).all()

        locations = self.meta.get('locations')
        if locations:
            ids = [l.get('id') for l in locations]
            bulletin.locations = Location.query.filter(Location.id.in_(ids)).all()

        mrefs = self.meta.get('refs')


        if mrefs:
            refs = refs + mrefs
        bulletin.ref = refs

        user = User.query.get(self.user_id)

        bulletin.source_link = info.get('old_path')

        bulletin.save()
        bulletin.create_revision(user_id=user.id)
        self.summary += 'Bulletin ID: {} \n'.format(bulletin.id)
        print ("bulletin ID : ", bulletin.id)
        # Record bulletin creation activity
        Activity.create(user, Activity.ACTION_CREATE, bulletin.to_mini(), 'bulletin')
        self.summary += '------------------------------------------------------------------------\n\n'
        self.log.write(self.summary)








