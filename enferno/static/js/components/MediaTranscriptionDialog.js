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
    isTranscriptionEmpty() {
      return !this.transcriptionText || this.transcriptionText.trim() === '';
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
      return ['needs_review', 'needs_transcription', 'processed', 'manual'].includes(this.media?.ocr_status);
    },
    isProcessing() {
      return this.media?.ocr_status === 'processing';
    },
    isPending() {
      return this.media?.ocr_status === 'pending';
    },
    isFailed() {
      return this.media?.ocr_status === 'failed';
    },
    isCantRead() {
      return this.media?.ocr_status === 'cant_read';
    },
    isProcessed() {
      return ['processed', 'manual'].includes(this.media?.ocr_status);
    },
    progressBarTextProps() {
      const hasConfidence = this.media?.extraction?.confidence > 0;
      return {
        class: hasConfidence ? 'text-white' : '',
        style: { 
          textShadow: `1px 1px 4px rgba(0, 0, 0, ${hasConfidence ? 1 : 0})` 
        }
      }
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
            <!-- Left Side - Image Preview -->
            <template #left>
              <div class="d-flex flex-column py-4 pl-4 pr-2" style="height: 100%;">
                <v-card class="border-thin flex-1-1 d-flex flex-column">
                  <v-card-text class="pa-4 flex-1-1 d-flex flex-column">
                    <v-skeleton-loader
                      v-if="loading"
                      class="flex-1-1"
                    ></v-skeleton-loader>
                    
                    <inline-media-renderer
                        v-else
                        :media="mediaRendererData"
                        media-type="image"
                        :use-metadata="true"
                        :initial-rotation="media?.extraction?.orientation || 0"
                        hide-close
                        ref="inlineMediaRendererRef"
                        content-style="height: calc(100vh - 174px);"
                        @fullscreen="$refs.inlineMediaRendererRef?.$refs?.imageViewer?.requestFullscreen()"
                    ></inline-media-renderer>
                  </v-card-text>
                </v-card>
              </div>
            </template>

            <!-- Right Side - Info Panel -->
            <template #right>
              <div class="d-flex flex-column py-4 pl-2 pr-4" style="height: 100%;">
                <v-card class="border-thin flex-1-1 d-flex flex-column overflow-hidden">
                  <v-card-text class="flex-1-1 overflow-y-auto pa-4 d-flex flex-column">
                    <!-- Metadata Card -->
                    <v-card class="flex-0-0 mb-4">
                      <v-card-text class="d-flex ga-6">
                        <!-- Bulletin Info -->
                        <div class="flex-0-0">
                          <div class="text-subtitle-2">{{ translations.bulletin_ }}</div>
                          <v-skeleton-loader
                            v-if="loading"
                            width="75"
                            height="20"
                          ></v-skeleton-loader>
                          <v-btn
                            v-else
                            density="compact"
                            color="primary"
                            variant="text"
                            :href="'/admin/bulletins/' + media.bulletin.id"
                            target="_blank"
                            class="px-1"
                          >
                            #{{ media.bulletin.id }}
                            <v-icon size="small" class="ml-1">mdi-open-in-new</v-icon>
                          </v-btn>
                        </div>

                        <!-- Detected Language -->
                        <div v-if="media?.extraction?.language || loading || true" class="flex-0-0">
                          <div class="text-subtitle-2">{{ translations.language_ }}</div>
                          <v-skeleton-loader
                            v-if="loading"
                            width="75"
                            height="20"
                          ></v-skeleton-loader>
                          <v-chip
                            v-else
                            density="compact"
                            prepend-icon="mdi-translate"
                          >
                            {{ media?.extraction?.language?.toUpperCase() }}
                          </v-chip>
                        </div>

                        <!-- Confidence -->
                        <div v-if="media?.extraction || loading" class="flex-1-1">
                          <div class="text-subtitle-2 mb-1 d-flex justify-space-between">
                            {{ translations.confidenceLevel_ }}
                            <span v-if="!loading" class="text-caption text-medium-emphasis">
                              {{ getConfidenceLabel(media?.extraction?.confidence) }}
                            </span>
                          </div>
                          
                          <v-skeleton-loader
                            v-if="loading"
                            width="100%"
                            height="16"
                          ></v-skeleton-loader>
                          
                          <v-progress-linear
                              v-else
                              :model-value="media?.extraction?.confidence"
                              :color="getConfidenceColor(media?.extraction?.confidence)"
                              height="16"
                              rounded
                          >
                            <template v-slot:default>
                              <strong v-bind="progressBarTextProps">{{ Math.round(media?.extraction?.confidence) }}</strong>
                            </template>
                          </v-progress-linear>
                        </div>
                      </v-card-text>
                    </v-card>

                    <!-- Alert for cant_read status -->
                    <v-alert
                      v-if="isCantRead"
                      color="brown"
                      variant="tonal"
                      density="compact"
                      icon="mdi-eye-off-outline"
                      class="mb-3 flex-0-0"
                      :title="translations.cannotRead_"
                    >
                      <template v-slot:text>
                        <div>{{ translations.thisMediaHasBeenMarkedAsUnreadableByAReviewer_ }}</div>
                        <div v-if="media?.extraction?.reviewed_at || media?.extraction?.reviewed_by" class="text-caption mt-1 text-medium-emphasis">
                          <template v-if="media?.extraction?.reviewed_by">
                            Reviewer ID: {{ media.extraction.reviewed_by }}
                          </template>
                          <template v-if="media?.extraction?.reviewed_at">
                            {{ media.extraction.reviewed_by ? ' • ' : '' }}{{ $root.formatDate(media.extraction.reviewed_at) }}
                          </template>
                        </div>
                      </template>
                    </v-alert>

                    <!-- Alert for manually transcribed status -->
                    <v-alert
                      v-else-if="media?.extraction?.manual"
                      color="indigo"
                      variant="tonal"
                      density="compact"
                      icon="mdi-account-edit-outline"
                      class="mb-3 flex-0-0"
                      :title="translations.manuallyTranscribed_"
                    >
                      <template v-slot:text>
                        <div>{{ translations.thisMediaWasManuallyTranscribedByAReviewer_ }}</div>
                        <div v-if="media?.extraction?.reviewed_at || media?.extraction?.reviewed_by" class="text-caption mt-1 text-medium-emphasis">
                          <template v-if="media?.extraction?.reviewed_by">
                            Reviewer ID: {{ media.extraction.reviewed_by }}
                          </template>
                          <template v-if="media?.extraction?.reviewed_at">
                            {{ media.extraction.reviewed_by ? ' • ' : '' }}{{ $root.formatDate(media.extraction.reviewed_at) }}
                          </template>
                        </div>
                      </template>
                    </v-alert>

                    <!-- Alert for processed (accepted) status -->
                    <v-alert
                      v-else-if="isProcessed && !media?.extraction?.manual"
                      color="green"
                      variant="tonal"
                      density="compact"
                      icon="mdi-check-circle-outline"
                      class="mb-3 flex-0-0"
                      :title="translations.processed_"
                    >
                      <template v-slot:text>
                        <div>{{ translations.thisMediaHasBeenReviewedAndAccepted_ }}</div>
                        <div v-if="media?.extraction?.reviewed_at || media?.extraction?.reviewed_by" class="text-caption mt-1 text-medium-emphasis">
                          <template v-if="media?.extraction?.reviewed_by">
                            Reviewer ID: {{ media.extraction.reviewed_by }}
                          </template>
                          <template v-if="media?.extraction?.reviewed_at">
                            {{ media.extraction.reviewed_by ? ' • ' : '' }}{{ $root.formatDate(media.extraction.reviewed_at) }}
                          </template>
                        </div>
                      </template>
                    </v-alert>

                    <!-- Alert for failed status -->
                    <v-alert
                      v-else-if="media?.ocr_status === 'failed'"
                      color="red"
                      variant="tonal"
                      density="compact"
                      icon="mdi-alert-circle-outline"
                      class="mb-3 flex-0-0"
                      :title="translations.failed_"
                    >
                      <template v-slot:text>
                        <div>{{ translations.ocrProcessingFailedForThisMedia_ }}</div>
                        <div v-if="media?.extraction?.created_at" class="text-caption mt-1 text-medium-emphasis">
                          {{ $root.formatDate(media.extraction.created_at) }}
                        </div>
                      </template>
                    </v-alert>

                    <!-- Extracted Text Section -->
                    <div class="flex-1-1 d-flex flex-column" style="min-height: 0;">
                      <div v-if="!(isPending || isFailed || isProcessing)" class="text-subtitle-2 mb-2 flex-0-0">
                        {{ translations.extractedText_ }} <span v-if="canEdit" class="text-error">*</span>
                      </div>
                      
                      <v-skeleton-loader
                        v-if="loading"
                        class="flex-1-1"
                      ></v-skeleton-loader>

                      <!-- Show message for processing items -->
                      <v-empty-state
                        v-else-if="isProcessing"
                        icon="mdi-cog-outline"
                        :text="translations.pleaseWaitWhileWeProcessThisMedia_"
                        :title="translations.processing_"
                      >
                        <template v-slot:actions>
                          <v-progress-circular
                            indeterminate
                            color="primary"
                            size="64"
                          ></v-progress-circular>
                        </template>
                      </v-empty-state>
                      
                      <!-- Show message for pending/failed items without extraction -->
                      <v-empty-state
                        v-else-if="isPending || isFailed"
                        :icon="isFailed ? 'mdi-alert-circle-outline' : 'mdi-text-recognition'"
                        :text="isFailed ? translations.clickRetryOCR_ : translations.clickRunOCR_"
                        :title="isFailed ? translations.ocrProcessingFailed_ : translations.ocrNotRunYet_"
                      >
                        <template v-slot:actions>
                          <v-tooltip location="top" :disabled="Boolean($root.visionApiKey)">
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
                                  {{ isFailed ? translations.retryOCR_ : translations.runOCR_ }}
                                </v-btn>
                              </div>
                            </template>
                            {{ translations.googleVisionApiHasNotBeenConfigured_ }}
                          </v-tooltip>
                        </template>
                      </v-empty-state>
                      
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
                  <v-card-actions v-if="canEdit" class="pa-4 pt-0">
                    <v-spacer></v-spacer>
                    <v-btn
                      v-if="!isProcessed"
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
                    <v-tooltip location="top" :disabled="!isTranscriptionEmpty">
                      <template v-slot:activator="{ props }">
                        <div v-bind="props">
                          <v-btn
                            color="primary"
                            variant="elevated"
                            size="large"
                            prepend-icon="mdi-check"
                            class="mx-1"
                            :disabled="loading || rejecting || isTranscriptionEmpty"
                            :loading="saving"
                            @click="isTranscriptionChanged ? markAsTranscribed({ media, text: transcriptionText }) : markAsAccepted(media)"
                          >
                            {{ isTranscriptionChanged || isProcessed ? translations.saveTranscription_ : translations.acceptTranscription_ }}
                          </v-btn>
                        </div>
                      </template>
                      {{ translations.transcriptionIsRequired_ }}
                    </v-tooltip>
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