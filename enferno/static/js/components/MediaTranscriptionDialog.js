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
    };
  },
  computed: {
    isTranscriptionChanged() {
      return this.transcriptionText !== this.media?.text;
    }
  },
  methods: {
    closeDialog() {
      this.$emit('update:open', false);
    },
    getConfidenceColor(confidence) {
      if (confidence >= 85) return 'success';
      if (confidence >= 70) return 'warning';
      return 'error';
    },
    getConfidenceLabel(confidence) {
      if (confidence >= 85) return "{{_('High')}}";
      if (confidence >= 70) return "{{_('Medium')}}";
      return "{{_('Low')}}";
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
        this.transcriptionText = newMedia?.text || '';
      },
    },
  },

  template: `
    <v-dialog
        v-if="open"
        :modelValue="open"
        fullscreen
    >
      <v-toolbar color="dark-primary">
        <v-toolbar-title>OCR Transcription</v-toolbar-title>
        <v-spacer></v-spacer>

        <template #append>
          <v-btn icon="mdi-close" @click="closeDialog()"></v-btn>
        </template>
      </v-toolbar>
      <v-card v-if="media && !loading" height="calc(100vh - 64px)">
        <v-form>
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
                                        s3url: media.media_url 
                                    }"
                                    media-type="image"
                                    :use-metadata="false"
                                    hide-close
                                    ref="inlineMediaRendererRef"
                                    class="mb-4"
                                    content-style="height: calc(100vh - 450px);"
                                    @fullscreen="$refs.inlineMediaRendererRef?.$refs?.imageViewer?.requestFullscreen()"
                                ></inline-media-renderer>
                            </div>
                            <v-card-subtitle class="text-center text-caption">
                                {{ media.title || "Unknown Filename" }}
                            </v-card-subtitle>
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
                                    block
                                >
                                    Bulletin {{ media.bulletin.ref }}
                                </v-btn>
                                <div class="text-caption text-medium-emphasis mt-2">
                                    {{ media.bulletin.title }}
                                </div>
                            </div>

                            <v-divider class="my-4"></v-divider>

                            <!-- Confidence -->
                            <div class="mb-4">
                                <div class="text-subtitle-2 mb-2">Confidence</div>
                                <v-progress-linear
                                    :model-value="media.confidence"
                                    :color="getConfidenceColor(media.confidence)"
                                    height="20"
                                    rounded
                                >
                                    <template v-slot:default>
                                        <strong>{{ Math.round(media.confidence) }}</strong>
                                    </template>
                                </v-progress-linear>
                                <div class="text-caption text-medium-emphasis mt-1">
                                    {{ getConfidenceLabel(media.confidence) }}
                                </div>
                            </div>

                            <v-divider class="my-4"></v-divider>

                            <!-- Extracted Text -->
                            <div>
                                <div class="text-subtitle-2 mb-2">Extracted Text</div>
                                <v-textarea
                                    v-model="transcriptionText"
                                    variant="outlined"
                                    no-resize
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
                        Accept
                    </v-btn>

                    <v-btn
                        color="error"
                        variant="elevated"
                        size="large"
                        prepend-icon="mdi-close-circle"
                        class="mx-2"
                        @click="$emit('rejected', media)"
                    >
                        Can't Read
                    </v-btn>
                    </v-col>
                </v-row>
            </v-card-text>
          </v-form>
        </v-card>
      <v-card v-else class="pa-8">
        <v-card-text class="text-center">loading</v-card-text>
      </v-card>
    </v-dialog>
    `,
});
