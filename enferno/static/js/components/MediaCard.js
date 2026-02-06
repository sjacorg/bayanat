const thumbnailContent = `
  <div @click="handleMediaClick" class="h-100 position-relative overflow-hidden">
    <!-- Image preview -->
    <div v-if="isHoveringPreview && (mediaType === 'video' || mediaType === 'image')" class="h-100 d-flex align-center justify-center transition-fast-in-fast-out bg-grey-darken-2 v-card--reveal text-h2">
      <v-icon size="48" color="white">mdi-magnify-plus</v-icon>
    </div>

    <!-- Image preview with gradient placeholder -->
    <template v-if="mediaType === 'image'">
      <!-- Random gradient placeholder - ALWAYS show it first -->
      <div 
        class="w-100 h-100 position-absolute top-0 left-0" 
        :style="{ 
          background: getRandomGradient(), 
          filter: 'blur(40px)',
          transform: 'scale(1.2)',
          opacity: imageLoaded ? 0 : 1,
          transition: 'opacity 0.4s ease-in-out',
          zIndex: 1
        }">
      </div>
      
      <!-- Actual image - only render when we have s3url -->
      <a class="media-item h-100 d-block position-relative" v-if="s3url" :data-src="s3url" style="z-index: 2;">
        <img 
          loading="lazy" 
          :src="s3url" 
          @load="imageLoaded = true"
          class="w-100 h-100" 
          style="object-fit: cover;"
          :style="{ 
            opacity: imageLoaded ? 1 : 0, 
            transition: 'opacity 0.4s ease-in-out' 
          }">
          <v-expand-transition>  
            <div v-if="isHoveringPreview" class="h-100 d-flex align-center justify-center transition-fast-in-fast-out bg-grey-darken-2 v-card--reveal text-h2 position-absolute top-0 left-0 w-100" style="z-index: 3;">
              <v-icon size="48" color="white">mdi-magnify-plus</v-icon>
            </div>
          </v-expand-transition>
        </img>
      </a>
    </template>

    <!-- Video preview with gradient placeholder -->
    <template v-if="mediaType === 'video'">
      <!-- Random gradient placeholder - ALWAYS show it first -->
      <div 
        class="w-100 h-100 position-absolute top-0 left-0" 
        :style="{ 
          background: getRandomGradient(), 
          filter: 'blur(40px)',
          transform: 'scale(1.2)',
          opacity: videoThumbnail ? 0 : 1,
          transition: 'opacity 0.4s ease-in-out',
          zIndex: 1
        }">
      </div>
      
      <v-img 
        v-if="videoThumbnail"
        :src="videoThumbnail" 
        cover 
        class="h-100 position-relative"
        :style="{ 
          opacity: videoThumbnail ? 1 : 0,
          transition: 'opacity 0.4s ease-in-out',
          zIndex: 2
        }">
        <div class="d-flex align-center justify-center fill-height">
          <v-btn icon="mdi-play-circle" variant="text" size="x-large" :class="['custom-play-icon', thumbnailBrightness > 128 ? 'dark-play-icon' : 'light-play-icon']"></v-btn>
        </div>
        <div v-if="durationFormatted" class="d-flex justify-center text-caption position-absolute bottom-0 right-0 text-white mb-2 mr-2 px-1 rounded-sm" style="background: rgba(0, 0, 0, 0.6);">
          {{ durationFormatted }}
        </div>
      </v-img>
    </template>

    <!-- PDF preview -->
    <div v-else-if="mediaType === 'pdf'" :class="['d-flex justify-center bg-grey-lighten-2 h-100 overflow-hidden', { 'align-center': !pdfThumbnailUrl, 'pa-4 align-start': pdfThumbnailUrl }]">
      <img v-if="pdfThumbnailUrl" :src="pdfThumbnailUrl" class="w-100 rounded elevation-4" />
      <v-icon v-else size="64" color="red">mdi-file-pdf-box</v-icon>
    </div>

    <!-- Audio preview -->
    <div v-else-if="mediaType === 'audio'" class="d-flex align-center justify-center bg-grey-lighten-2 h-100">
      <div class="d-flex align-center justify-center fill-height position-relative">
        <v-icon size="128" color="primary">mdi-music-box</v-icon>
        <v-btn icon="mdi-play-circle" variant="text" size="x-large" :class="['custom-play-icon', 'dark-play-icon']" class="position-absolute" style="top: 50%; left: 50%; transform: translate(-50%, -50%);"></v-btn>
      </div>
    </div>

    <!-- Other file types preview -->
    <div v-else-if="mediaType === 'unknown'" class="d-flex align-center justify-center bg-grey-lighten-2 h-100">
      <v-icon size="64">mdi-file-download</v-icon>
    </div>
  </div>
`

const toolbarContent = `
    <v-toolbar density="compact" class="px-2">
      <div class="w-100 d-flex justify-space-between align-center">
        <div class="d-flex align-center">
          <v-icon :icon="iconMap[mediaType]" :color="mediaType === 'pdf' ? 'red' : 'primary'"></v-icon>
          <v-divider vertical class="mx-2"></v-divider>
          <v-chip prepend-icon="mdi-identifier" variant="text" class="font-weight-bold">{{ media.id }}</v-chip>
          <v-divider vertical class="mx-2"></v-divider>
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-chip prepend-icon="mdi-tag" variant="plain" v-if="media.category" size="small" v-bind="props">
                {{ media.category.title }}
              </v-chip>
            </template>
            <span>{{ translations.category_ }}</span>
          </v-tooltip>
        </div>
      </div>

    </v-toolbar>
    <v-divider></v-divider>
    <v-sheet>
      <uni-field :english="media.title || 'Untitled'" :arabic="media.title_ar || ''" class="py-0 my-0" />
    </v-sheet>
    <v-divider></v-divider>
`

const fileMetadata = `
  <v-card-text class="px-2 py-1">
    <div class=" cursor-pointer" @click="copyToClipboard(media.filename)">
      <v-list-item class="text-caption ml-1 py-0">
        <template v-slot:prepend>
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props" icon="mdi-file-outline"></v-icon>
            </template>
            <div class="d-flex flex-column align-center">
              <span><strong>{{ translations.filename_ }}</strong></span>
              <span>{{ translations.click_to_copy_ }}</span>
            </div>
          </v-tooltip>
        </template>
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <div v-bind="props" class="text-truncate">
              {{ media.filename }}
            </div>
          </template>
            {{ media.filename }}
        </v-tooltip>
      </v-list-item>
    </div>
    <div class="d-flex align-center  cursor-pointer" @click="copyToClipboard(media.etag)">
      <v-list-item class="text-caption ml-1 py-0 text-truncate">
        <template v-slot:prepend>
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon v-bind="props" icon="mdi-fingerprint"></v-icon>
              </template>
            <div class="d-flex flex-column align-center">
              <span><strong>{{ translations.etag_ }}</strong></span>
              <span>{{ translations.click_to_copy_ }}</span>
            </div>
          </v-tooltip>
        </template>
        <v-tooltip location="bottom">
          <template v-slot:activator="{ props }">
            <div v-bind="props" class="text-truncate">
              {{ media.etag }}
            </div>
          </template>
            {{ media.etag }}
        </v-tooltip>
      </v-list-item>
    </div>
  </v-card-text>
`

const MediaCard = Vue.defineComponent({
  props: {
    media: {
      type: Object,
      required: true
    },
    miniMode: {
      type: Boolean,
      default: false,
    }
  },
  emits: ['media-click', 'ready'],
  data() {
    return {
      s3url: '',
      isInViewport: false,
      observer: null,
      videoDuration: null,
      videoThumbnail: null,
      pdfThumbnailUrl: null,
      translations: window.translations,
      thumbnailBrightness: 0,
      imageLoaded: false,
      randomGradient: null, // Cache it so it doesn't change on re-render
      pdfCanvas: null,
      iconMap: {
        image: 'mdi-image',
        video: 'mdi-video',
        pdf: 'mdi-file-pdf-box',
        audio: 'mdi-music-box',
        unknown: 'mdi-file-download'
      },
    };
  },
  computed: {
    mediaType() {
      const fileType = this.media.fileType;
      if (['image/jpeg', 'image/png', 'image/gif'].includes(fileType)) return 'image';
      if (['video/webm', 'video/mp4', 'video/ogg'].includes(fileType)) return 'video';
      if (['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg'].includes(fileType)) return 'audio';
      if (['application/pdf'].includes(fileType)) return 'pdf';
      return 'unknown';
    },
    durationFormatted() {
      return this.videoDuration ? this.formatDuration(this.videoDuration) : null;
    },
  },
  mounted() {
    this.setupIntersectionObserver();
  },
  beforeUnmount() {
    if (this.observer) {
      this.observer.disconnect();
    }
  },
  methods: {
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
    setupIntersectionObserver() {
      const element = this.$refs.rootCard.$el;
      
      if (!element) {
        console.warn('Root element not found for intersection observer');
        return;
      }
      
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
        { rootMargin: '100px' }
      );
      
      this.observer.observe(element);
    },
    async loadPdfJs() {
      await loadScript('/static/js/pdf.js/pdf.min.mjs');
      await loadScript('/static/js/pdf.js/pdf.worker.min.mjs');
    },
    init() {
      api.get(`/admin/api/media/${this.media.filename}`)
        .then(response => {
          this.s3url = response.data.url;
          this.media.s3url = response.data.url;
          if (this.mediaType === 'video') {
            // Check if duration exists in media object
            if (this.media.duration) {
              this.videoDuration = Number(this.media.duration);
            }
            this.generateVideoThumbnail(); // This now handles both duration and thumbnail
          } else if (this.mediaType === 'pdf') {
            this.generatePdfThumbnail();
          }
        })
        .catch(error => console.error('Error fetching media:', error))
        .finally(() => this.$emit('ready'));
    },
    handleMediaClick() {
      switch (this.mediaType) {
        case 'pdf':
        case 'image':
        case 'video':
        case 'audio':
          this.$emit('media-click', { media: this.media, mediaType: this.mediaType});
          break;
        default:
          this.downloadFile();
      }
    },
    getVideoDuration() {
      if (this.media.duration) {
        this.videoDuration = Number(this.media.duration)
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
      
      // Get duration when metadata loads
      video.onloadedmetadata = () => {
        if (!this.media.duration) {
          this.videoDuration = video.duration;
        }
      };
      
      // Generate thumbnail when data loads
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
          
          // Clean up
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
    downloadFile() {
      const link = document.createElement('a');
      link.href = this.s3url;
      link.download = this.media.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    },
    copyToClipboard(text) {
      navigator.clipboard.writeText(text)
        .then(() => this.$root.showSnack('Copied to clipboard'))
        .catch(() => this.$root.showSnack('Failed to copy to clipboard'));
    },
  },
  template: /*html*/`
    <!-- Mini mode card -->
    <v-card v-if="miniMode" ref="rootCard" style="width: min(200px,100%); height: fit-content;" class="border border-1 mx-2" :disabled="!s3url">
      <v-card-text class="text-center pa-0">
        <v-hover v-slot="{ isHovering: isHoveringPreview, props: previewHoverProps }">
          <div v-bind="previewHoverProps" class="preview-container position-relative cursor-pointer"
              style="height: 120px;">
              ${thumbnailContent}
          </div>
        </v-hover>
      </v-card-text>

      <v-card-actions class="d-flex py-0" style="min-height: 45px;">
        <v-menu
          open-on-hover
          location="top"
        >
          <template v-slot:activator="{ props }">
            <v-btn v-if="miniMode" v-bind="props" size="small" variant="text" icon="mdi-information" color="blue"></v-btn>
          </template>

          <v-card>
            ${toolbarContent}
            ${fileMetadata}
          </v-card>
        </v-menu>
      </v-card-actions>
    </v-card>

    <!-- Normal size card -->
    <v-card v-else ref="rootCard" style="width: min(350px,100%); height: fit-content;" class="border border-1 mx-2" :disabled="!s3url">
      ${toolbarContent}

      <v-card-text class="text-center pa-0">
        <v-hover v-slot="{ isHovering: isHoveringPreview, props: previewHoverProps }">
          <div v-bind="previewHoverProps" class="preview-container position-relative cursor-pointer"
              style="height: 160px;">
            ${thumbnailContent}
          </div>
        </v-hover>
      </v-card-text>

      ${fileMetadata}
      
      <v-divider></v-divider>
      <v-card-actions class="justify-end d-flex py-0" style="min-height: 45px;">
        <v-spacer></v-spacer>
        <slot name="actions"></slot>
      </v-card-actions>
    </v-card>
  `
});