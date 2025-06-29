let mediaMixin = {
  mixins: [reauthMixin],
  data: function () {
    return {
      mediaDialog: false,
      media: null,
      medias: [],
      mediaCats: translations.mediaCats,
      editedMediaIndex: -1,
      editedMedia: {
        title: '',
        files: [],
        category: '',
      },
      defaultMedia: {
        title: '',
        files: [],
        category: null,
      },
      expandedMedia: null,
      expandedMediaType: null,
      mediaTitle__: true,
      upMediaBtnDisabled: true,
      videoDialog: false,
      audioDialog: false,
      mediaPlayer: null,
      playerOptions: {},
      videoMeta: {},
      audioMeta: {},
      screenshots: [],
      cropper: {
        canvas: null,
        tool: null,
        active: false,
      },
    };
  },

  computed: {
    enableAttach() {
      return this.editedMedia.files && this.editedMedia.files.length > 0;
    },
  },

  methods: {
    showError(err, message) {
      if ([401].includes(err?.xhr?.status)) {
        this.showLoginDialog();
      }
      this.showSnack(handleRequestError({ response: { data: message }}));
    },

    fileAdded(file) {
      // Log the added file for debugging or monitoring

      // Get the Dropzone instance
      const dropzone = this.$refs.dropzone.dz;

      // Check if there are any files in the Dropzone
      if (dropzone.files.length) {
        // Iterate over existing files in the Dropzone (excluding the current file)
        for (let i = 0; i < dropzone.files.length - 1; i++) {
          const existingFile = dropzone.files[i];

          // Check if the current file is a duplicate based on name, size, and lastModified timestamp
          if (
            existingFile.name === file.name &&
            existingFile.size === file.size &&
            existingFile.lastModified.toString() === file.lastModified.toString()
          ) {
            // Remove the duplicate file from the Dropzone
            dropzone.removeFile(file);
            break; // Exit the loop since a duplicate is found
          }
        }
      }
    },
    fileRemoved(file, error, xhr) {
      this.editedMedia.files = this.editedMedia.files.filter((f) => f.upload.uuid !== file.upload.uuid);
    },
    uploadSuccess(file, response) {
      // Add file to editedMedia.files here.
      // The 'file' object can be enhanced with the 'response' from the server as needed.
      // fix bug with file type is lose by spread operator

      file.etag = response.etag;
      file.filename = response.filename;
      if(response.original_filename) {
        file.original_filename = response.original_filename;
        if (this.editedMedia.title === ''){
          this.editedMedia.title = response.original_filename;
        } 
      }
      if(this.editedItem.medias.some(m => m.etag === file.etag)) {
        this.showSnack(file.name + ' is already uploaded. Skipping...');
        this.$refs.dropzone.dz.removeFile(file);
        this.upMediaBtnDisabled = false;
        return;
      }
      this.editedMedia.files.push(file);
      this.upMediaBtnDisabled = false;
    },

    viewImage(item) {
      viewer.show(item);
    },

    crop() {
      if (this.cropper.active) {
        document.querySelector('.croppr-container').remove();
        this.cropper.active = false;
        return;
      }

      const video = this.mediaPlayer.el().getElementsByTagName('video')[0];
      video.pause();

      this.cropper.canvas = document.createElement('canvas');
      this.cropper.canvas.width = this.videoMeta.width;
      this.cropper.canvas.height = this.videoMeta.height;
      let context = this.cropper.canvas.getContext('2d');
      context.fillRect(0, 0, this.cropper.canvas.width, this.cropper.canvas.height);
      context.drawImage(video, 0, 0, this.cropper.canvas.width, this.cropper.canvas.height);
      let img = document.querySelector('#cropImg');
      if (!img) {
        img = new Image();
        img.id = 'cropImg';

        document.querySelector('.crop').prepend(img);
      }
      img.src = this.cropper.canvas.toDataURL('image/jpeg');
      (this.cropper.time = Math.round(video.currentTime * 10) / 10),
        (this.cropper.tool = new Croppr(img));
      this.cropper.active = true;
    },

    attachCrop() {
      const crop = this.cropper.tool.getValue();
      const img = document.querySelector('.croppr-image');

      const id = this.screenshots.length;
      const video = this.mediaPlayer.el().getElementsByTagName('video')[0];

      let media = {
        width: crop.width,
        height: crop.height,
        time: this.cropper.time,
        fileType: 'image/jpeg',
        filename: video.src.getFilename(),
        ready: false,
        overlay: false,
        sw: true,
      };

      this.screenshots.push(media);
      // wait until data binding is in effect
      this.$nextTick(() => {

        let canvas = document.querySelector('.canvas' + id);
        canvas.width = media.width;
        canvas.height = media.height;
        // calculate ration based on widht/height

        let context = canvas.getContext('2d');
        context.fillRect(0, 0, media.width, media.height);
        context.drawImage(
          img,
          crop.x,
          crop.y,
          media.width,
          media.height,
          0,
          0,
          media.width,
          media.height,
        );

        //clear source image

        document.querySelector('.croppr-container').remove();
        this.cropper.active = false;
      });
    },

    getFileName(path) {
      return path
        .split('/')
        .pop()
        .split(/[#?]/)[0]
        .replace(/\.[^/.]+$/, '');
    },

    snapshot() {
      let id = this.screenshots.length;
      if (!this.mediaPlayer || !this.mediaPlayer.isReady_) {
        this.showSnack('Error: Media player is not initialized or not ready.');
        return;
      }

      const video = this.mediaPlayer.el().getElementsByTagName('video')[0];

      video.pause();


      let media = {
        width: this.videoMeta.width,
        height: this.videoMeta.height,
        time: Math.round(video.currentTime * 10) / 10,
        fileType: 'image/jpeg',
        filename: this.videoMeta.filename,
        ready: false,
        overlay: false,
        sw: true,
      };

      this.screenshots.push(media);
      // wait until data binding is in effect
      this.$nextTick(() => {

        let canvas = document.querySelector('.canvas' + id);
        canvas.width = media.width;
        canvas.height = media.height;
        let context = canvas.getContext('2d');
        context.fillRect(0, 0, media.width, media.height);
        context.drawImage(video, 0, 0, media.width, media.height);
      });
    },
    removeSnapshot(e, index) {
      debugger;
      this.screenshots.splice(index,1);
      //this.screenshots[index].deleted = true;
      // force Vue to re-render the UI
      this.$forceUpdate();
    },
    uploadSnapshot(e, index) {
      let media = this.screenshots[index];
      media.overlay = true;
      let canvas = document.querySelector('#screenshots .canvas' + index);
      let dataUrl = canvas.toDataURL("image/jpeg");
      let blob = dataUriToBlob(dataUrl);
      let data = new FormData();
      let filename = media.filename;
      if (!filename.endsWith('.jpg')) {
        filename += '.jpg';
      }


      data.append('file', blob, filename)

      axios.post("/admin/api/media/upload", data, {
          headers: {"content-type": false}
      }).then(response => {

          const serverId = response.data;
          //this.showSnack(response.data);
          media.filename = serverId.filename;
          media.etag = serverId.etag;
          media.overlay = false;
          media.ready = true;


          //this.refresh(this.options);
      }).catch(err => {
          console.error(err.response.data);
          this.showSnack(err.response.data);

          media.error = true;
      }).finally(() => {
          media.overlay = false;
      });


  },

    // Prepares and filters snapshots for attachment
    prepareSnapshotsForAttachment() {
      return this.screenshots.filter((snapshot) => snapshot.ready && !snapshot.deleted);
    },

    // Attaches prepared snapshots to the edited item
    attachPreparedSnapshots(preparedSnapshots) {
      let skipped = [];

      for (const snapshot of preparedSnapshots) {
        if (this.editedItem.medias.some((media) => media.etag === snapshot.etag)) {
          skipped.push(snapshot);
        } else {
          let mediaItem = {
            title: snapshot.title,
            title_ar: snapshot.title_ar,
            fileType: snapshot.fileType,
            filename: snapshot.filename,
            etag: snapshot.etag,
            time: snapshot.time,
            category: snapshot.category,
          };
          this.editedItem.medias.push(mediaItem);
        }
      }

      if (skipped.length) {
        this.showSnack(`${skipped.length} duplicate items skipped.`);
      }
    },

    attachSnapshots() {
      let preparedSnapshots = this.prepareSnapshotsForAttachment();
      this.attachPreparedSnapshots(preparedSnapshots);
      this.disposeMediaPlayer();
    },

    viewMedia(media) {
      // Cleanup existing player if it exists
      this.disposeMediaPlayer();
      this.media = media;

      const videoElement = buildVideoElement();
      if (media.fileType.includes('audio')) {
        videoElement.poster = '/static/img/waveform.png';
      }

      const playerContainer = this.$refs.playerContainer; // Ensure you have a ref="playerContainer" on the container element
      playerContainer.prepend(videoElement);

      this.mediaPlayer = videojs(videoElement, DEFAULT_VIDEOJS_OPTIONS);

      this.mediaPlayer.src({ src: media.s3url, type: media?.fileType ?? 'video/mp4' });
      this.mediaPlayer.on('loadedmetadata', this.handleMetaData);
      this.mediaPlayer.play();
      videoElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    handleMetaData() {
      const videoElement = this.mediaPlayer.el().querySelector('video');
      this.videoMeta = {
        filename: videoElement.src.getFilename(),
        time: videoElement.currentTime,
        width: videoElement.videoWidth,
        height: videoElement.videoHeight,
      };
    },

    disposeMediaPlayer() {
      this.mediaPlayer?.dispose?.();
      this.mediaPlayer = null;
      this.media = null;
    },
    
    viewMediaPlayerDialog(media) {
      if (media.fileType.includes('video')) {
        this.videoDialog = true;
      } else {
        this.audioDialog = true;
      }
      this.screenshots = [];
      this.$nextTick(() => {
        this.viewMedia(media);
      });
    },

    addMedia(media, item, index) {
      this.editedMedia = JSON.parse(JSON.stringify(this.defaultMedia));
      //console.log(this.editedEvent);
      //enable below to activate edit mode
      //this.editedMediaIndex = index;

      //reset dual fields display to english
      this.mediaTitle__ = true;
      this.mediaDialog = true;
      //this.locations = this.editedItem.locations;
    },

    removeMedia: function (index) {
      if (confirm('Are you sure?')) {
        this.editedItem.medias.splice(index, 1);
      }
    },

    closeMediaDialog() {
      this.editedMedia.files = [];
      this.videoDialog = false;
      this.audioDialog = false;
      this.mediaDialog = false;
      setTimeout(() => {
        this.editedMedia = Object.assign({}, this.defaultMedia);

        this.editedMediaIndex = -1;
      }, 300);
    },

    attachMedia() {
      //push files from editedMedia to edited item medias
      
      for (const file of this.editedMedia.files) {
        let item = {};
        const response = JSON.parse(file.xhr.response);
        item.title = this.editedMedia.title;
        item.title_ar = this.editedMedia.title_ar;
        item.category = this.editedMedia.category;
        item.fileType = file.type;
        item.filename = response.filename;
        item.uuid = file.upload.uuid;
        item.etag = file.etag;
        this.editedItem.medias.push(item);
      }

      this.$refs.dropzone.dz.removeAllFiles();
      this.closeMediaDialog();
    },

    onFileUploaded(error, file) {
      if (!error) {
        this.upMediaBtnDisabled = false;
      } else {
        if (error.code == 409) {
          this.showSnack('This file already exists in the system');
        } else {
          this.showSnack('Error uploading media. Please check your network connection.');
        }
        console.log(error);
      }
    },

    handleExpandedMedia(media, mediaType) {
      this.expandedMedia = media;
      this.expandedMediaType = mediaType;

      if (!media || !mediaType) return

      this.$nextTick(() => {
        if (['video', 'audio'].includes(mediaType)) {
          this.viewMedia(media)
        }
        this.$refs.expandedMediaRef?.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
        })
      })

    },
    closeExpandedMedia() {
      this.expandedMedia = null;
      this.expandedMediaType = null;
    }
  }
};
