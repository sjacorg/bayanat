import hashlib, os, boto3
import pyexifinfo as exiflib
from enferno.admin.models import Media, Bulletin, Source, Label, Location, Activity
from enferno.user.models import User
from enferno.utils.date_helper import DateHelper
import arrow, shutil
from enferno.settings import ProdConfig, DevConfig
import subprocess

def now():
    return str(arrow.utcnow())

#log_file = '{}.log'.format(uuid.uuid4().hex[:8])
#log = open(log_file, 'a')

if os.environ.get("FLASK_DEBUG") == '0':
    cfg = ProdConfig
else:
    cfg = DevConfig

class DataImport():

    # file: Filestorage class
    def __init__(self, batch_id, meta, user_id, log):

        self.meta = meta
        self.batch_id = batch_id
        self.user_id = user_id
        self.summary = ''
        self.log = open(log,'a')

    def upload(self, file, target):

        if cfg.FILESYSTEM_LOCAL:
            shutil.copy(file, target)
        elif cfg.S3_BUCKET:
            print(f'terget:{target} - {os.path.basename(target)}')
            target = os.path.basename(target)
            s3 = boto3.resource('s3', aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                                region_name=cfg.AWS_REGION
                                )
            try:
                s3.Bucket(cfg.S3_BUCKET).put_object(Key=target, Body=open(file, 'rb'))
            except Exception as e:
                print(e)
        else:
            raise RuntimeError('Filesystem is not configured properly!')

    def get_duration(self, path):
        try:
            # get video duration via ffprobe
            cmd = f'ffprobe -i "{path}" -show_entries format=duration -v quiet -of csv="p=0"'
            duration = subprocess.check_output(cmd, shell=True).strip().decode('utf-8')
            return duration
        except Exception as e:
            print('Failed to get video duration')
            print(e)
            return None

    def get_etag(self, path):
        f = open(path, 'rb').read()
        etag = hashlib.md5(f).hexdigest()
        return etag
    
    def optimize(self, old_filename, old_path):
        check = ''
        _, ext = os.path.splitext(old_filename)

        try:
            # get video codec
            cmd = f'ffprobe -i "{old_path}" -show_entries stream=codec_name -v quiet -of csv="p=0"'
            check = subprocess.check_output(cmd, shell=True).strip().decode('utf-8')

        except Exception as e:
            print('Failed to get original video codec, optimizing anyway')
            print(e)
        
        accepted_codecs = 'h264' in check or 'theora' in check or 'vp8' in check
        accepted_formats = 'mp4' in ext or 'ogg' in ext or 'webm' in ext
        accepted_codecs = accepted_formats 
        
        if not accepted_formats or (accepted_formats and not accepted_codecs):
            #process video
            try:
                new_filename = f'{Media.generate_file_name(old_filename)}.mp4'
                new_filepath = (Media.media_dir / new_filename).as_posix()
                command = f'ffmpeg -i "{old_path}" -vcodec libx264  -acodec aac -strict -2 "{new_filepath}"'
                subprocess.call(command, shell=True)

                new_etag = self.get_etag(new_filepath)
                return True, new_filename, new_filepath, new_etag

            except Exception as e:
                print(f'An exception occurred while transcoding file {e}')
                return False, None, None, None
        else:
            return False, None, None, None

    def process(self, file):
        # handle file uploads based on mode of ETL
        print(file)
        duration = None
        optimized = False
        print(self.meta.get('mode'))

        # Server-side mode
        if self.meta.get('mode') == 2:

            self.summary += '------------------------------------------------------------------------ \n'
            self.summary += now() + 'file: {}'.format(file.get('file').get('name')) + '\n'

            # check here for duplicate to skip unnecessary code execution
            old_path = file.get('file').get('path')
            # get md5 hash directly from the source file (before copying it)
            etag = self.get_etag(old_path)

            # check if original file exists in db
            exists = Media.query.filter(Media.etag == etag).first()
            if exists:
                self.summary += now() + ' File already exists:  {} \n'.format(old_path)
                print('File already exists: {} \n'.format(old_path))
                self.summary += '------------------------------------------------------------------------\n\n'
                self.log.write(self.summary)
                return

            # server side mode, need to copy files and generate etags
            old_filename = file.get('file').get('name')
            title, ext = os.path.splitext(old_filename)

            filename = Media.generate_file_name(old_filename)
            filepath = (Media.media_dir / filename).as_posix()

            # copy file to media dir or s3 bucket
            self.upload(old_path, filepath)
            self.summary += now() + f'File saved as {filename}'
            info = exiflib.get_json(old_path)[0]

            # check if file is video (accepted extension)
            if ext[1:].lower() in cfg.ETL_VID_EXT:
                duration = self.get_duration(old_path)

                if self.meta.get('optimize'):
                    optimized, new_filename, new_filepath, new_etag = self.optimize(old_filename, old_path)
                    if optimized:
                        self.summary += now() + f'Optimized version saved as {new_filename}\n'

        elif self.meta.get('mode') == 1:
            self.summary += now() + ' ------ Processing file: {} ------'.format(file.get('filename')) + '\n'

            # we already have the file and the etag
            filename = file.get('filename')
            n, ext = os.path.splitext(filename)
            title, ex = os.path.splitext(file.get('name'))
            filepath = (Media.media_dir / filename).as_posix()
            info = exiflib.get_json(filepath)[0]

            if not cfg.FILESYSTEM_LOCAL:
                self.upload(filepath, os.path.basename(filepath))

            etag = file.get('etag')

            # check here for duplicate to skip unnecessary code execution
            # this is necessary even though upload function checks for duplicates
            # as two identical files can be uploaded at the same import attempt 
            exists = Media.query.filter(Media.etag == etag).first()
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
                return 

            # else check if video processing is enabled
            if ext[1:].lower() in cfg.ETL_VID_EXT:
                duration = self.get_duration(filepath)

                if self.meta.get('optimize'):
                    optimized, new_filename, new_filepath, new_etag = self.optimize(filename, filepath)
                    if optimized:
                        self.summary += now() + f'Optimized version saved as {new_filename}\n'

        # bundle title with json info
        info['bulletinTitle'] = title
        info['filename'] = filename
        # pass filepath for cleanup purposes
        info['filepath'] = filepath

        # include details of optimized files
        if optimized:
            info['new_filename'] = new_filename
            info['new_filepath'] = new_filepath
            info['new_etag'] = new_etag

        info['etag'] = etag
        if self.meta.get('mode') == 2:
            info['old_path'] = old_path
        # pass duration
        if duration:
            info['vduration'] = duration
        print ('=====================')

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

        # media for the orginal file
        org_media = Media()
        org_media.title = bulletin.title
        org_media.media_file = info.get('filename')
        # handle mime type failure
        mime_type = info.get('File:MIMEType')
        duration = info.get('vduration')
        if duration:
            org_media.duration = duration
            print ('duration set')
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

        org_media.media_file_type = mime_type
        org_media.etag = info.get('etag')
        bulletin.medias.append(org_media)

        # additional media for optimized video
        if info.get('new_filename'):
            new_media = Media()
            new_media.title = bulletin.title
            new_media.media_file = info.get('new_filename')
            new_media.media_file_type = 'video/mp4'
            new_media.etag = info.get('new_etag')
            if duration:
                new_media.duration = duration
            bulletin.medias.append(new_media)

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
