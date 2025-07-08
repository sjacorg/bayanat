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
      upMediaBtnDisabled: true,
      videoDialog: false,
      audioDialog: false,
      mediaPlayer: null,
      playerOptions: {},
      videoMeta: {},
      audioMeta: {},
      screenshots: [],
      snapshot: null,
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

    initCroppr() {
      if (this.cropper.active) this.destroyCrop();
    
      const video = this.mediaPlayer.el().getElementsByTagName('video')[0];
      video.pause();
    
      const maxPreviewSize = 250;
    
      // calculate preview size
      let newWidth = this.videoMeta.width;
      let newHeight = this.videoMeta.height;
    
      if (newWidth > maxPreviewSize) {
        newHeight = (newHeight * maxPreviewSize) / newWidth;
        newWidth = maxPreviewSize;
      }
    
      // ✅ Store full-res video frame
      this.cropper.fullCanvas = document.createElement('canvas');
      this.cropper.fullCanvas.width = this.videoMeta.width;
      this.cropper.fullCanvas.height = this.videoMeta.height;
    
      const fullCtx = this.cropper.fullCanvas.getContext('2d');
      fullCtx.drawImage(video, 0, 0, this.videoMeta.width, this.videoMeta.height);
    
      // 👁️ Create preview canvas (scaled down)
      this.cropper.canvas = document.createElement('canvas');
      this.cropper.canvas.width = newWidth;
      this.cropper.canvas.height = newHeight;
    
      const context = this.cropper.canvas.getContext('2d');
      context.fillRect(0, 0, newWidth, newHeight);
      context.drawImage(
        video,
        0, 0,
        this.videoMeta.width, this.videoMeta.height,
        0, 0,
        newWidth, newHeight
      );
    
      // 📏 Save scale factor between preview and full-res
      this.cropper.previewScale = newWidth / this.videoMeta.width;
    
      // 📷 Update image preview
      let img = document.querySelector('#cropImg');
      if (!img) {
        img = new Image();
        img.id = 'cropImg';
    
        this.$nextTick(() => {
          document.querySelector('.crop').prepend(img);
        });
      }
    
      img.src = this.cropper.canvas.toDataURL('image/jpeg');
      this.cropper.time = Math.round(video.currentTime * 10) / 10;
      this.cropper.tool = new Croppr(img);
      this.cropper.active = true;
    
      this.snapshot = {
        ...this.videoMeta,
        time: this.cropper.time,
        fileType: 'image/jpeg',
        ready: true,
      };
    },
    destroyCrop() {
      document.querySelector('.croppr-container')?.remove();
      this.cropper.active = false;
    },

    getFileName(path) {
      return path
        .split('/')
        .pop()
        .split(/[#?]/)[0]
        .replace(/\.[^/.]+$/, '');
    },
    async attachSnapshot(form) {
      try {
        const blob = await this.getCroppedImageData();
    
        let data = new FormData();
        let filename = this.snapshot.filename;
        if (!filename.endsWith('.jpg')) {
          filename += '.jpg';
        }
        data.append('file', blob, filename);
    
        const response = await axios.post("/admin/api/media/upload", data, {
          headers: { "content-type": false },
        });
    
        const serverId = response.data;
        console.log('Response', response.data);
    
        this.snapshot.filename = serverId.filename;
        this.snapshot.etag = serverId.etag;
        this.snapshot.ready = true;
    
        let skipped = [];
    
        if (this.editedItem.medias.some(media => media.etag === this.snapshot.etag)) {
          skipped.push(this.snapshot);
        } else {
          const mediaItem = {
            title: form.title,
            title_ar: form.title_ar,
            fileType: this.snapshot.fileType,
            filename: this.snapshot.filename,
            etag: this.snapshot.etag,
            time: this.snapshot.time,
            category: form.category,
          };
          this.editedItem.medias.push(mediaItem);
        }
    
        if (skipped.length) {
          this.showSnack(`${skipped.length} duplicate items skipped.`);
        }
    
      } catch (err) {
        console.error(err?.response?.data || err);
        this.showSnack(err?.response?.data || "Upload failed.");
      }
    },
    getCroppedImageData() {
      return new Promise((resolve) => {
        const crop = this.cropper.tool.getValue();
        const fullCanvas = this.cropper.fullCanvas;
        const scale = this.cropper.previewScale;
    
        // ✅ Convert crop box from preview scale to full resolution
        const realX = crop.x / scale;
        const realY = crop.y / scale;
        const realW = crop.width / scale;
        const realH = crop.height / scale;
    
        this.$nextTick(() => {
          const canvas = document.createElement('canvas');
          canvas.width = realW;
          canvas.height = realH;
    
          const context = canvas.getContext('2d');
          context.fillRect(0, 0, realW, realH);
          context.drawImage(
            fullCanvas,
            realX,
            realY,
            realW,
            realH,
            0,
            0,
            realW,
            realH
          );
    
          canvas.toBlob((blob) => {
            resolve(blob);
          }, 'image/jpeg');
        });
      });
    },

    viewMedia({ media, mediaType }) {
      // Cleanup existing player if it exists
      this.disposeMediaPlayer();
      this.media = media;

      const videoElement = buildVideoElement();
      if (mediaType === 'audio') {
        videoElement.poster = '/static/img/waveform.png';
      }

      const playerContainer = this.$refs.inlineMediaRendererRef.$refs.playerContainer || this.$refs.playerContainer; // Ensure you have a ref="playerContainer" on the container element
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

    addMedia(media, item, index) {
      this.editedMedia = JSON.parse(JSON.stringify(this.defaultMedia));
      //console.log(this.editedEvent);
      //enable below to activate edit mode
      //this.editedMediaIndex = index;

      //reset dual fields display to english
      this.mediaDialog = true;
      //this.locations = this.editedItem.locations;
    },

    removeMedia: function (index) {
      if (confirm('Are you sure?')) {
        this.editedItem.medias.splice(index, 1);
      }
    },

    closeMediaDialog() {
      this.destroyCrop();
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

    handleExpandedMedia({media, mediaType}) {
      const isSameContent = this.expandedMedia?.s3url === media?.s3url
      if (isSameContent) {
        return this.closeExpandedMedia();
      }

      this.expandedMedia = media;
      this.expandedMediaType = mediaType;

      if (!media || !mediaType) return

      this.$nextTick(() => {
        if (['video', 'audio'].includes(mediaType)) {
          this.viewMedia({ media, mediaType });
        }
        this.$refs.inlineMediaRendererRef?.$el?.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
        })
      })

    },
    closeExpandedMedia() {
      this.expandedMedia = null;
      this.expandedMediaType = null;
    },
    handleFullscreen() {
      switch (this.expandedMediaType) {
        case 'audio':
        case 'video':
          this.mediaPlayer?.requestFullscreen()
          break;
        case 'image':
          this.$refs.inlineMediaRendererRef?.$refs?.imageViewer?.requestFullscreen()
          break;
        case 'pdf':
          this.$refs.inlineMediaRendererRef?.$refs?.pdfViewer?.requestFullscreen()
          break;
        default:
          break;
      }
    }
  }
};
