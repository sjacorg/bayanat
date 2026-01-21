const MediaTranscriptionDialog = Vue.defineComponent({
  props: {
    open: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    media: { type: Object, default: () => ({}) },
  },
  emits: ['update:open', 'rejected', 'accepted', 'transcribed'],
  data() {
    return {
      translations: window.translations,
      transcriptionText: this.media?.text || '',
      confidenceLevels: {
        high: 85,
        medium: 70,
      },
    };
  },
  computed: {
    isTranscriptionChanged() {
      return this.transcriptionText !== this.media?.extraction?.text;
    },
  },
  methods: {
    closeDialog() {
      this.$emit('update:open', false);
    },
    getConfidenceColor(confidence) {
      if (confidence >= this.confidenceLevels.high) return 'success';
      if (confidence >= this.confidenceLevels.medium) return 'warning';
      return 'error';
    },
    getConfidenceLabel(confidence) {
      if (confidence >= this.confidenceLevels.high) return this.translations.high_;
      if (confidence >= this.confidenceLevels.medium) return this.translations.medium_;
      return this.translations.low_;
    },
    isRTL(text) {
      if (!text) return false;
      // Check if first character is Arabic
      const arabicRegex = /[\u0600-\u06FF]/;
      return arabicRegex.test(text.charAt(0));
    },
  },
  watch: {
    media: {
      immediate: true,
      handler(newMedia) {
        this.transcriptionText = newMedia?.extraction?.text || '';
      },
    },
  },

  template: `
    <v-dialog
        v-if="open"
        :modelValue="open"
        fullscreen
        persistent
        no-click-animation
    >
      <v-toolbar color="dark-primary">
        <v-toolbar-title>{{ translations.transcriptionReview_ }}</v-toolbar-title>
        <v-spacer></v-spacer>

        <template #append>
          <v-btn icon="mdi-close" @click="closeDialog()"></v-btn>
        </template>
      </v-toolbar>
      <v-card v-if="media && !loading" height="calc(100vh - 64px)">
        <v-card-text class="overflow-y-auto">
          <v-row>
            <!-- Left Side - Image Preview -->
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="image-preview-card border-thin">
                  <v-card-text class="pa-0">
                      <div class="text-center pa-4">
                          <inline-media-renderer
                              :media="{ 
                                  thumbnail_url: media.thumbnail_url, 
                                  s3url: media.media_url,
                                  title: media.title,
                                  id: media.id 
                              }"
                              media-type="image"
                              :use-metadata="true"
                              hide-close
                              ref="inlineMediaRendererRef"
                              class="mb-4"
                              content-style="height: calc(100vh - 450px);"
                              @fullscreen="$refs.inlineMediaRendererRef?.$refs?.imageViewer?.requestFullscreen()"
                          ></inline-media-renderer>
                      </div>
                  </v-card-text>
              </v-card>
            </v-col>

            <!-- Right Side - Info Panel -->
            <v-col cols="12" md="6">
              <v-card variant="outlined" class="border-thin">
                  <v-card-text>
                      <!-- Bulletin Info -->
                      <div class="mb-4">
                          <v-btn
                              variant="tonal"
                              prepend-icon="mdi-file-document"
                              target="_blank"
                              :href="'/admin/bulletins/' + media.bulletin.id"
                              block
                          >
                              {{ translations.bulletin_ }} #{{ media.bulletin.id }}
                          </v-btn>
                      </div>

                      <v-divider class="my-4"></v-divider>

                      <!-- Confidence -->
                      <div v-if="media?.extraction?.confidence" class="mb-4">
                          <div class="text-subtitle-2 mb-2">Confidence</div>
                          <v-progress-linear
                              :model-value="media?.extraction?.confidence"
                              :color="getConfidenceColor(media?.extraction?.confidence)"
                              height="20"
                              rounded
                          >
                              <template v-slot:default>
                                  <strong>{{ Math.round(media?.extraction?.confidence) }}</strong>
                              </template>
                          </v-progress-linear>
                          <div class="text-caption text-medium-emphasis mt-1">
                              {{ getConfidenceLabel(media?.extraction?.confidence) }}
                          </div>
                      </div>
                      <v-divider v-if="media?.extraction?.confidence" class="my-4"></v-divider>

                      <!-- Extracted Text -->
                      <div>
                          <div class="text-subtitle-2 mb-2">Extracted Text</div>
                          <v-textarea
                              v-model="transcriptionText"
                              variant="outlined"
                              no-resize
                              placeholder="{{ translations.typeWhatYouSeeInMediaHere_ }}"
                              rows="12"
                              :dir="isRTL(transcriptionText) ? 'rtl' : 'ltr'"
                          ></v-textarea>
                      </div>
                  </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <v-row class="mt-4">
            <v-col class="text-center">
              <v-btn
                color="success"
                variant="elevated"
                size="large"
                prepend-icon="mdi-check"
                class="mx-2"
                @click="isTranscriptionChanged ? $emit('transcribed', { media, text: transcriptionText }) : $emit('accepted', media)"
              >
                {{ translations.saveTranscription_ }}
              </v-btn>

              <v-btn
                color="error"
                variant="elevated"
                size="large"
                prepend-icon="mdi-close-circle"
                class="mx-2"
                @click="$emit('rejected', media)"
              >
                {{ translations.cantRead_ }}
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
      <v-card v-else class="pa-8">
        <v-card-text class="text-center">loading</v-card-text>
      </v-card>
    </v-dialog>
    `,
});
