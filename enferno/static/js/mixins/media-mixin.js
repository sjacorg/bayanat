const getDefaultMedia = () => ({
  title: '',
  files: [],
  category: null,
})

const mediaMixin = {
  mixins: [reauthMixin],

  data() {
    return {
      mediaDialog: false,
      snapshotDialog: false,
      media: null,
      editedMedia: {
        title: '',
        files: [],
        category: '',
      },
      expandedMedia: null,
      expandedMediaType: null,
      mediaPlayer: null,
      videoMeta: {},
      snapshot: null,
      cropper: {
        fullCanvas: null,
        canvas: null,
        tool: null,
        active: false,
      },
    };
  },

  /* ------------------------------------------------------------------
   * COMPUTED — normalized refs
   * ------------------------------------------------------------------ */
  computed: {
    enableAttach() {
      return this.editedMedia.files?.length > 0;
    },

    dropzone() {
      return this.getRef(this.$refs.dropzone)?.dz || null;
    },

    inlineMediaRenderer() {
      return this.getRef(this.$refs.inlineMediaRendererRef);
    },

    inlineMediaRendererEl() {
      return this.inlineMediaRenderer?.$el || null;
    },

    imageViewer() {
      return this.inlineMediaRenderer?.$refs?.imageViewer || null;
    },

    pdfViewer() {
      return this.inlineMediaRenderer?.$refs?.pdfViewer || null;
    },

    playerContainer() {
      return (
        this.inlineMediaRenderer?.$refs?.playerContainer ||
        this.$refs.playerContainer ||
        null
      );
    },
  },

  /* ------------------------------------------------------------------
   * METHODS
   * ------------------------------------------------------------------ */
  methods: {
    /* ---------- ref helper ---------- */
    getRef(ref) {
      if (!ref) return null;
      return Array.isArray(ref) ? ref[0] : ref;
    },

    showError(err, message) {
      if ([401].includes(err?.xhr?.status)) {
        this.showLoginDialog();
      }
      this.showSnack(handleRequestError({ response: { data: message }}));
    },

    /* ---------- Dropzone ---------- */
    fileAdded(file) {
      const dz = this.dropzone;
      if (!dz) return;

      for (let i = 0; i < dz.files.length - 1; i++) {
        const existingFile = dz.files[i];
        if (
          existingFile.name === file.name &&
          existingFile.size === file.size &&
          existingFile.lastModified?.toString() === file.lastModified?.toString()
        ) {
          dz.removeFile(file);
          break;
        }
      }
    },

    fileRemoved(file) {
      this.editedMedia.files = this.editedMedia.files.filter(
        f => f.upload.uuid !== file.upload.uuid
      );
    },

    uploadSuccess(file, response) {
      file.etag = response.data.etag;
      file.filename = response.data.filename;

      if (response.data.original_filename) {
        file.original_filename = response.data.original_filename;
        if (!this.editedMedia.title) {
          this.editedMedia.title = response.data.original_filename;
        }
      }

      if (this.editedItem.medias.some(m => m.etag === file.etag)) {
        this.showSnack(`${file.name} is already uploaded. Skipping…`);
        this.dropzone?.removeFile(file);
        return;
      }

      this.editedMedia.files.push(file);
    },

    /* ---------- Snapshot / Crop ---------- */
    openSnapshotDialog() {
      this.snapshotDialog = true;
    },

    closeSnapshotDialog() {
      this.snapshotDialog = false;
    },

    initCroppr() {
      if (this.cropper.active) this.destroyCrop();
      this.openSnapshotDialog();

      const videoElement = this.mediaPlayer.el().querySelector('video');
      videoElement.pause();

      const { width, height } = this.videoMeta;
      const maxSize = 600;
      const scale = Math.min(maxSize / width, maxSize / height, 1);

      const previewWidth = width * scale;
      const previewHeight = height * scale;

      const fullCanvas = document.createElement('canvas');
      fullCanvas.width = width;
      fullCanvas.height = height;
      fullCanvas.getContext('2d').drawImage(videoElement, 0, 0);
      this.cropper.fullCanvas = fullCanvas;

      const previewCanvas = document.createElement('canvas');
      previewCanvas.width = previewWidth;
      previewCanvas.height = previewHeight;
      previewCanvas.getContext('2d').drawImage(
        videoElement,
        0, 0, width, height,
        0, 0, previewWidth, previewHeight
      );

      this.cropper.canvas = previewCanvas;
      this.cropper.previewScale = scale;

      this.$nextTick(() => {
        const previewImage = document.querySelector('#cropImg');
        previewImage.src = previewCanvas.toDataURL('image/jpeg');

        this.cropper.time = Math.round(videoElement.currentTime * 10) / 10;
        this.cropper.tool = new Croppr(previewImage);
        this.cropper.active = true;
      });

      this.snapshot = {
        ...this.videoMeta,
        time: Math.round(videoElement.currentTime * 10) / 10,
        fileType: 'image/jpeg',
        ready: true,
      };
    },

    destroyCrop() {
      document.querySelector('.croppr-container')?.remove();
      this.cropper.active = false;
    },

    async attachSnapshot(form) {
      try {
        const blob = await this.getCroppedImageData();

        const formData = new FormData();
        let filename = this.snapshot.filename;
        if (!filename.endsWith('.jpg')) filename += '.jpg';
        formData.append('file', blob, filename);

        const response = await axios.post('/admin/api/media/upload', formData, {
          headers: { 'content-type': false },
        });

        const uploaded = response.data;
        this.snapshot.filename = uploaded.filename;
        this.snapshot.etag = uploaded.etag;
        this.snapshot.ready = true;

        if (this.editedItem.medias.some(m => m.etag === uploaded.etag)) {
          this.showSnack('1 duplicate item skipped.');
          return;
        }

        this.editedItem.medias.push({
          title: form.title,
          title_ar: form.title_ar,
          fileType: this.snapshot.fileType,
          filename: uploaded.filename,
          etag: uploaded.etag,
          time: this.snapshot.time,
          category: form.category,
        });

        this.closeSnapshotDialog();
      } catch (error) {
        console.error(error?.response?.data || error);
        this.showSnack(error?.response?.data || 'Upload failed.');
      }
    },

    getCroppedImageData() {
      return new Promise(resolve => {
        const { x, y, width, height } = this.cropper.tool.getValue();
        const scale = this.cropper.previewScale;

        const canvas = document.createElement('canvas');
        canvas.width = width / scale;
        canvas.height = height / scale;

        canvas.getContext('2d').drawImage(
          this.cropper.fullCanvas,
          x / scale,
          y / scale,
          width / scale,
          height / scale,
          0,
          0,
          canvas.width,
          canvas.height
        );

        canvas.toBlob(blob => resolve(blob), 'image/jpeg');
      });
    },

    getFileName(path) {
      return path
        .split('/')
        .pop()
        .split(/[#?]/)[0]
        .replace(/\.[^/.]+$/, '');
    },

    /* ---------- Media viewing ---------- */
    viewMedia({ media, mediaType }) {
      this.disposeMediaPlayer();
      this.media = media;

      const videoElement = buildVideoElement();
      if (mediaType === 'audio') {
        videoElement.poster = '/static/img/waveform.png';
      }

      this.playerContainer?.prepend(videoElement);

      this.mediaPlayer = videojs(videoElement, DEFAULT_VIDEOJS_OPTIONS);
      this.mediaPlayer.src({ src: media.s3url, type: media.fileType });
      this.mediaPlayer.on('loadedmetadata', this.handleMetaData);
      this.mediaPlayer.play();

      videoElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    },

    handleMetaData() {
      const video = this.mediaPlayer.el().querySelector('video');
      this.videoMeta = {
        filename: video.src.getFilename(),
        time: video.currentTime,
        width: video.videoWidth,
        height: video.videoHeight,
      };
    },

    disposeMediaPlayer() {
      this.mediaPlayer?.dispose?.();
      this.mediaPlayer = null;
      this.media = null;
    },

    /* ---------- Attach / detach ---------- */
    addMedia() {
      this.editedMedia = getDefaultMedia();
      this.mediaDialog = true;
    },

    removeMedia(index) {
      if (confirm('Are you sure?')) {
        this.editedItem.medias.splice(index, 1);
      }
    },

    attachMedia() {
      for (const file of this.editedMedia.files) {
        const response = JSON.parse(file.xhr.response);
        this.editedItem.medias.push({
          title: this.editedMedia.title,
          title_ar: this.editedMedia.title_ar,
          category: this.editedMedia.category,
          fileType: file.type,
          filename: response.data.filename,
          uuid: file.upload.uuid,
          etag: file.etag,
        });
      }

      this.dropzone?.removeAllFiles();
      this.closeMediaDialog();
    },

    closeMediaDialog() {
      this.destroyCrop();
      this.editedMedia.files = [];
      this.mediaDialog = false;
      setTimeout(() => {
        this.editedMedia = getDefaultMedia();
      }, 300);
    },

    /* ---------- Expanded media ---------- */
    handleExpandedMedia({ media, mediaType }) {
      if (this.expandedMedia?.s3url === media?.s3url) {
        return this.closeExpandedMedia();
      }

      this.expandedMedia = media;
      this.expandedMediaType = mediaType;

      this.$nextTick(() => {
        if (['video', 'audio'].includes(mediaType)) {
          this.viewMedia({ media, mediaType });
        }

        this.inlineMediaRendererEl?.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
        });
      });
    },

    closeExpandedMedia() {
      this.expandedMedia = null;
      this.expandedMediaType = null;
    },

    handleFullscreen() {
      switch (this.expandedMediaType) {
        case 'video':
        case 'audio':
          this.mediaPlayer?.requestFullscreen();
          break;
        case 'image':
          this.imageViewer?.requestFullscreen();
          break;
        case 'pdf':
          this.pdfViewer?.requestFullscreen();
          break;
      }
    },
  },
};
