const getDefaultMedia = () => ({
  title: '',
  files: [],
  category: null,
})

const mediaMixin = {
  mixins: [reauthMixin],
  data: function () {
    return {
      mediaDialog: false,
      snapshotDialog: false,
      editedMedia: {
        title: '',
        files: [],
        category: '',
      },
      renderers: {},
      pendingMediaByRenderer: {},
      expandedByRenderer: {},
      dropzoneInstance: null,
      mediaPlayers: {},
      snapshot: null,
      cropper: {
        fullCanvas: null, // Full-resolution canvas for cropping
        canvas: null, // Downscaled preview canvas
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
      const dropzone = this.dropzoneInstance;
      if (!dropzone) return;

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
      file.etag = response.data.etag;
      file.filename = response.data.filename;
      if(response.data.original_filename) {
        file.original_filename = response.data.original_filename;
        if (this.editedMedia.title === ''){
          this.editedMedia.title = response.data.original_filename;
        } 
      }
      if(this.editedItem.medias.some(m => m.etag === file.etag)) {
        this.showSnack(file.name + ' is already uploaded. Skipping...');
        this.dropzoneInstance?.removeFile(file);
        return;
      }
      this.editedMedia.files.push(file);
    },

    openSnapshotDialog() {
      this.snapshotDialog = true;
    },
    closeSnapshotDialog() {
      this.snapshotDialog = false;
    },

    initCroppr(rendererId) {
      if (this.cropper.active) this.destroyCrop();
      this.openSnapshotDialog();
    
      const player = this.mediaPlayers[rendererId]
      if (!player) return

      const videoElement = player.el().querySelector('video')
      videoElement.pause();
    
      const originalWidth = this.renderers[rendererId].videoMeta.width;
      const originalHeight = this.renderers[rendererId].videoMeta.height;
      const maxPreviewWidth = 600;
      const maxPreviewHeight = 600;

      // Calculate scale factor that keeps aspect ratio and fits within both limits
      const scaleFactor = Math.min(
        maxPreviewWidth / originalWidth,
        maxPreviewHeight / originalHeight,
        1 // Don't upscale if it's already smaller
      );

      const previewWidth = originalWidth * scaleFactor;
      const previewHeight = originalHeight * scaleFactor;
    
      // Create full-resolution canvas
      const fullCanvas = document.createElement('canvas');
      fullCanvas.width = originalWidth;
      fullCanvas.height = originalHeight;
      fullCanvas.getContext('2d').drawImage(videoElement, 0, 0, originalWidth, originalHeight);
      this.cropper.fullCanvas = fullCanvas;
    
      // Create scaled preview canvas
      const previewCanvas = document.createElement('canvas');
      previewCanvas.width = previewWidth;
      previewCanvas.height = previewHeight;
      previewCanvas.getContext('2d').drawImage(
        videoElement,
        0, 0, originalWidth, originalHeight,
        0, 0, previewWidth, previewHeight
      );
      this.cropper.canvas = previewCanvas;
      this.cropper.previewScale = scaleFactor;
    
      // Update image preview and initialize Croppr
      this.$nextTick(() => {
        const previewImage = document.querySelector('#cropImg');
        previewImage.src = previewCanvas.toDataURL('image/jpeg');
    
        this.cropper.time = Math.round(videoElement.currentTime * 10) / 10;
        this.cropper.tool = new Croppr(previewImage);
        this.cropper.active = true;
      });
    
      this.snapshot = {
        ...this.renderers[rendererId].videoMeta,
        time: Math.round(videoElement.currentTime * 10) / 10,
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
    
        const formData = new FormData();
        let filename = this.snapshot.filename;
        if (!filename.endsWith('.jpg')) filename += '.jpg';
        formData.append('file', blob, filename);
    
        const response = await axios.post("/admin/api/media/upload", formData, {
          headers: { "content-type": false },
        });
    
        const uploaded = response.data;
        this.snapshot.filename = uploaded.filename;
        this.snapshot.etag = uploaded.etag;
        this.snapshot.ready = true;
    
        const isDuplicate = this.editedItem.medias.some(media => media.etag === uploaded.etag);
        if (isDuplicate) {
          this.showSnack(`1 duplicate item skipped.`);
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
        this.showSnack(error?.response?.data || "Upload failed.");
      }
    },
    getCroppedImageData() {
      return new Promise(resolve => {
        const cropBox = this.cropper.tool.getValue();
        const fullCanvas = this.cropper.fullCanvas;
        const scale = this.cropper.previewScale;
    
        const cropX = cropBox.x / scale;
        const cropY = cropBox.y / scale;
        const cropWidth = cropBox.width / scale;
        const cropHeight = cropBox.height / scale;
    
        this.$nextTick(() => {
          const croppedCanvas = document.createElement('canvas');
          croppedCanvas.width = cropWidth;
          croppedCanvas.height = cropHeight;
    
          croppedCanvas.getContext('2d').drawImage(
            fullCanvas,
            cropX, cropY, cropWidth, cropHeight,
            0, 0, cropWidth, cropHeight
          );
    
          croppedCanvas.toBlob(blob => resolve(blob), 'image/jpeg');
        });
      });
    },

    viewMedia({ rendererId, media, mediaType }) {
      const renderer = this.renderers[rendererId]
      if (!renderer?.playerContainer) {
        console.warn('mediaPlayerContainer not found for', rendererId)
        return
      }

      // ✅ dispose ONLY this renderer's player
      this.disposeMediaPlayer(rendererId)

      const videoElement = buildVideoElement()

      if (mediaType === 'audio') {
        videoElement.poster = '/static/img/waveform.png'
      }

      renderer.playerContainer.prepend(videoElement)

      const player = videojs(videoElement, DEFAULT_VIDEOJS_OPTIONS)

      player.src({
        src: media.s3url,
        type: media?.fileType ?? 'video/mp4'
      })

      player.on('loadedmetadata', () => {
        this.handleMetaData(rendererId, player)
      })

      player.play()

      this.mediaPlayers[rendererId] = player

      renderer.scrollIntoView?.({
        behavior: 'smooth',
        block: 'nearest'
      })
    },

    handleMetaData(rendererId, player) {
      const video = player.el().querySelector('video')

      this.renderers[rendererId].videoMeta = {
        filename: video.src.getFilename(),
        time: video.currentTime,
        width: video.videoWidth,
        height: video.videoHeight,
      }
    },

    disposeMediaPlayer(rendererId) {
      if (rendererId) {
        const player = this.mediaPlayers?.[rendererId]
        if (!player) return
  
        player.dispose()
        delete this.mediaPlayers[rendererId]
      } else {
        this.mediaPlayers = {}
      }
    },


    addMedia(media, item, index) {
      this.editedMedia = getDefaultMedia()

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
      this.mediaDialog = false;
      setTimeout(() => {
        this.editedMedia = getDefaultMedia()
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
        item.filename = response.data.filename;
        item.uuid = file.upload.uuid;
        item.etag = file.etag;
        this.editedItem.medias.push(item);
      }

      this.dropzoneInstance?.removeAllFiles();
      this.closeMediaDialog();
    },

    handleExpandedMedia({ rendererId, media, mediaType }) {
      const current = this.expandedByRenderer?.[rendererId]
      // toggle same media on same renderer
      if (current?.media?.s3url === media?.s3url) {
        this.closeExpandedMedia(rendererId)
        return
      }

      this.expandedByRenderer[rendererId] = {
        media,
        mediaType,
      }

      if (['video', 'audio'].includes(mediaType)) {
        this.pendingMediaByRenderer[rendererId] = { media, mediaType }
      } else {
        delete this.pendingMediaByRenderer[rendererId]
      }
    },
    closeExpandedMedia(rendererId) {
      if (rendererId) {
        delete this.expandedByRenderer[rendererId];
        delete this.pendingMediaByRenderer[rendererId];
      } else {
        this.expandedByRenderer = {};
        this.pendingMediaByRenderer = {};
      }
      this.disposeMediaPlayer(rendererId)
    },
    handleFullscreen(rendererId) {
      const expanded = this.expandedByRenderer?.[rendererId]
      const renderer = this.renderers?.[rendererId]
      if (!expanded || !renderer) return

      if (['video', 'audio'].includes(expanded.mediaType)) {
        this.mediaPlayers[rendererId]?.requestFullscreen()
      } else {
        renderer.requestFullscreen?.()
      }
    },
    onMediaRendererReady({ rendererId, playerContainer, requestFullscreen, scrollIntoView }) {
      if (!rendererId) return

      this.renderers[rendererId] = {
        playerContainer,
        requestFullscreen,
        scrollIntoView,
        videoMeta: null,
      }

      const pending = this.pendingMediaByRenderer[rendererId]

      if (pending && playerContainer) {
        delete this.pendingMediaByRenderer[rendererId]
        this.viewMedia({ rendererId, ...pending })
      }

      this.renderers[rendererId]?.scrollIntoView?.({
        behavior: 'smooth',
        block: 'center',
      })
    },
    onDropzoneReady(dz) {
      this.dropzoneInstance = dz
    },
  }
};
