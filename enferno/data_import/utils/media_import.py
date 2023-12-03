import hashlib, os, boto3, json
import pyexifinfo as exiflib
from docx import Document
from PyPDF2 import PdfReader
from PIL import Image
from pdf2image import convert_from_path

from enferno.admin.models import Media, Bulletin, Source, Label, Location, Activity
from enferno.data_import.models import DataImport
from enferno.user.models import User, Role
from enferno.utils.date_helper import DateHelper
import arrow, shutil
from enferno.settings import Config as cfg
import subprocess

from enferno.utils.base import DatabaseException


def now():
    return str(arrow.utcnow())

if cfg.OCR_ENABLED:
    from pytesseract import image_to_string, pytesseract
    try:
        pytesseract.tesseract_cmd = cfg.TESSERACT_CMD
        tesseract_langs = '+'.join(pytesseract.get_languages(config=''))
    except Exception as e:
        print(f"Tesseract system package is missing or Bayanat's OCR settings are not set properly: {e}")

class MediaImport():

    # file: Filestorage class
    def __init__(self, batch_id, meta, user_id, data_import_id):

        self.meta = meta
        self.batch_id = batch_id
        self.user_id = user_id
        self.data_import = DataImport.query.get(data_import_id)

    def upload(self, filepath, target):
        """
        Copies file to media folder or S3 bucket.

            Parameters:
                filepath: filepath file
                target: file name in media
        """

        if cfg.FILESYSTEM_LOCAL:
            try:
                shutil.copy(filepath, target)
                self.data_import.add_to_log(f"File saved as {target}.")
                return True
            except Exception as e:
                self.data_import.add_to_log('Failed to save file in local filesystem.')
                self.data_import.add_to_log(str(e))
                return False

        elif cfg.S3_BUCKET:
            target = os.path.basename(target)
            s3 = boto3.resource('s3', aws_access_key_id=cfg.AWS_ACCESS_KEY_ID,
                                aws_secret_access_key=cfg.AWS_SECRET_ACCESS_KEY,
                                region_name=cfg.AWS_REGION)
            try:
                s3.Bucket(cfg.S3_BUCKET).put_object(Key=target, Body=open(filepath, 'rb'))
                self.data_import.add_to_log(f"File uploaded to S3 bucket.")
                return True
            except Exception as e:
                self.data_import.add_to_log('Failed to upload to S3 bucket.')
                self.data_import.add_to_log(str(e))
                return False
        else:
            self.data_import.add_to_log('Filesystem is not configured properly')
            return False

    def get_duration(self, filepath):
        """
        Returns duration of a video file.

            Parameters:
                filepath: filepath of video file

            Returns:
                duration: flout duration of video
        """
        try:
            # get video duration via ffprobe
            # cmd = f'ffprobe -i "{filepath}" -show_entries format=duration -v quiet -of csv="p=0"'
            cmd = ['ffprobe', '-i', f'{filepath}', '-show_entries', 'format=duration',
                   '-v', 'quiet', '-of', 'csv=p=0']
            duration = subprocess.check_output(cmd, shell=False).strip().decode('utf-8')
            return duration
        except Exception as e:
            self.data_import.add_to_log('Failed to get video duration')
            self.data_import.add_to_log(str(e))
            return None

    def get_etag(self, filepath):
        """
        Returns MD5 hash of file.

            Parameters:
                filepath: filepath of file

            Returns:
                etag: md5 hash
        """
        f = open(filepath, 'rb').read()
        etag = hashlib.md5(f).hexdigest()
        return etag

    def parse_docx(self, filepath):
        """
        Parses MS Word file.

            Parameters:
                filepath: filepath of MS Word file

            Returns:
                str: text content of the MS Word file
        """
        try:
            doc = Document(filepath)
            text_content = []

            for p in doc.paragraphs:
                if p.text:
                    text_content.append(p.text)

            return '<p>\n</p>'.join(text_content)
        except Exception as e:
            self.data_import.add_to_log('Failed to parse DOCx file.')
            self.data_import.add_to_log(str(e))
            return None

    def parse_pdf(self, filepath, attempt_ocr=False):
        """
        Parses PDF file.

            Parameters:
                filepath: filepath of PDF file

            Returns:
                str: text content of the PDF file
        """
        try:
            pdf = PdfReader(filepath)
            text_content = []

            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content.append(text)

            # if no text contect recognize
            # attempt to use Tesseract OCR
            if not text_content and attempt_ocr:
                images = convert_from_path(filepath)
                for image in images:
                    text = image_to_string(image, lang=tesseract_langs)
                    if text:
                        text_content.append(text)

            return '<p>\n</p>'.join(text_content)

        except Exception as e:
            self.data_import.add_to_log('Failed to parse PDF file.')
            self.data_import.add_to_log(str(e))
            return None

    def parse_pic(self, filepath):
        """
        Parses image files using Google's 
        Tesseract OCR engine for text content.

            Parameters:
                filepath: filepath of image file

            Returns:
                str: text content of the image file
        """
        try:
            text_content = image_to_string(filepath, lang=tesseract_langs)
            return text_content
        except Exception as e:
            self.data_import.add_to_log('Failed to parse image file using Tesseract.')
            self.data_import.add_to_log(str(e))
            return None

    def optimize(self, old_filename, old_path):
        """
        Converts a video to H.264 format.

            Parameters:
                old_filename: unoptimized video filename
                old_path: video path

            Returns:
                True/Flase: whether op is successful
                new_filename: optimized video filename
                new_filepath: optimized video file path
                new_etag: optimized video md5 hash 

        """
        check = ''
        _, ext = os.path.splitext(old_filename)

        try:
            # get video codec
            # cmd = f'ffprobe -i "{old_path}" -show_entries stream=codec_name -v quiet -of csv="p=0"'
            cmd = ['ffprobe', '-i', f'{old_path}', '-show_entries', 'stream=codec_name',
                   '-v', 'quiet', '-of', 'csv=p=0']
            check = subprocess.check_output(cmd, shell=False).strip().decode('utf-8')

        except Exception as e:
            self.data_import.add_to_log('Failed to get original video codec, optimizing anyway.')
            self.data_import.add_to_log(str(e))

        accepted_codecs = 'h264' in check or 'theora' in check or 'vp8' in check
        accepted_formats = 'mp4' in ext or 'ogg' in ext or 'webm' in ext
        accepted_codecs = accepted_formats

        if not accepted_formats or (accepted_formats and not accepted_codecs):
            # process video
            try:
                new_filename = f'{Media.generate_file_name(old_filename)}.mp4'
                new_filepath = (Media.media_dir / new_filename).as_posix()
                command = f'ffmpeg -i "{old_path}" -vcodec libx264  -acodec aac -strict -2 "{new_filepath}"'
                command = ['ffmpeg', '-i', f'{old_path}', '-vcodec', 'libx264', '-acodec', 'aac', '-strict', '-2',
                           f'{new_filepath}']
                subprocess.call(command, shell=False)

                new_etag = self.get_etag(new_filepath)
                self.data_import.add_to_log(f'Optimized version saved at {new_filepath}.')
                return True, new_filename, new_filepath, new_etag

            except Exception as e:
                self.data_import.add_to_log('An exception occurred while transcoding file.')
                self.data_import.add_to_log(str(e))
                return False, None, None, None
        else:
            return False, None, None, None

    def process(self, file):
        # handle file uploads based on mode of ETL
        duration = None
        optimized = False
        text_content = None
        self.data_import.processing()

        # Server-side mode
        if self.meta.get('mode') == 2:

            self.data_import.add_to_log(f"Processing {file.get('filename')}...")

            # check here for duplicate to skip unnecessary code execution
            old_path = file.get('path')

            # server side mode, need to copy files and generate etags
            old_filename = file.get('filename')
            title, ext = os.path.splitext(old_filename)

            filename = Media.generate_file_name(old_filename)
            filepath = (Media.media_dir / filename).as_posix()

            # copy file to media dir or s3 bucket
            if not self.upload(old_path, filepath):
                self.data_import.add_to_log("Unable to proceed without media file. Terminating.")
                self.data_import.fail()
                return

            info = exiflib.get_json(old_path)[0]

            # check file extension
            file_ext = ext[1:].lower()
            self.data_import.add_format(file_ext)

            # get duration and optimize if video
            if file_ext in cfg.ETL_VID_EXT:
                duration = self.get_duration(old_path)

                if self.meta.get('optimize'):
                    optimized, new_filename, new_filepath, new_etag = self.optimize(filename, filepath)

            # ocr pictures
            elif cfg.OCR_ENABLED and self.meta.get('ocr') and file_ext in cfg.OCR_EXT:
                parsed_text = self.parse_pic(filepath)
                if parsed_text:
                    text_content = parsed_text

            # parse content of word
            elif self.meta.get('parse') and file_ext == "docx":
                parsed_text = self.parse_docx(filepath)
                if parsed_text:
                    text_content = parsed_text

            # scan pdf for text
            elif self.meta.get('parse') and file_ext == "pdf":
                attempt_ocr = cfg.OCR_ENABLED and self.meta.get('ocr')
                parsed_text = self.parse_pdf(filepath, attempt_ocr)

                if parsed_text:
                    text_content = parsed_text

        elif self.meta.get('mode') == 1:

            self.data_import.add_to_log(f"Processing {file.get('filename')}...")

            # we already have the file and the etag
            filename = file.get('filename')
            n, ext = os.path.splitext(filename)
            title, ex = os.path.splitext(file.get('name'))
            filepath = (Media.media_dir / filename).as_posix()
            info = exiflib.get_json(filepath)[0]

            if not cfg.FILESYSTEM_LOCAL:
                self.upload(filepath, os.path.basename(filepath))

            file_ext = ext[1:].lower()
            self.data_import.add_format(file_ext)

            # get duration and optimize if video
            if ext[1:].lower() in cfg.ETL_VID_EXT:
                duration = self.get_duration(filepath)

                if self.meta.get('optimize'):
                    optimized, new_filename, new_filepath, new_etag = self.optimize(filename, filepath)

            # ocr pictures
            elif cfg.OCR_ENABLED and self.meta.get('ocr') and file_ext in cfg.OCR_EXT:
                parsed_text = self.parse_pic(filepath)
                if parsed_text:
                    text_content = parsed_text

            # parse content of word docs
            elif self.meta.get('parse') and file_ext == "docx":
                parsed_text = self.parse_docx(filepath)
                if parsed_text:
                    text_content = parsed_text

            # scan pdf for text
            elif self.meta.get('parse') and file_ext == "pdf":
                attempt_ocr = cfg.OCR_ENABLED and self.meta.get('ocr')
                parsed_text = self.parse_pdf(filepath, attempt_ocr)

                if parsed_text:
                    text_content = parsed_text

        else:
            self.data_import.add_to_log(f"Invalid import mode {self.meta.get('mode')}. Terminating.")
            self.data_import.fail()
            return
        
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

        if text_content:
            info['text_content'] = text_content

        info['etag'] = file.get('etag')
        if self.meta.get('mode') == 2:
            info['old_path'] = old_path
        # pass duration
        if duration:
            info['vduration'] = duration

        self.data_import.add_to_log("Metadata parsed successfully.")
        result = self.create_bulletin(info)
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
        bulletin.comments = f'Created using Media Import Tool. Batch ID: {self.batch_id}.'

        if info.get('text_content'):
            bulletin.description = info.get('text_content')

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
        # mark as undeletable
        org_media.main = True
        org_media.title = bulletin.title
        org_media.media_file = info.get('filename')
        # handle mime type failure
        mime_type = info.get('File:MIMEType')
        duration = info.get('vduration')
        if duration:
            org_media.duration = duration

        if not mime_type:
            self.data_import.add_to_log("Unable to retrieve file mime type.")
            try:
                os.remove(info.get('filepath'))
                self.data_import.add_to_log("Unknown file type removed.")
            except OSError as e:
                self.data_import.add_to_log("Unable to remove unknown file type.")
                self.data_import.add_to_log(str(e))

            self.data_import.fail()
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

        # access roles restrictions
        roles = self.meta.get('roles')
        if roles:
            # Fetch Roles
            bulletin_roles = Role.query.filter(Role.id.in_([r.get('id') for r in roles])).all()
            bulletin.roles = []
            bulletin.roles.extend(bulletin_roles)

        user = User.query.get(self.user_id)

        bulletin.source_link = info.get('old_path')
        bulletin.meta = info

        try:
            bulletin.save(raise_exception=True)
            bulletin.create_revision(user_id=user.id)
            # Record bulletin creation activity
            Activity.create(user, Activity.ACTION_CREATE, bulletin.to_mini(), 'bulletin')

            self.data_import.add_to_log(f"Created Bulletin {bulletin.id} successfully.")
            self.data_import.add_item(bulletin.id)
            self.data_import.sucess()
        except DatabaseException as e:
            self.data_import.add_to_log(f"Failed to create Bulletin.")
            self.data_import.fail(e)

