const MediaThumbnail = Vue.defineComponent({
  props: {
    media: {
      type: Object,
      required: true
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
  emits: ['click', 'ready'],
  data() {
    return {
      videoDuration: null,
      thumbnailUrl: null,
      thumbnailBrightness: 0,
      imageLoaded: false,
      randomGradient: null, // Cache it so it doesn't change on re-render
      isInViewport: false,
      observer: null,
      s3url: '',
      isGeneratingThumbnail: false,
      hasError: false,
      clickLoading: false,
    };
  },
  mounted() {
    this.setupIntersectionObserver();
  },
  beforeUnmount() {
    if (this.observer) {
      this.observer.disconnect();
    }
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
        if (!newUrl) return;
        
        const hasExistingThumbnail = this.thumbnailUrl || this.thumbnailUrl || this.imageLoaded;
        const isGenerating = this.isGeneratingThumbnail;
        
        if (!hasExistingThumbnail && !isGenerating) {
          this.initThumbnail();
        }
      }
    }
  },
  methods: {
    setupIntersectionObserver() {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting && !this.isInViewport) {
              this.isInViewport = true;
              this.init();
              this.observer.disconnect();
            }
          });
        },
        { rootMargin: '0px' }
      );
      
      this.observer.observe(this.$el);
    },
    async init() {
      if (this.media.s3url) {
        this.s3url = this.media.s3url;
        this.initThumbnail();
        this.$emit('ready', this.media);
        return;
      }

      try {
        const response = await api.get(`/admin/api/media/${this.media.filename}`);
        this.s3url = response.data.url;
        this.media.s3url = response.data.url;
        this.initThumbnail();
      } catch (error) {
        console.error('Error fetching media:', error);
        this.hasError = true;
        this.imageLoaded = true;
        throw error;
      } finally {
        this.$emit('ready', this.media);
      }
    },
    async loadPdfJs() {
      await loadScript('/static/js/pdf.js/pdf.min.mjs');
      await loadScript('/static/js/pdf.js/pdf.worker.min.mjs');
    },
    initThumbnail() {
      if (this.mediaType === 'video') {
        this.generatethumbnailUrl();
      } else if (this.mediaType === 'pdf') {
        this.generatePdfThumbnail();
      }
    },
    async handleClick() {
      if (!this.clickable) return;

      // If already ready → emit immediately
      if (this.media?.s3url) {
        this.$emit('click', { media: this.media, mediaType: this.mediaType });
        return;
      }

      // Prevent parallel inits
      if (this.clickLoading) return;
      this.clickLoading = true;

      try {
        await this.init();   // wait for s3url
        if (this.media?.s3url) {
          this.$emit('click', { media: this.media, mediaType: this.mediaType });
        }
      } catch (e) {
        console.error('Click init failed:', e);
      } finally {
        this.clickLoading = false;
      }
    },
    async generatePdfThumbnail() {
      if (this.isGeneratingThumbnail) return;
      
      this.isGeneratingThumbnail = true;
      this.hasError = false; // Reset error state
      
      try {
        if (typeof pdfjsLib === 'undefined') {
          await loadScript('/static/js/pdf.js/pdf.min.mjs');
          await loadScript('/static/js/pdf.js/pdf.worker.min.mjs');
        }

        const pdf = await pdfjsLib.getDocument(this.s3url).promise;
        const page = await pdf.getPage(1);

        const THUMB_WIDTH = 240;
        const DPR = window.devicePixelRatio || 1;

        const baseViewport = page.getViewport({ scale: 1 });
        const scale = THUMB_WIDTH / baseViewport.width;

        const renderViewport = page.getViewport({
          scale: scale * DPR
        });

        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");

        canvas.width = Math.floor(renderViewport.width);
        canvas.height = Math.floor(renderViewport.height);
        canvas.style.borderRadius = "4px";
        canvas.classList.add("w-100");

        await page.render({
          canvasContext: ctx,
          viewport: renderViewport
        }).promise;

        this.thumbnailUrl = canvas.toDataURL('image/png');
        
        await page.cleanup();
        pdf.destroy();
        
      } catch (err) {
        console.error("PDF thumbnail error:", err);
        this.hasError = true;
      } finally {
        this.isGeneratingThumbnail = false;
      }
    },
    
    generatethumbnailUrl() {
      if (this.isGeneratingThumbnail) return;
      
      this.isGeneratingThumbnail = true;
      this.hasError = false; // Reset error state
      
      const video = document.createElement('video');
      video.crossOrigin = "anonymous";
      video.preload = "metadata";
      video.src = this.s3url;
      
      video.onerror = (e) => {
        console.error('Video thumbnail generation failed:', e);
        this.hasError = true; // Set error state
        this.isGeneratingThumbnail = false;
        
        // Cleanup
        video.onerror = null;
        video.onloadeddata = null;
        video.onseeked = null;
        video.src = '';
        video.load();
        video.remove();
      };
      
      video.onloadeddata = () => {
        this.videoDuration = Number(video.duration);
        video.currentTime = 0.1;
        
        video.onseeked = () => {
          try {
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            this.thumbnailUrl = canvas.toDataURL();
            
            // Calculate brightness
            const centerX = Math.floor(canvas.width / 2);
            const centerY = Math.floor(canvas.height / 2);
            const imageData = ctx.getImageData(centerX - 5, centerY - 5, 10, 10);
            let brightness = 0;
            for (let i = 0; i < imageData.data.length; i += 4) {
              brightness += (imageData.data[i] + imageData.data[i + 1] + imageData.data[i + 2]) / 3;
            }
            this.thumbnailBrightness = brightness / (imageData.data.length / 4);
          } catch (err) {
            console.error('Error generating video thumbnail:', err);
            this.hasError = true;
          }

          // Cleanup
          this.isGeneratingThumbnail = false;
          video.onerror = null;
          video.onloadeddata = null;
          video.onseeked = null;
          video.src = '';
          video.load();
          video.remove();
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
        transition: 'opacity 0.4s ease-in-out'
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
    },
    getRandomGradient() {
      if (this.randomGradient) return this.randomGradient;
      
      // Hash the ID to get better distribution for sequential numbers
      const id = this.media.id || 1;
      const hash = (id * 2654435761) % (2 ** 32); // Knuth's multiplicative hash
      const seed = hash / (2 ** 32); // Normalize to 0-1
      
      // Muted, realistic color schemes for documents, buildings, evidence photos
      const colorSchemes = [
        // Paper/document tones
        ['#e8e8e8', '#d4d4d4', '#c0c0c0'],
        // Concrete/building grays
        ['#95a5a6', '#7f8c8d', '#bdc3c7'],
        // Warm beige (aged paper, indoor lighting)
        ['#d7ccc8', '#bcaaa4', '#a1887f'],
        // Cool gray (overcast, fluorescent lighting)
        ['#b0bec5', '#90a4ae', '#78909c'],
        // Neutral tan (manila folders, cardboard)
        ['#d2b48c', '#c4a57b', '#b8936f'],
        // Steel/metal tones
        ['#9e9e9e', '#757575', '#616161'],
        // Pale blue-gray (institutional walls)
        ['#cfd8dc', '#b0bec5', '#90a4ae'],
        // Olive/military green (muted)
        ['#9e9d89', '#8d8b73', '#7c7a5e'],
        // Dusty brown (dirt, ruins)
        ['#a1887f', '#8d6e63', '#795548'],
        // Off-white/cream (documents under various lighting)
        ['#f5f5f5', '#eeeeee', '#e0e0e0'],
      ];
      
      const schemeIndex = Math.floor(seed * colorSchemes.length);
      const colors = colorSchemes[schemeIndex];
      
      // Angle from hash
      const angle = Math.floor(seed * 360);
      
      this.randomGradient = `linear-gradient(${angle}deg, ${colors[0]}, ${colors[1]}, ${colors[2]})`;
      
      return this.randomGradient;
    },
    handleImageError() {
      this.hasError = true;
      this.imageLoaded = true;
    },
  },
  template: /*html*/`
    <div @click="handleClick" :class="['h-100 w-100 position-relative overflow-hidden', { 'cursor-pointer': clickable }]">
      <!-- Hover icon overlay -->
      <div v-if="showHoverIcon && clickable && (mediaType === 'pdf' || mediaType === 'image')" class="h-100 d-flex align-center justify-center transition-fast-in-fast-out bg-grey-darken-2 v-card--reveal text-h2 position-absolute top-0 left-0 w-100" style="z-index: 10;">
        <v-icon size="48" color="white">mdi-magnify-plus</v-icon>
      </div>

      <!-- Image preview -->
      <template v-if="mediaType === 'image'">
        <div 
          class="w-100 h-100 position-absolute top-0 left-0" 
          :style="{ 
            background: getRandomGradient(), 
            filter: 'blur(40px)',
            opacity: imageLoaded ? 0 : 1,
            transition: 'opacity 0.4s ease-in-out',
            zIndex: 1
          }">
        </div>
        
        <!-- Fallback icon if error -->
        <a
          class="media-item h-100 d-block position-relative"
          :data-src="s3url"
          style="z-index: 2;">

          <!-- Actual image (always exists) -->
          <img 
            loading="lazy" 
            :src="s3url" 
            @load="imageLoaded = true"
            @error="handleImageError"
            class="w-100 h-100" 
            :style="{
              ...getImageStyle(media?.extraction?.orientation || 0),
              opacity: hasError ? 0 : (imageLoaded ? 1 : 0),
              pointerEvents: hasError ? 'none' : 'auto'
            }"
          >

          <!-- Error overlay instead of replacing node -->
          <div 
            v-show="hasError"
            class="position-absolute top-0 left-0 w-100 h-100 d-flex align-center justify-center bg-grey-lighten-2"
            style="z-index: 3;"
          >
            <v-icon :size="compact ? '32' : '64'" color="primary">mdi-image</v-icon>
          </div>

        </a>
      </template>

      <!-- Video preview -->
      <template v-else-if="mediaType === 'video'">
        <div 
          class="w-100 h-100 position-absolute top-0 left-0" 
          :style="{ 
            background: getRandomGradient(), 
            filter: 'blur(40px)',
            opacity: (thumbnailUrl || hasError) ? 0 : 1,
            transition: 'opacity 0.4s ease-in-out',
            zIndex: 1
          }">
        </div>
        
        <!-- Fallback icon if error -->
        <div v-if="hasError" class="w-100 h-100 d-flex align-center justify-center bg-grey-lighten-2" style="z-index: 2;">
          <v-icon :size="compact ? '64' : '128'" color="primary">mdi-video</v-icon>
        </div>
        
        <!-- Video thumbnail -->
        <v-img 
          v-else-if="thumbnailUrl"
          :src="thumbnailUrl" 
          cover 
          class="h-100 position-relative"
          :style="{ 
            opacity: thumbnailUrl ? 1 : 0,
            transition: 'opacity 0.4s ease-in-out',
            zIndex: 2
          }">
          <div v-if="showPlayButton" class="d-flex align-center justify-center fill-height">
            <v-btn icon="mdi-play-circle" variant="text" :size="compact ? 'small' : 'x-large'" :class="['custom-play-icon', thumbnailBrightness > 128 ? 'dark-play-icon' : 'light-play-icon']"></v-btn>
          </div>
          <div v-if="showDuration && durationFormatted" class="d-flex justify-center text-caption position-absolute bottom-0 right-0 text-white mb-2 mr-2 px-1 rounded-sm" style="background: rgba(0, 0, 0, 0.6);">
            {{ durationFormatted }}
          </div>
        </v-img>
      </template>

      <!-- PDF preview -->
      <div v-else-if="mediaType === 'pdf'" :class="['d-flex justify-center bg-grey-lighten-2 h-100 overflow-hidden', { 'align-center': !thumbnailUrl, 'pa-1 align-start': thumbnailUrl && compact, 'pa-4 align-start': thumbnailUrl && !compact }]">
        <!-- PDF thumbnail or fallback icon -->
        <img v-if="thumbnailUrl" :src="thumbnailUrl" :class="['w-100', compact ? 'rounded-sm' : 'rounded elevation-4']" />
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