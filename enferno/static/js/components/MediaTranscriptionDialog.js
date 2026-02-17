const MediaTranscriptionDialog = Vue.defineComponent({
  props: {
    open: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    media: { type: Object, default: () => ({}) },
    hasVisionApiKey: { type: Boolean, default: false },
  },
  emits: ['update:open', 'rejected', 'transcribed', 'processed', 'orientation-saved'],
  data() {
    return {
      translations: window.translations,
      transcriptionText: '',
      editing: false,
      saving: false,
      rejecting: false,
      confidenceLevels: { high: 85, medium: 70 },
      translation: {
        loading: false,
        text: '',
        sourceLanguage: '',
        targetLanguage: this.getPreferredLanguage(),
        show: false,
      },
      orientation: {
        saving: false,
        orientationToSave: null,
        showSaveButton: false,
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
    hasText() {
      return !!this.media?.extraction?.text?.trim();
    },
    canEdit() {
      return ['processed', 'manual'].includes(this.media?.ocr_status);
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
    progressBarTextProps() {
      const hasConfidence = this.media?.extraction?.confidence > 0;
      return {
        class: hasConfidence ? 'text-white' : '',
        style: { textShadow: `1px 1px 4px rgba(0, 0, 0, ${hasConfidence ? 1 : 0})` }
      }
    },
    effectiveWordCount() {
      if (this.editing) return this.$root.countWords(this.transcriptionText);
      const apiCount = this.media?.extraction?.word_count;
      if (apiCount > 0) return apiCount;
      return this.$root.countWords(this.media?.extraction?.text);
    },
    isLowWordCount() {
      return this.effectiveWordCount > 0 && this.effectiveWordCount < this.$root.lowWordCount;
    },
    canTranslate() {
      return this.hasText && this.media?.extraction?.id;
    },
    revisionCount() {
      return this.media?.extraction?.history?.length || 0;
    },
  },
  methods: {
    enterEditMode() {
      this.transcriptionText = this.media?.extraction?.text || '';
      this.editing = true;
    },
    cancelEdit() {
      this.editing = false;
      this.transcriptionText = '';
    },
    saveRevision() {
      if (!this.media?.extraction) return;
      if (!this.transcriptionText?.trim()) return;
      this.saving = true;

      api.put(`/admin/api/extraction/${this.media.extraction.id}`, { action: 'transcribe', text: this.transcriptionText })
        .then(() => {
          this.$root.showSnack(this.translations.revisionSaved_ || 'Revision saved');
          this.editing = false;
          this.$emit('transcribed', { media: this.media, text: this.transcriptionText });
        })
        .catch(error => {
          console.error('Save revision error:', error);
        })
        .finally(() => {
          this.saving = false;
        });
    },
    markAsCannotRead(media) {
      if (!media?.extraction) return this.$root.showSnack(this.translations.noExtractionDataFoundForThisMedia_);
      this.rejecting = true;

      api.put(`/admin/api/extraction/${media.extraction.id}`, { action: 'cant_read' })
        .then(() => {
          this.$root.showSnack(this.translations.mediaMarkedAsCannotRead_);
          this.$emit('rejected', { media });
        })
        .catch(error => {
          console.error('Reject error:', error);
        })
        .finally(() => {
          this.rejecting = false;
        });
    },
    normalizeOrientation(newOrientation) {
      let normalized = newOrientation % 360;
      if (normalized < 0) normalized += 360;
      return Math.round(normalized / 90) * 90 % 360;
    },
    onOrientationChanged(newOrientation) {
      this.orientation.showSaveButton = true;
      this.orientation.orientationToSave = this.normalizeOrientation(newOrientation);
    },
    saveOrientation() {
      if (!this.media?.id) return;
      this.orientation.saving = true;

      api.put(`/admin/api/media/${this.media.id}/orientation`, { orientation: this.orientation.orientationToSave })
        .then(() => {
          this.$root.showSnack(this.translations.orientationSaved_);
          this.$emit('orientation-saved', { media: this.media, orientation: this.orientation.orientationToSave });
          this.orientation.showSaveButton = false;
        })
        .catch(error => {
          console.error('Orientation save error:', error);
        })
        .finally(() => {
          this.orientation.saving = false;
        });
    },
    closeDialog() {
      this.editing = false;
      this.$root.closeExpandedMedia('ocr-dialog');
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
    runOCRProcess() {
      if (!this.media?.id) return;
      if (!this.hasVisionApiKey) return this.$root.showSnack(this.translations.googleVisionApiHasNotBeenConfigured_);

      this.saving = true;

      api.post(`/admin/api/ocr/process/${this.media.id}`)
        .then(response => {
          if (response.data.success) {
            this.$root.showSnack(this.translations.ocrProcessedSuccessfully_);
            this.$emit('processed', { media: this.media });
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
    getPreferredLanguage() {
      return localStorage.getItem('ocr_translation_target_language') || 'en';
    },
    savePreferredLanguage(langCode) {
      localStorage.setItem('ocr_translation_target_language', langCode);
    },
    async translateText() {
      if (!this.canTranslate) return;
      this.translation.loading = true;
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
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text);
        this.$root?.showSnack?.(this.translations.copiedToClipboard_);
      } catch (err) {
        this.$root?.showSnack?.(this.translations.failedToCopyCoordinates_);
      }
    }
  },
  watch: {
    media: {
      immediate: true,
      handler(newMedia) {
        this.editing = false;
        this.transcriptionText = '';
        this.translation.show = false;
        this.translation.text = '';
        this.translation.sourceLanguage = '';
        this.orientation.saving = false;
        this.orientation.showSaveButton = false;

        if (newMedia) {
          this.$root.closeExpandedMedia('ocr-dialog');
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

                    <div v-else class="position-relative">
                      <div>
                        <inline-media-renderer
                          renderer-id="ocr-dialog"
                          :initial-orientation="media?.orientation || 0"
                          :media="$root.expandedByRenderer?.['ocr-dialog']?.media"
                          :media-type="fileTypeFromMedia"
                          @orientation-changed="onOrientationChanged"
                          @ready="$root.onMediaRendererReady"
                          @fullscreen="$root.handleFullscreen('ocr-dialog')"
                          content-style="height: calc(100vh - 174px);"
                          hide-close
                          :use-metadata="true"
                        ></inline-media-renderer>
                      </div>
                      <v-btn v-if="orientation.showSaveButton" @click="saveOrientation" prepend-icon="mdi-check" :loading="orientation.saving" class="ma-2 position-absolute right-0 bottom-0" color="primary" style="zIndex: 3002;">{{ translations.saveOrientation_ }}</v-btn>
                    </div>
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
                          <v-skeleton-loader v-if="loading" width="75" height="20"></v-skeleton-loader>
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
                          <div class="text-subtitle-2">{{ translations.sourceLanguage_ }}</div>
                          <v-skeleton-loader v-if="loading" width="75" height="20"></v-skeleton-loader>
                          <v-chip v-else density="compact" prepend-icon="mdi-translate">
                            {{ media?.extraction?.language?.toUpperCase() }}
                          </v-chip>
                        </div>

                        <!-- Word Count -->
                        <div v-if="media?.extraction || loading" class="flex-0-0">
                          <div class="text-subtitle-2">{{ translations.wordCount_ }}</div>
                          <v-skeleton-loader v-if="loading" width="75" height="20"></v-skeleton-loader>
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
                          <v-skeleton-loader v-if="loading" width="100%" height="16"></v-skeleton-loader>
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

                    <!-- Alert for low word count -->
                    <v-alert
                      v-if="isLowWordCount && !editing"
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
                      </template>
                    </v-alert>

                    <!-- Alert for failed status -->
                    <v-alert
                      v-else-if="isFailed"
                      color="red"
                      variant="tonal"
                      density="compact"
                      icon="mdi-alert-circle-outline"
                      class="mb-3 flex-0-0"
                      :title="translations.failed_"
                    >
                      <template v-slot:text>
                        <div>{{ translations.ocrProcessingFailedForThisMedia_ }}</div>
                      </template>
                    </v-alert>

                    <!-- Extracted Text Section -->
                    <div class="flex-1-1 d-flex flex-column" style="min-height: 0;">
                      <div v-if="hasText || editing" class="text-subtitle-2 mb-2 d-flex align-center">
                        {{ translations.extractedText_ }}
                        <v-chip v-if="editing" color="warning" size="x-small" variant="tonal" class="ml-2">{{ translations.editing_ || 'Editing' }}</v-chip>
                        <v-spacer></v-spacer>

                        <!-- Edit / Cancel button -->
                        <v-btn
                          v-if="canEdit && !editing"
                          prepend-icon="mdi-pencil"
                          variant="outlined"
                          class="border-thin mr-2"
                          @click="enterEditMode"
                        >{{ translations.edit_ || 'Edit' }}</v-btn>

                        <v-btn
                          v-if="editing"
                          variant="text"
                          class="mr-2"
                          @click="cancelEdit"
                        >{{ translations.cancel_ || 'Cancel' }}</v-btn>

                        <v-btn
                          v-if="hasVisionApiKey && !editing"
                          prepend-icon="mdi-translate"
                          variant="outlined"
                          :loading="translation.loading"
                          :disabled="loading || saving || translation.show || !canTranslate"
                          class="border-thin"
                          @click.stop="translateText"
                        >{{ translations.translate_ }}</v-btn>
                      </div>

                      <v-skeleton-loader v-if="loading" class="flex-1-1"></v-skeleton-loader>

                      <!-- No API key configured -->
                      <v-empty-state
                        v-if="!hasVisionApiKey && !hasText"
                        icon="mdi-alert-circle-outline"
                        :title="translations.apiNotConfigured_"
                        :text="translations.googleVisionApiHasNotBeenConfigured_"
                      ></v-empty-state>

                      <!-- Processing -->
                      <v-empty-state
                        v-else-if="isProcessing"
                        icon="mdi-cog-outline"
                        :text="translations.pleaseWaitWhileWeProcessThisMedia_"
                        :title="translations.processing_"
                      >
                        <template v-slot:actions>
                          <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
                        </template>
                      </v-empty-state>

                      <!-- Unsupported file type -->
                      <v-empty-state
                        v-else-if="!this.$root.selectableFileTypes.includes(fileTypeFromMedia)"
                        icon="mdi-alert-circle-outline"
                        :title="translations.fileTypeNotSupported_"
                        :text="translations.ocrProcessingIsOnlyAvailableForTheFollowingFileTypes_(this.$root.selectableFileTypes)"
                      ></v-empty-state>

                      <!-- Pending / Failed - run OCR -->
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

                      <!-- Text content area -->
                      <div v-else-if="hasText || editing" class="flex-1-1 d-flex ga-4" style="min-height: 0;">
                        <div class="position-relative h-100 w-100">
                          <!-- Edit mode: textarea -->
                          <v-textarea
                              v-if="editing"
                              v-model="transcriptionText"
                              variant="outlined"
                              no-resize
                              :placeholder="translations.typeWhatYouSeeInMediaHere_"
                              dir="auto"
                              class="h-100"
                              hide-details
                              autofocus
                          ></v-textarea>

                          <!-- View mode: read-only text -->
                          <div
                            v-else
                            class="h-100 overflow-y-auto text-body-1 pa-4 rounded border-thin"
                            dir="auto"
                            style="white-space: pre-wrap; line-height: 1.8;"
                          >{{ media?.extraction?.text }}</div>
                        </div>

                        <!-- Translation Result -->
                        <v-card
                          v-if="translation.show && !editing"
                          variant="outlined"
                          class="flex-1-1 d-flex flex-column w-100"
                          style="min-height: 0;"
                        >
                          <v-card-title class="d-flex align-center justify-space-between text-subtitle-2 py-2">
                            <v-select
                              v-model="translation.targetLanguage"
                              :items="availableLanguages"
                              item-title="name"
                              item-value="code"
                              density="compact"
                              hide-details
                              :disabled="loading || saving || translation.loading"
                              class="mr-4"
                              @update:model-value="translateText()"
                            ></v-select>

                            <div class="d-flex align-center ga-1">
                              <v-btn icon="mdi-content-copy" size="x-small" variant="text" @click="copyToClipboard(translation.text)"></v-btn>
                              <v-btn icon="mdi-close" size="x-small" variant="text" @click="closeTranslation"></v-btn>
                            </div>
                          </v-card-title>
                          <v-divider></v-divider>
                          <v-card-text class="flex-1-1 overflow-y-auto text-pre-wrap text-body-1" dir="auto">
                            {{ translation.text }}
                          </v-card-text>
                        </v-card>
                      </div>
                    </div>
                  </v-card-text>

                  <!-- Revisions -->
                  <v-expansion-panels v-if="revisionCount > 0" flat class="flex-0-0 mx-4 mb-2">
                    <v-expansion-panel>
                      <v-expansion-panel-title class="text-caption py-1" style="min-height: 36px;">
                        <v-icon icon="mdi-history" size="small" class="mr-2"></v-icon>
                        {{ translations.revisions_ || 'Revisions' }} ({{ revisionCount }})
                      </v-expansion-panel-title>
                      <v-expansion-panel-text>
                        <div v-for="(entry, idx) in [...media.extraction.history].reverse()" :key="idx" class="mb-2 text-caption">
                          <div class="d-flex align-center ga-2 text-medium-emphasis">
                            <v-icon icon="mdi-account" size="x-small"></v-icon>
                            <span>User #{{ entry.user_id }}</span>
                            <span>{{ $root.formatDate(entry.timestamp) }}</span>
                          </div>
                        </div>
                      </v-expansion-panel-text>
                    </v-expansion-panel>
                  </v-expansion-panels>

                  <!-- Action Buttons -->
                  <v-card-actions v-if="editing" class="pa-4 pt-0">
                    <v-btn
                      variant="tonal"
                      size="large"
                      prepend-icon="mdi-eye-off"
                      :disabled="saving"
                      :loading="rejecting"
                      @click="markAsCannotRead(media)"
                    >
                      {{ translations.cantRead_ }}
                    </v-btn>
                    <v-spacer></v-spacer>
                    <v-btn
                      variant="text"
                      size="large"
                      @click="cancelEdit"
                    >
                      {{ translations.cancel_ || 'Cancel' }}
                    </v-btn>
                    <v-btn
                      color="primary"
                      variant="elevated"
                      size="large"
                      prepend-icon="mdi-content-save"
                      :disabled="!transcriptionText?.trim() || rejecting"
                      :loading="saving"
                      @click="saveRevision"
                    >
                      {{ translations.saveRevision_ || 'Save Revision' }}
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
