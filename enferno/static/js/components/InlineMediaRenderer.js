const InlineMediaRenderer = Vue.defineComponent({
    props: {
      rendererId: {
        type: String,
      },
      media: {
        type: Object,
      },
      useMetadata: {
        type: Boolean,
      },
      mediaType: {
        type: String,
      },
      contentStyle: {
        type: String,
        default: 'height: 450px;'
      },
      hideClose: {
        type: Boolean,
        default: false
      },
      initialOrientation: {
        type: Number,
        default: 0,
      },
    },
    emits: ['ready', 'fullscreen', 'close', 'orientation-changed'],
    data: () => ({
      translations: window.translations,
      iconMap: {
        image: 'mdi-image',
        video: 'mdi-video',
        pdf: 'mdi-file-pdf-box',
        audio: 'mdi-music-box',
        unknown: 'mdi-file-download'
      },
    }),
    methods: {
      emitReady() {
        this.$nextTick(() => {
          this.$emit('ready', {
            rendererId: this.rendererId,
            playerContainer:  this.$refs.playerContainer ?? null,
            requestFullscreen: this.requestFullscreen,
            scrollIntoView: (options) => {
              this.$refs.inlineMediaRenderer?.scrollIntoView?.(options);
            }
          });
        });
      },
      requestFullscreen() {
        if (this.mediaType === 'image') {
          this.$refs.imageViewer?.requestFullscreen?.();
        }

        if (this.mediaType === 'pdf') {
          this.$refs.pdfViewer?.requestFullscreen?.();
        }
      }
    },
    watch: {
      media: {
        immediate: true,
        handler(nextMedia) {
          if (nextMedia) this.emitReady();
        },
      },
    },
    template: `
      <div ref="inlineMediaRenderer" v-if="media">
        <v-toolbar density="compact" class="px-2">
          <div v-if="useMetadata" class="w-100 d-flex justify-space-between align-center">
            <div class="d-flex align-center">
              <v-icon
                :icon="iconMap[mediaType]"
                :color="mediaType === 'pdf' ? 'red' : 'primary'"
              ></v-icon>
              <v-divider vertical class="mx-2"></v-divider>
              <v-chip prepend-icon="mdi-identifier" variant="text" class="font-weight-bold"
                >{{ media.id }}</v-chip
              >
              <v-divider vertical class="mx-2"></v-divider>
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-chip
                    prepend-icon="mdi-tag"
                    variant="plain"
                    v-if="media.category"
                    size="small"
                    v-bind="props"
                  >
                    {{ media.category.title }}
                  </v-chip>
                </template>
                <span>{{ translations.category_ }}</span>
              </v-tooltip>
              <uni-field
                class="text-truncate"
                :english="media.title || 'Untitled'"
                :arabic="media.title_ar || ''"
                disable-spacing
              ></uni-field>
              <div v-if="media.filename" class="cursor-pointer">
                <v-list-item class="text-caption ml-1 py-0">
                  <template v-slot:prepend>
                    <v-tooltip location="bottom">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" icon="mdi-file-outline"></v-icon>
                      </template>
                      <div class="d-flex flex-column align-center">
                        <span><strong>{{ translations.filename_ }}</strong></span>
                      </div>
                    </v-tooltip>
                  </template>
                  <v-tooltip location="bottom">
                    <template v-slot:activator="{ props }">
                      <div v-bind="props" class="text-truncate">{{ media.filename }}</div>
                    </template>
                    {{ media.filename }}
                  </v-tooltip>
                </v-list-item>
              </div>
              <div v-if="media.etag" class="d-flex align-center cursor-pointer">
                <v-list-item class="text-caption ml-1 py-0 text-truncate">
                  <template v-slot:prepend>
                    <v-tooltip location="bottom">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" icon="mdi-fingerprint"></v-icon>
                      </template>
                      <div class="d-flex flex-column align-center">
                        <span><strong>{{ translations.etag_ }}</strong></span>
                      </div>
                    </v-tooltip>
                  </template>
                  <v-tooltip location="bottom">
                    <template v-slot:activator="{ props }">
                      <div v-bind="props" class="text-truncate">{{ media.etag }}</div>
                    </template>
                    {{ media.etag }}
                  </v-tooltip>
                </v-list-item>
              </div>
            </div>
          </div>
          <v-spacer></v-spacer>
          <v-btn @click="$emit('fullscreen')" icon="mdi-fullscreen" class="ml-2" size="small"></v-btn>
          <v-btn v-if="hideClose === false" icon="mdi-close" class="ml-2" size="small" @click="$emit('close')"></v-btn>
        </v-toolbar>

        <div :style="contentStyle">
          <div
            v-if="['video', 'audio'].includes(mediaType)"
            ref="playerContainer"
            class="h-100"
          ></div>
          <pdf-viewer ref="pdfViewer" v-if="mediaType === 'pdf'" :media="media" :media-type="mediaType" class="w-100 h-100"></pdf-viewer>
          <image-viewer ref="imageViewer" v-if="mediaType === 'image'" :initial-orientation="initialOrientation" :media="media" :media-type="mediaType" class="h-100" @orientation-changed="$emit('orientation-changed', $event)"></image-viewer>

          <!-- Fallback for unknown file types -->
          <div v-if="mediaType === 'unknown'" class="h-100 d-flex flex-column align-center justify-center bg-grey-lighten-2">
            <v-icon size="64" color="grey">mdi-file-download</v-icon>
            <div class="text-h6 mt-4 text-medium-emphasis">{{ translations.previewNotAvailable_ }}</div>
            <div class="text-caption text-medium-emphasis">{{ media.filename }}</div>
            <v-btn 
              color="primary" 
              variant="elevated" 
              class="mt-4"
              prepend-icon="mdi-download"
              :href="media.s3url"
              download
            >
              {{ translations.downloadFile_ }}
            </v-btn>
          </div>
        </div>
      </div>
    `,
  });
  