const MediaTranscriptionDialog = Vue.defineComponent({
  props: {
    open: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    media: { type: Object, default: () => ({}) },
    hasVisionApiKey: { type: Boolean, default: false },
  },
  emits: ['update:open', 'rejected', 'accepted', 'transcribed', 'processed'],
  data() {
    return {
      translations: window.translations,
      transcriptionText: this.media?.extraction?.original_text || this.media?.extraction?.text || '',
      saving: false,
      rejecting: false,
      confidenceLevels: {
        high: 85,
        medium: 70,
      },
      // Translation feature
      translation: {
        loading: false,
        text: '',
        sourceLanguage: '',
        targetLanguage: this.getPreferredLanguage(),
        show: false,
      },
      availableLanguages: [
        { code: 'en', name: window.translations.english_ },
        { code: 'fr', name: window.translations.french_ },
        { code: 'de', name: window.translations.german_ },
        { code: 'nl', name: window.translations.dutch_ },
        { code: 'es', name: window.translations.spanish_ },
      ],
    };
  },
  computed: {
    isTranscriptionChanged() {
      return this.transcriptionText !== (this.media?.extraction?.original_text || this.media?.extraction?.text);
    },
    isTranscriptionEmpty() {
      return !this.transcriptionText || this.transcriptionText.trim() === '';
    },
    fileTypeFromMedia() {
      return this.$root.getFileTypeFromMimeType(this.media?.fileType);
    },
    mediaRendererData() {
      return {
        ...this.media,
        s3url: this.media?.media_url,
        title: this.media?.title,
        id: this.media?.id,
      };
    },
    needsReview() {
      return ['needs_review', 'needs_transcription'].includes(this.media?.ocr_status);
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
    },
    effectiveWordCount() {
      // If user is editing, count words in their text
      if (this.isTranscriptionChanged) {
        return this.$root.countWords(this.transcriptionText);
      }
      
      // Use API word count or fallback to counting the text
      const apiCount = this.media?.extraction?.word_count;
      if (apiCount > 0) {
        return apiCount;
      }
      
      // Count from text as fallback
      return this.$root.countWords(this.media?.extraction?.original_text || this.media?.extraction?.text);
    },
    isLowWordCount() {
      return this.effectiveWordCount > 0 && this.effectiveWordCount < this.$root.lowWordCount;
    },
    canTranslate() {
      return !this.isTranscriptionEmpty && this.media?.extraction?.id;
    },
  },
  methods: {
    closeDialog() {
      this.$root.closeExpandedMedia('ocr-dialog')
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
      if (!this.hasVisionApiKey) return this.$root.showSnack(this.translations.googleVisionApiHasNotBeenConfigured_);
      
      this.saving = true;
      
      api.post(`/admin/api/ocr/process/${this.media.id}`)
        .then(response => {
          if (response.data.success) {
            this.$root.showSnack(this.translations.ocrProcessedSuccessfully_);
            this.$emit('processed', { media: this.media});
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
          this.$emit('accepted', { media });
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
          this.$emit('rejected', { media});
        })
        .catch(error => {
          console.error('Reject error:', error);
        })
        .finally(() => {
          this.rejecting = false;
        });
    },
    // Translation methods
    getLanguageName(langCode) {
      const lang = this.availableLanguages.find(l => l.code === langCode);
      return lang ? lang.name : langCode.toUpperCase();
    },
    getPreferredLanguage() {
      return localStorage.getItem('ocr_translation_target_language') || 'en';
    },
    savePreferredLanguage(langCode) {
      localStorage.setItem('ocr_translation_target_language', langCode);
    },
    async translateText() {
      if (!this.canTranslate) return;
      
      this.translation.loading = true;
      
      // Save user's language preference
      this.savePreferredLanguage(this.translation.targetLanguage);
      
      try {
        const response = await api.post(`/admin/api/extraction/${this.media.extraction.id}/translate`, {
          target_language: this.translation.targetLanguage
        });
        
        if (response.data) {
          this.translation.show = true;
          this.translation.text = response.data.translated_text;
          this.translation.sourceLanguage = response.data.source_language;
          this.$root.showSnack(this.translations.translationCompleted_);
        }
      } catch (error) {
        console.error('Translation error:', error);
        this.translation.show = false;
      } finally {
        this.translation.loading = false;
      }
    },
    closeTranslation() {
      this.translation.show = false;
      this.translation.text = '';
      this.translation.sourceLanguage = '';
    },
  },
  watch: {
    media: {
      immediate: true,
      handler(newMedia) {
        this.transcriptionText = newMedia?.extraction?.original_text || newMedia?.extraction?.text || '';
        // Reset translation when media changes
        this.translation.show = false;
        this.translation.text = '';
        this.translation.sourceLanguage = '';
        
        if (newMedia) {
          this.$root.closeExpandedMedia('ocr-dialog')
          this.$root.handleExpandedMedia({ rendererId: 'ocr-dialog', media: this.mediaRendererData, mediaType: this.fileTypeFromMedia });
        }
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
                      renderer-id="ocr-dialog"
                      :initial-rotation="media?.extraction?.orientation || 0"
                      :media="$root.expandedByRenderer?.['ocr-dialog']?.media"
                      :media-type="fileTypeFromMedia"
                      @ready="$root.onMediaRendererReady"
                      @fullscreen="$root.handleFullscreen('ocr-dialog')""
                      content-style="height: calc(100vh - 174px);"
                      hide-close
                      :use-metadata="true"
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
                            v-else-if="media?.bulletin"
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
                        <div v-if="media?.extraction?.language || loading" class="flex-0-0">
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

                        <!-- Word Count -->
                        <div v-if="media?.extraction || loading" class="flex-0-0">
                          <div class="text-subtitle-2">{{ translations.wordCount_ }}</div>
                          <v-skeleton-loader
                            v-if="loading"
                            width="75"
                            height="20"
                          ></v-skeleton-loader>
                          <v-chip
                            v-else
                            density="compact"
                            prepend-icon="mdi-format-letter-case"
                            :color="isLowWordCount ? 'warning' : 'default'"
                            :variant="isLowWordCount ? 'tonal' : 'flat'"
                          >
                            {{ effectiveWordCount }}
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
                              <strong v-bind="progressBarTextProps">{{ Math.round(media?.extraction?.confidence ?? 0) }}</strong>
                            </template>
                          </v-progress-linear>
                        </div>
                      </v-card-text>
                    </v-card>

                    <!-- Alert for low word count - only show when viewing, not editing -->
                    <v-alert
                      v-if="isLowWordCount && !isTranscriptionChanged && needsReview"
                      color="info"
                      variant="tonal"
                      density="compact"
                      icon="mdi-information-outline"
                      class="mb-3 flex-0-0"
                      :title="translations.reviewRecommended_"
                    >
                      <template v-slot:text>
                        <div>{{ translations.thisDocumentHasOnlyXWords_.replace('{count}', effectiveWordCount) }}</div>
                        <div>{{ translations.considerCheckingForHandwrittenContent_ }}</div>
                      </template>
                    </v-alert>

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
                      
                      <!-- Show message for not supported file types -->
                      <v-empty-state
                        v-else-if="!this.$root.selectableFileTypes.includes(fileTypeFromMedia)"
                        icon="mdi-alert-circle-outline"
                        :title="translations.fileTypeNotSupported_"
                        :text="translations.ocrProcessingIsOnlyAvailableForTheFollowingFileTypes_(this.$root.selectableFileTypes)"
                      ></v-empty-state>

                      <!-- Show message for pending/failed items without extraction -->
                      <v-empty-state
                        v-else-if="isPending || isFailed"
                        :icon="isFailed ? 'mdi-alert-circle-outline' : 'mdi-text-recognition'"
                        :text="isFailed ? translations.clickRetryOCR_ : translations.clickRunOCR_"
                        :title="isFailed ? translations.ocrProcessingFailed_ : translations.ocrNotRunYet_"
                      >
                        <template v-slot:actions>
                          <v-tooltip location="top" :disabled="Boolean(hasVisionApiKey)">
                            <template v-slot:activator="{ props }">
                              <div v-bind="props">
                                <v-btn
                                  color="primary"
                                  variant="elevated"
                                  size="large"
                                  prepend-icon="mdi-text-recognition"
                                  :disabled="loading || !hasVisionApiKey"
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
                      <div v-else class="flex-1-1 d-flex flex-column" style="min-height: 0;">
                        <div class="position-relative" :class="translation.show ? 'flex-0-0 mb-3' : 'flex-1-1'">
                          <v-textarea
                              v-model="transcriptionText"
                              variant="outlined"
                              no-resize
                              :readonly="!canEdit"
                              :placeholder="translations.typeWhatYouSeeInMediaHere_"
                              dir="auto"
                              :class="translation.show ? '' : 'h-100'"
                              hide-details
                          >
                            <template v-slot:append-inner v-if="canTranslate">
                              <v-tooltip location="top">
                                <template v-slot:activator="{ props }">
                                  <div v-bind="props">
                                    <v-btn
                                      icon="mdi-translate"
                                      size="small"
                                      variant="text"
                                      :loading="translation.loading"
                                      :disabled="loading || saving"
                                      @click.stop="translateText"
                                    ></v-btn>
                                  </div>
                                </template>
                                {{ translations.translateToLanguage_(getLanguageName(translation.targetLanguage)) }}
                              </v-tooltip>
                              
                              <v-menu location="bottom end">
                                <template v-slot:activator="{ props: menuProps }">
                                  <v-tooltip location="top">
                                    <template v-slot:activator="{ props: tooltipProps }">
                                      <div v-bind="{ ...menuProps, ...tooltipProps }">
                                        <v-btn
                                          icon="mdi-chevron-down"
                                          size="small"
                                          variant="text"
                                          :disabled="loading || saving || translation.loading"
                                        ></v-btn>
                                      </div>
                                    </template>
                                    {{ translations.changeLanguage_ }}
                                  </v-tooltip>
                                </template>
                                <v-list density="compact">
                                  <v-list-item
                                    v-for="lang in availableLanguages"
                                    :key="lang.code"
                                    :value="lang.code"
                                    :active="translation.targetLanguage === lang.code"
                                    @click="translation.targetLanguage = lang.code; savePreferredLanguage(lang.code)"
                                  >
                                    <v-list-item-title>{{ lang.name }}</v-list-item-title>
                                  </v-list-item>
                                </v-list>
                              </v-menu>
                            </template>
                          </v-textarea>
                        </div>
                        
                        <!-- Translation Result -->
                        <v-card
                          v-if="translation.show"
                          variant="outlined"
                          class="flex-1-1 d-flex flex-column"
                          style="min-height: 0;"
                        >
                          <v-card-title class="d-flex align-center justify-space-between text-subtitle-2 py-2">
                            <div class="d-flex align-center ga-2">
                              <v-icon size="small">mdi-translate</v-icon>
                              {{ translations.translation_ }}
                              <v-chip
                                v-if="translation.sourceLanguage"
                                density="compact"
                                size="x-small"
                              >
                                {{ translation.sourceLanguage?.toUpperCase() }} → {{ translation.targetLanguage?.toUpperCase() }}
                              </v-chip>
                            </div>
                            <v-btn
                              icon="mdi-close"
                              size="x-small"
                              variant="text"
                              @click="closeTranslation"
                            ></v-btn>
                          </v-card-title>
                          <v-divider></v-divider>
                          <v-card-text class="flex-1-1 overflow-y-auto text-pre-wrap" dir="auto">
                            {{ translation.text }}
                          </v-card-text>
                        </v-card>
                      </div>
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