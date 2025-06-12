const MediaCard = Vue.defineComponent({
  props: {
    media: {
      type: Object,
      required: true
    }
  },
  emits: ['video-click', 'audio-click', 'ready'],
  data() {
    return {
      s3url: '',
      videoDuration: null,
      videoThumbnail: null,
      translations: window.translations,
      thumbnailBrightness: 0,
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
    iconMap() {
      return {
        image: 'mdi-image',
        video: 'mdi-video',
        pdf: 'mdi-file-pdf-box',
        audio: 'mdi-music-box',
        unknown: 'mdi-file-download'
      };
    },
    durationFormatted() {
      return this.videoDuration ? this.formatDuration(this.videoDuration) : 'N/A';
    },
    actionTooltip() {
      switch (this.mediaType) {
        case 'image': return this.translations.image_preview_;
        case 'video': return this.translations.video_preview_;
        case 'pdf': return this.translations.pdf_preview_;
        case 'audio': return this.translations.audio_preview_;
        default: return this.translations.file_preview_;
      }
    }
  },
  mounted() {
    this.init();
  },
  methods: {
    init() {
      axios.get(`/admin/api/media/${this.media.filename}`)
        .then(response => {
          this.s3url = response.data;
          this.media.s3url = response.data;
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
          this.$root.$refs.pdfViewer.openPDF(this.s3url);
          break;
        case 'image':
          this.$refs.thumbnailRef?.click()
          break;
        case 'video':
          this.$emit('video-click', this.media);
          break;
        case 'audio':
          this.$emit('audio-click', this.media);
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
    }
  },
  template: /*html*/`
    <v-card style="width:min(350px,100%)"  class="border border-1 mx-2" :disabled="!s3url">
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
          <div class="d-flex align-center">
            <slot name="top-actions" :media="media" :mediaType="mediaType"></slot>
            <v-btn size="small" variant="text" icon="mdi-magnify-expand" @click="handleMediaClick"></v-btn> 
          </div>
        </div>

      </v-toolbar>
      <v-divider></v-divider>
      <v-sheet>
        <uni-field :english="media.title || 'Untitled'" :arabic="media.title_ar || ''"/>
      </v-sheet>
      <v-divider></v-divider>


      <v-card-text class="text-center pa-0">
        <v-hover v-slot="{ isHovering, props }">
          <div v-bind="props" @click="handleMediaClick" class="preview-container"
              style="height: 180px; cursor: pointer;">
            <!-- Image preview -->
            <a v-if="mediaType === 'image'" ref="thumbnailRef" :href="s3url" target="_blank">
              <v-img :src="s3url" height="180" cover class="bg-grey-lighten-2">
                <v-expand-transition>  
                  <div v-if="isHovering" style="height: 100%;" class="d-flex align-center justify-center transition-fast-in-fast-out bg-grey-darken-2 v-card--reveal text-h2">
                    <v-icon size="48" color="white">mdi-magnify-plus</v-icon>
                  </div>
                </v-expand-transition>
              </v-img>
            </a>

            <!-- Video preview -->
            <v-img v-else-if="mediaType === 'video'" :src="videoThumbnail" height="180" cover class="bg-grey-lighten-2">
              <div class="d-flex align-center justify-center fill-height">
                <v-btn icon="mdi-play-circle" variant="text" size="x-large" :class="['custom-play-icon', thumbnailBrightness > 128 ? 'dark-play-icon' : 'light-play-icon']"></v-btn>
              </div>
            </v-img>

            <!-- PDF preview -->
            <v-card v-else-if="mediaType === 'pdf'" height="180"
                    class="d-flex align-center justify-center bg-grey-lighten-2">
              <v-icon size="64" color="red">mdi-file-pdf-box</v-icon>
            </v-card>

            <!-- Audio preview -->
            <v-card v-else-if="mediaType === 'audio'" height="180" class="d-flex align-center justify-center bg-grey-lighten-2">
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
            </v-card>

            <!-- Other file types preview -->
            <v-card v-else height="180" class="d-flex align-center justify-center bg-grey-lighten-2">
              <v-icon size="64">mdi-file-download</v-icon>
            </v-card>
          </div>
        </v-hover>
      </v-card-text>

      <v-card-text class="px-2">
        
        <div class=" cursor-pointer" @click="copyToClipboard(media.filename)">
          <v-list-item class="text-caption ml-1">
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
            {{ media.filename }}
          </v-list-item>
        </div>
        <div class="d-flex align-center  cursor-pointer" @click="copyToClipboard(media.etag)">
          <v-list-item class="text-caption ml-1">
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
            {{ media.etag }}
          </v-list-item>
        </div>

        <div v-if="mediaType === 'video'" class="d-flex ">
          <v-list-item class="text-caption ml-1">
            <template v-slot:prepend>
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-icon v-bind="props" icon="mdi-timer-outline"></v-icon>
                </template>
                <span><strong>{{ translations.duration_ }}</strong></span>
              </v-tooltip>
            </template>
            {{ durationFormatted }}
          </v-list-item>

        </div>
      </v-card-text>
      
        
        <slot name="actions">
        </slot>

    </v-card>
  `
});