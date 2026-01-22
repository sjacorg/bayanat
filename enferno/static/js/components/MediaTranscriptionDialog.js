const MediaTranscriptionDialog = Vue.defineComponent({
  props: {
    open: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    media: { type: Object, default: () => ({}) },
  },
  emits: ['update:open', 'rejected', 'accepted', 'transcribed', 'processed'],
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
    },
    isPending() {
      return ['pending', 'failed'].includes(this.media?.ocr_status);
    },
    isProcessed() {
      return this.media?.ocr_status === 'processed';
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
    runOCRProcess() {
      if (!this.media?.id) return;
      if (!this.$root.visionApiKey) return this.$root.showSnack(this.translations.googleVisionApiHasNotBeenConfigured_);
      
      this.saving = true;
      
      api.post(`/admin/api/ocr/process/${this.media.id}`)
        .then(response => {
          if (response.data.success) {
            this.$root.showSnack(this.translations.ocrProcessedSuccessfully_);
            this.$emit('processed', this.media);
          } else {
            this.$root.showSnack(response.data.error);
          }
        })
        .catch(error => {
          console.error('OCR process error:', error);
          this.$root.showSnack(this.translations.errorProcessingOCR_);
        })
        .finally(() => {
          this.saving = false;
        });
    },
    markAsTranscribed({ media, text }) {
      if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
      this.saving = true;

      api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'transcribe', text })
        .then(response => {
          this.$root.showSnack(this.translations.mediaManuallyTranscribed_);
          this.$emit('transcribed', { media, text });
        })
        .catch(error => {
          console.error('Transcribe error:', error);
          this.$root.showSnack(this.translations.errorSavingTranscription_ || 'Error saving transcription');
        })
        .finally(() => {
          this.saving = false;
        });
    },
    markAsAccepted(media) {
      if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
      this.saving = true;

      api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'accept' })
        .then(response => {
          this.$root.showSnack(this.translations.mediaMarkedAsAccepted_);
          this.$emit('accepted', media);
        })
        .catch(error => {
          console.error('Accept error:', error);
          this.$root.showSnack(this.translations.errorAcceptingTranscription_ || 'Error accepting transcription');
        })
        .finally(() => {
          this.saving = false;
        });
    },
    markAsCannotRead(media) {
      if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
      this.rejecting = true;

      api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'cant_read' })
        .then(response => {
          this.$root.showSnack(this.translations.mediaMarkedAsCannotRead_);
          this.$emit('rejected', media);
        })
        .catch(error => {
          console.error('Reject error:', error);
          this.$root.showSnack(this.translations.errorRejectingMedia_ || 'Error rejecting media');
        })
        .finally(() => {
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
                    <div class="flex-0-0 d-flex align-center ga-6">
                      <!-- Bulletin Info -->
                      <div class="flex-0-0">
                        <v-skeleton-loader
                          v-if="loading"
                          width="175"
                          height="36"
                        ></v-skeleton-loader>

                        <a
                          v-else
                          class="mx-2 text-decoration-underline"
                          :href="'/admin/bulletins/' + media.bulletin.id"
                          target="_blank"
                        >
                            {{ translations.previewBulletin_ }} #{{ media.bulletin.id }}
                            <v-icon size="small" class="ml-1">mdi-open-in-new</v-icon>
                        </a>
                      </div>

                      <!-- Confidence -->
                      <div v-if="media?.extraction || loading" class="flex-1-1">
                        <div class="text-subtitle-2 mb-2">{{ translations.confidence_ }}</div>
                        
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
                    </div>
                    <v-divider class="my-4 flex-0-0"></v-divider>

                    <!-- Extracted Text - This takes remaining space -->
                    <div class="flex-1-1 d-flex flex-column" style="min-height: 0;">
                      <div v-if="!isPending" class="text-subtitle-2 mb-2 flex-0-0">
                        {{ translations.extractedText_ }}
                      </div>
                      
                      <v-skeleton-loader
                        v-if="loading"
                        class="flex-1-1"
                      ></v-skeleton-loader>
                      
                      <!-- Show message for pending items -->
                      <v-empty-state
                        v-else-if="isPending"
                        icon="mdi-text-recognition"
                        :text="translations.clickRunOCR_"
                        :title="translations.ocrNotRunYet_"
                      ></v-empty-state>
                      
                      <!-- Show textarea for items with extraction -->
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
                  <v-card-actions class="pa-4 pt-0">
                    <v-spacer></v-spacer>
                    
                    <!-- Pending/Failed State - Show "Run OCR" button -->
                    <template v-if="isPending">
                      <v-tooltip location="top">
                        <template v-slot:activator="{ props }">
                          <div v-bind="props">
                            <v-btn
                              color="primary"
                              variant="elevated"
                              size="large"
                              prepend-icon="mdi-text-recognition"
                              :disabled="loading || !$root.visionApiKey"
                              :loading="saving"
                              @click="runOCRProcess()"
                            >
                              {{ translations.runOCR_ }}
                            </v-btn>
                          </div>
                        </template>
                          {{ translations.googleVisionApiHasNotBeenConfigured_ }}
                      </v-tooltip>
                    </template>
                    
                    <!-- Needs Review/Transcription State - Show edit buttons -->
                    <template v-else-if="canEdit">
                      <v-btn
                        variant="tonal"
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
                        :color="isTranscriptionChanged ? 'info' : 'primary'"
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
                    </template>
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