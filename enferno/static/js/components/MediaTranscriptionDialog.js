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
      saving: false,
      rejecting: false,
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
    mediaRendererData() {
      return {
        thumbnail_url: this.media.thumbnail_url, 
        s3url: this.media.media_url,
        title: this.media.title,
        id: this.media.id 
      };
    },
    canEdit() {
      return ['needs_review', 'needs_transcription'].includes(this.media?.ocr_status);
    }
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
      const arabicRegex = /[\u0600-\u06FF]/;
      return arabicRegex.test(text.charAt(0));
    },
    markAsTranscribed({ media, text }) {
        if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
        this.saving = true;

        api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'transcribe', text }).then(response => {
            this.$root.showSnack(this.translations.mediaManuallyTranscribed_);
            this.$emit('transcribed', { media, text })
        }).finally(() => {
          this.saving = false;
        });
    },
    markAsAccepted(media) {
        if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
        this.saving = true;

        api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'accept' }).then(response => {
            this.$root.showSnack(this.translations.mediaMarkedAsAccepted_);
            this.$emit('accepted', media)
        }).finally(() => {
          this.saving = false;
        });
    },
    markAsCannotRead(media) {
        if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
        this.rejecting = true;

        api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'cant_read' }).then(response => {
            this.$root.showSnack(this.translations.mediaMarkedAsCannotRead_);
            this.$emit('rejected', media)
        }).finally(() => {
          this.rejecting = false;
        });
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
      <v-card class="d-flex flex-column" height="100vh">
        <v-toolbar color="dark-primary">
          <v-toolbar-title>{{ translations.transcriptionReview_ }}</v-toolbar-title>
          <v-spacer></v-spacer>
          <template #append>
            <v-btn icon="mdi-close" @click="closeDialog()"></v-btn>
          </template>
        </v-toolbar>

        <v-card-text class="flex-1-1 pa-0 overflow-y-auto">
          <split-view :left-width-percent="50">
            <template #left>
              <!-- Left Side - Image Preview -->
              <div class="d-flex flex-column py-4 pl-4 pr-2" style="height: 100%;">
                <v-card variant="outlined" class="border-thin flex-1-1 d-flex flex-column">
                  <v-card-text class="pa-4 flex-1-1 d-flex flex-column">
                    <!-- Skeleton loader for image -->
                    <v-skeleton-loader
                      v-if="loading"
                      class="flex-1-1"
                    ></v-skeleton-loader>
                    
                    <inline-media-renderer
                        v-else
                        :media="mediaRendererData"
                        media-type="image"
                        :use-metadata="true"
                        hide-close
                        ref="inlineMediaRendererRef"
                        content-style="height: calc(100vh - 174px);"
                        @fullscreen="$refs.inlineMediaRendererRef?.$refs?.imageViewer?.requestFullscreen()"
                    ></inline-media-renderer>
                  </v-card-text>
                </v-card>
              </div>
            </template>
            <template #right>
              <!-- Right Side - Info Panel -->
              <div class="d-flex flex-column py-4 pl-2 pr-4" style="height: 100%;">
                <v-card variant="outlined" class="border-thin flex-1-1 d-flex flex-column overflow-hidden">
                  <v-card-text class="flex-1-1 overflow-y-auto pa-4 d-flex flex-column">
                    <!-- Bulletin Info -->
                    <div class="flex-0-0">
                      <v-skeleton-loader
                        v-if="loading"
                        width="100%"
                        height="36"
                      ></v-skeleton-loader>
                      
                      <v-btn
                          v-else
                          variant="tonal"
                          prepend-icon="mdi-file-document"
                          target="_blank"
                          :href="'/admin/bulletins/' + media.bulletin.id"
                          block
                      >
                          {{ translations.bulletin_ }} #{{ media.bulletin.id }}
                      </v-btn>
                    </div>

                    <v-divider class="my-4 flex-0-0"></v-divider>

                    <!-- Confidence -->
                    <div v-if="media?.extraction?.confidence || loading" class="flex-0-0">
                      <div class="text-subtitle-2 mb-2">Confidence</div>
                      
                      <v-skeleton-loader
                        v-if="loading"
                        width="100%"
                        height="44"
                      ></v-skeleton-loader>
                      
                      <template v-else>
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
                      </template>
                    </div>
                    <v-divider v-if="media?.extraction?.confidence || loading" class="my-4 flex-0-0"></v-divider>

                    <!-- Extracted Text - This takes remaining space -->
                    <div class="flex-1-1 d-flex flex-column" style="min-height: 0;">
                      <div class="text-subtitle-2 mb-2 flex-0-0">Extracted Text</div>
                      
                      <v-skeleton-loader
                        v-if="loading"
                        class="flex-1-1"
                      ></v-skeleton-loader>
                      
                      <v-textarea
                          v-else
                          v-model="transcriptionText"
                          variant="outlined"
                          no-resize
                          :readonly="!canEdit"
                          :placeholder="translations.typeWhatYouSeeInMediaHere_"
                          :dir="isRTL(transcriptionText) ? 'rtl' : 'ltr'"
                          class="flex-1-1"
                          hide-details
                      ></v-textarea>
                    </div>
                  </v-card-text>

                  <!-- Action Buttons - Fixed at bottom -->
                  <v-card-actions v-if="canEdit" class="pa-4 pt-0">
                    <v-spacer></v-spacer>
                    <v-btn
                      color="error"
                      variant="elevated"
                      size="large"
                      prepend-icon="mdi-close-circle"
                      class="mx-1"
                      :disabled="loading || saving"
                      :loading="rejecting"
                      @click="markAsCannotRead(media)"
                    >
                      {{ translations.cantRead_ }}
                    </v-btn>
                    <v-btn
                      :color="isTranscriptionChanged ? 'info' : 'success'"
                      variant="elevated"
                      size="large"
                      prepend-icon="mdi-check"
                      class="mx-1"
                      :disabled="loading || rejecting"
                      :loading="saving"
                      @click="isTranscriptionChanged ? markAsTranscribed({ media, text: transcriptionText }) : markAsAccepted(media)"
                    >
                      {{ isTranscriptionChanged ? translations.saveTranscription_ : translations.acceptTranscription_ }}
                    </v-btn>
                  </v-card-actions>
                </v-card>
              </div>
            </template>
          </split-view>
        </v-card-text>
      </v-card>
    </v-dialog>
    `,
});