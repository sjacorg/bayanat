const toolbarContent = `
  <v-toolbar density="compact" class="px-2">
    <div class="w-100 d-flex justify-space-between align-center">
      <div class="w-100 d-flex align-center">
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

        <v-spacer></v-spacer>

        <v-tooltip v-if="ocrButtonState?.visible" location="bottom">
          <template v-slot:activator="{ props }">
            <v-chip
              :color="$root.getStatusColor($root.getEffectiveStatus(media))"
              size="small"
              class="mr-1"
              v-bind="props"
            >
              <v-icon 
                :icon="$root.getStatusIcon($root.getEffectiveStatus(media))"
                :class="[{ 'mdi-spin': $root.getEffectiveStatus(media) === 'processing' }]"
              ></v-icon>
            </v-chip>
          </template>
          {{ translations.ocrStatus_ }}: {{ $root.getStatusText($root.getEffectiveStatus(media)) }}
        </v-tooltip>

        <v-tooltip v-if="ocrButtonState?.visible" location="bottom">
          <template v-slot:activator="{ props }">
            <div v-bind="props">
              <v-btn size="small" variant="text" icon="mdi-text-recognition" @click="$root.showOcrDialog(media.id)" :disabled="ocrButtonState.disabled"></v-btn>
            </div>
          </template>
          <span>{{ ocrButtonState.text }}</span>
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
      isCurrentUserAdmin: window.__isAdmin__ || false,
      translations: window.translations,
      iconMap: {
        image: 'mdi-image',
        video: 'mdi-video',
        pdf: 'mdi-file-pdf-box',
        audio: 'mdi-music-box',
        unknown: 'mdi-file-download'
      },
      ocrText: null,
      ocrLoading: false,
    };
  },
  computed: {
    mediaType() {
      return this.$root.getFileTypeFromMimeType(this.media?.fileType);
    },
    ocrButtonState() {
      // If no ocr mixin exit early
      if (!this.$root?.ocr) return;

      const isMediaSaved = !!this.media?.id;
      const isSupportedType = this.$root.selectableFileTypes.includes(this.mediaType);
      const visible = this.isCurrentUserAdmin;
      const disabled = !isSupportedType || !isMediaSaved;
      let text = '';

      if (!isSupportedType) {
        text = this.translations.ocrProcessingIsOnlyAvailableForTheFollowingFileTypes_(this.$root.selectableFileTypes);
      } else if (!isMediaSaved) {
        text = this.translations.transcriptionAvailableAfterSaving_;
      } else if (this.media?.extraction?.word_count) {
        text = this.translations.viewEditTranscription_;
      } else {
        text = this.translations.transcribe_;
      }

      return {
        text,
        visible,
        disabled
      }
    }
  },
  mounted() {
    this.init();
  },
  methods: {
    init() {
      // If s3url already exists on media, use it
      if (this.media.s3url) {
        this.s3url = this.media.s3url;
        this.$emit('ready');
        return;
      }

      // If we already have s3url in local state, don't refetch
      if (this.s3url) {
        this.$emit('ready');
        return;
      }

      // Fetch the s3url
      api.get(`/admin/api/media/${this.media.filename}`)
        .then(response => {
          this.s3url = response.data.url;
          // Store on media object for persistence across re-renders
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
    loadOcrText(e) {
      if (!e?.value || this.ocrText || this.ocrLoading) return;
      this.ocrLoading = true;
      api.get(`/admin/api/extraction/${this.media.extraction.id}`)
        .then(response => {
          this.ocrText = response.data.text;
        })
        .catch(() => this.$root.showSnack('Failed to load OCR text'))
        .finally(() => this.ocrLoading = false);
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

      <template v-if="media.extraction?.word_count">
        <v-divider></v-divider>
        <v-expansion-panels variant="accordion" flat>
          <v-expansion-panel @group:selected="loadOcrText">
            <v-expansion-panel-title class="py-1 text-caption" style="min-height: 36px;">
              <v-icon icon="mdi-text-recognition" size="small" class="mr-2"></v-icon>
              {{ translations.extractedText_ || 'Extracted Text' }}
              <v-chip size="x-small" class="ml-2" variant="text">{{ media.extraction.word_count }} {{ translations.words_ || 'words' }}</v-chip>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-progress-linear v-if="ocrLoading" indeterminate color="primary" class="mb-2"></v-progress-linear>
              <div v-else-if="ocrText" class="text-body-2" :dir="media.extraction.language === 'ar' ? 'rtl' : 'ltr'" style="max-height: 200px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6;">{{ ocrText }}</div>
              <div class="d-flex justify-end mt-1">
                <v-btn size="x-small" variant="text" icon="mdi-pencil" @click="$root.showOcrDialog(media.id)"></v-btn>
                <v-btn size="x-small" variant="text" icon="mdi-content-copy" @click="copyToClipboard(ocrText)" :disabled="!ocrText"></v-btn>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </template>

      <v-divider></v-divider>
      <v-card-actions class="justify-end d-flex py-0" style="min-height: 45px;">
        <v-spacer></v-spacer>
        <slot name="actions"></slot>
      </v-card-actions>
    </v-card>
  `
});