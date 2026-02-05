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
      translations: window.translations,
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
      return this.$root.getFileTypeFromMimeType(this.media?.fileType);
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
        })
        .catch(error => console.error('Error fetching media:', error))
        .finally(() => this.$emit('ready'));
    },
    handleMediaClick(payload) {
      // If media-thumbnail passes payload, use it; otherwise create it
      const clickPayload = payload || { media: this.media, mediaType: this.mediaType };
      
      switch (clickPayload.mediaType) {
        case 'pdf':
        case 'image':
        case 'video':
        case 'audio':
          this.$emit('media-click', clickPayload);
          break;
        default:
          this.downloadFile();
      }
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
          <div v-bind="previewHoverProps" class="preview-container position-relative"
              style="height: 120px;">
            <media-thumbnail
              :media="media"
              :s3url="s3url"
              :show-hover-icon="isHoveringPreview"
              clickable
              @click="handleMediaClick"
            />
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
          <div v-bind="previewHoverProps" class="preview-container position-relative"
              style="height: 160px;">
            <media-thumbnail
              :media="media"
              :s3url="s3url"
              :show-hover-icon="isHoveringPreview"
              clickable
              @click="handleMediaClick"
            />
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