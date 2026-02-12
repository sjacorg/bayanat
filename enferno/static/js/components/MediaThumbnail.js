const MediaThumbnail = Vue.defineComponent({
  props: {
    media: {
      type: Object,
      required: true
    },
    s3url: {
      type: String,
      default: ''
    },
    clickable: {
      type: Boolean,
      default: false
    },
    showHoverIcon: {
      type: Boolean,
      default: false
    },
    showPlayButton: {
      type: Boolean,
      default: true
    },
    showDuration: {
      type: Boolean,
      default: true
    },
    compact: {
      type: Boolean,
      default: false
    }
  },
  emits: ['click'],
  data() {
    return {
      videoDuration: null,
      videoThumbnail: null,
      pdfThumbnailUrl: null,
      thumbnailBrightness: 0,
    };
  },
  computed: {
    mediaType() {
      return this.$root.getFileTypeFromMimeType(this.media?.fileType);
    },
    durationFormatted() {
      return this.videoDuration ? this.formatDuration(this.videoDuration) : null;
    },
  },
  watch: {
    s3url: {
      immediate: true,
      handler(newUrl) {
        if (newUrl) {
          this.initThumbnail();
        }
      }
    }
  },
  methods: {
    async loadPdfJs() {
      await loadScript('/static/js/pdf.js/pdf.min.mjs');
      await loadScript('/static/js/pdf.js/pdf.worker.min.mjs');
    },
    initThumbnail() {
      if (this.mediaType === 'video') {
        this.getVideoDuration();
        this.generateVideoThumbnail();
      } else if (this.mediaType === 'pdf') {
        this.generatePdfThumbnail();
      }
    },
    handleClick() {
      if (this.clickable) {
        this.$emit('click', { media: this.media, mediaType: this.mediaType });
      }
    },
    getVideoDuration() {
      if (this.media.duration) {
        this.videoDuration = Number(this.media.duration);
      } else {
        const video = document.createElement('video');
        video.src = this.s3url;
        video.crossOrigin = "anonymous";
        video.onloadedmetadata = () => {
          this.videoDuration = video.duration;
        };
      }
    },
    async generatePdfThumbnail() {
      try {
        if (typeof pdfjsLib === 'undefined') await this.loadPdfJs();

        const pdf = await pdfjsLib.getDocument(this.s3url).promise;
        const page = await pdf.getPage(1);

        const THUMB_WIDTH = 240;
        const DPR = window.devicePixelRatio || 1;

        // Base viewport (CSS size)
        const baseViewport = page.getViewport({ scale: 1 });
        const scale = THUMB_WIDTH / baseViewport.width;

        // Render viewport (high DPI)
        const renderViewport = page.getViewport({
          scale: scale * DPR
        });

        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        // Internal resolution
        canvas.width = Math.floor(renderViewport.width);
        canvas.height = Math.floor(renderViewport.height);

        // Display size
        canvas.style.borderRadius = "4px";
        canvas.classList.add("w-100");

        await page.render({
          canvasContext: ctx,
          viewport: renderViewport
        }).promise;

        this.pdfThumbnailUrl = canvas.toDataURL('image/png');
      } catch (err) {
        console.error("PDF thumbnail error:", err);
      }
    },
    generateVideoThumbnail() {
      const video = document.createElement('video');
      video.src = this.s3url;
      video.crossOrigin = "anonymous";
      video.onloadeddata = () => {
        video.currentTime = 1; // Seek to 1 second
        video.onseeked = () => {
          const canvas = document.createElement('canvas');
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
          this.videoThumbnail = canvas.toDataURL();
          
          // Calculate brightness of center pixels
          const centerX = Math.floor(canvas.width / 2);
          const centerY = Math.floor(canvas.height / 2);
          const imageData = ctx.getImageData(centerX - 5, centerY - 5, 10, 10);
          let brightness = 0;
          for (let i = 0; i < imageData.data.length; i += 4) {
            brightness += (imageData.data[i] + imageData.data[i + 1] + imageData.data[i + 2]) / 3;
          }
          this.thumbnailBrightness = brightness / (imageData.data.length / 4);
        };
      };
    },
    formatDuration(seconds) {
      const hrs = Math.floor(seconds / 3600);
      const mins = Math.floor((seconds % 3600) / 60);
      const secs = Math.floor(seconds % 60);
      return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    },
    getImageStyle(orientation) {
      const baseStyle = {
        objectFit: 'cover',
        transform: `rotate(${orientation}deg)`,
        maxWidth: '100%',
        maxHeight: '100%',
      };
      
      // For 90 or 270 degree rotations, we need to swap dimensions
      if (orientation === 90 || orientation === 270) {
        return {
          ...baseStyle,
          width: 'auto',
          height: '100%'
        };
      }
      
      return {
        ...baseStyle,
        width: '100%',
        height: 'auto'
      };
    }
  },
  template: /*html*/`
    <div @click="handleClick" :class="['h-100 position-relative', { 'cursor-pointer': clickable }]">
      <!-- Hover icon overlay -->
      <div v-if="showHoverIcon && clickable && (mediaType === 'video' || mediaType === 'image')" class="h-100 d-flex align-center justify-center transition-fast-in-fast-out bg-grey-darken-2 v-card--reveal text-h2 position-absolute top-0 left-0 w-100" style="z-index: 10;">
        <v-icon size="48" color="white">mdi-magnify-plus</v-icon>
      </div>

      <!-- Image preview -->
      <a class="media-item h-100 block" v-if="mediaType === 'image' && s3url" :data-src="s3url" style="position: relative; z-index: 1;">
        <div class="w-100 h-100 overflow-hidden bg-grey-lighten-2 d-flex align-center justify-center">
          <img 
            :src="s3url" 
            class="bg-grey-lighten-2" 
            :style="getImageStyle(media?.extraction?.orientation || 0)"
          >
        </div>
      </a>

      <!-- Video preview -->
      <div v-else-if="mediaType === 'video'" class="h-100 position-relative bg-grey-lighten-2">
        <img v-if="videoThumbnail" :src="videoThumbnail" class="w-100 h-100" style="object-fit: cover;">
        <div v-if="showPlayButton" class="d-flex align-center justify-center position-absolute top-0 left-0 w-100 h-100">
          <v-btn icon="mdi-play-circle" variant="text" :size="compact ? 'small' : 'x-large'" :class="['custom-play-icon', thumbnailBrightness > 128 ? 'dark-play-icon' : 'light-play-icon']"></v-btn>
        </div>
        <div v-if="showDuration && durationFormatted" class="d-flex justify-center text-caption position-absolute bottom-0 right-0 text-white mb-2 mr-2 px-1 rounded-sm" style="background: rgba(0, 0, 0, 0.6);">
          {{ durationFormatted }}
        </div>
      </div>

      <!-- PDF preview -->
      <div v-else-if="mediaType === 'pdf'" :class="['d-flex justify-center bg-grey-lighten-2 h-100 overflow-hidden', { 'align-center': !pdfThumbnailUrl, 'pa-1 align-start': pdfThumbnailUrl && compact, 'pa-4 align-start': pdfThumbnailUrl && !compact }]">
        <img v-if="pdfThumbnailUrl" :src="pdfThumbnailUrl" :class="['w-100', compact ? 'rounded-sm' : 'rounded elevation-4']" />
        <v-icon v-else :size="compact ? '32' : '64'" color="red">mdi-file-pdf-box</v-icon>
      </div>

      <!-- Audio preview -->
      <div v-else-if="mediaType === 'audio'" class="d-flex align-center justify-center bg-grey-lighten-2 h-100">
        <div class="d-flex align-center justify-center fill-height position-relative">
          <v-icon :size="compact ? '64' : '128'" color="primary">mdi-music-box</v-icon>
          <v-btn
            v-if="showPlayButton"
            icon="mdi-play-circle"
            variant="text"
            :size="compact ? 'small' : 'x-large'"
            :class="['custom-play-icon', 'dark-play-icon']"
            class="position-absolute"
            style="top: 50%; left: 50%; transform: translate(-50%, -50%);"
          ></v-btn>
        </div>
      </div>

      <!-- Other file types preview -->
      <div v-else-if="mediaType === 'unknown'" class="d-flex align-center justify-center bg-grey-lighten-2 h-100">
        <v-icon :size="compact ? '32' : '64'">mdi-file-download</v-icon>
      </div>
    </div>
  `
});