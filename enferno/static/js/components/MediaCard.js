const thumbnailContent = `
  <div @click="handleMediaClick" class="h-100">
    <!-- Image preview -->
    <div v-if="isHoveringPreview && (mediaType === 'video' || mediaType === 'image')" class="h-100 d-flex align-center justify-center transition-fast-in-fast-out bg-grey-darken-2 v-card--reveal text-h2">
      <v-icon size="48" color="white">mdi-magnify-plus</v-icon>
    </div>

    <a class="media-item h-100 block" v-if="mediaType === 'image' && s3url" :data-src="s3url">
      <img :src="s3url" class="w-100 h-100 bg-grey-lighten-2" style="object-fit: cover;"></img>
    </a>

    <!-- Video preview -->
    <v-img v-if="mediaType === 'video'" :src="videoThumbnail" cover class="bg-grey-lighten-2 h-100">
      <div class="d-flex align-center justify-center fill-height">
        <v-btn icon="mdi-play-circle" variant="text" size="x-large" :class="['custom-play-icon', thumbnailBrightness > 128 ? 'dark-play-icon' : 'light-play-icon']"></v-btn>
      </div>
      <div v-if="mediaType === 'video' && durationFormatted" class="d-flex justify-center text-caption position-absolute bottom-0 right-0 text-white mb-2 mr-2 px-1 rounded-sm" style="background: rgba(0, 0, 0, 0.6);">
        {{ durationFormatted }}
      </div>
    </v-img>

    <!-- PDF preview -->
    <div v-else-if="mediaType === 'pdf'"
            class="d-flex align-center justify-center bg-grey-lighten-2 h-100 overflow-hidden">
      <v-icon size="64" color="red">mdi-file-pdf-box</v-icon>
    </div>

    <!-- Audio preview -->
    <div v-else-if="mediaType === 'audio'" class="d-flex align-center justify-center bg-grey-lighten-2 h-100">
      <div class="d-flex align-center justify-center fill-height position-relative">
        <v-icon size="128" color="primary">mdi-music-box</v-icon>
        <v-btn
          icon="mdi-play-circle"
          variant="text"
          size="x-large"
          :class="['custom-play-icon', 'dark-play-icon']"
          class="position-absolute"
          style="top: 50%; left: 50%; transform: translate(-50%, -50%);"
        ></v-btn>
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
      videoDuration: null,
      videoThumbnail: null,
      translations: window.translations,
      thumbnailBrightness: 0,
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
    this.init();
  },
  methods: {
    init() {
      api.get(`/admin/api/media/${this.media.filename}`)
        .then(response => {
          this.s3url = response.data.url;
          this.media.s3url = response.data.url;
          if (this.mediaType === 'video') {
            this.getVideoDuration();
            this.generateVideoThumbnail();
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
    <v-card v-if="miniMode" style="width: min(200px,100%); height: fit-content;" class="border border-1 mx-2" :disabled="!s3url">
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
    <v-card v-else style="width: min(350px,100%); height: fit-content;" class="border border-1 mx-2" :disabled="!s3url">
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