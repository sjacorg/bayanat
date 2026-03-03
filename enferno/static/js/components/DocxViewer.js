const DocxViewer = Vue.defineComponent({
  props: ['media'],
  data: () => ({
    loading: false,
    error: false,
  }),
  computed: {
    src() {
      return this.media?.id ? `/admin/api/media/${this.media.id}/proxy` : null;
    },
  },
  watch: {
    src: {
      immediate: true,
      async handler(url) {
        if (!url) return; 
        await this.loadDocument(url);
      },
    },
  },
  methods: {
    async loadDocument(url) {
      this.loading = true;
      this.error = false;

      try {
        await loadScript('/static/js/jszip/jszip.min.js');
        await loadScript('/static/js/docx-preview/docx-preview.min.js');

        const response = await api.get(url, { responseType: 'blob' });
        const blob = response.data;

        await docx.renderAsync(blob, this.$refs.docxContainer, null, {
          className: 'docx-preview bg-white elevation-2 rounded mx-auto pa-16',
          inWrapper: false,
        });
      } catch (e) {
        console.error('Docx load error:', e);
        this.error = true;
      } finally {
        this.loading = false;
      }
    },
    requestFullscreen() {
      this.$refs.container?.requestFullscreen?.();
    },
  },
  template: `
    <div ref="container" class="w-100 h-100 d-flex flex-column align-center bg-grey-lighten-3">
      <!-- Loading state -->
      <v-progress-circular
        v-if="loading"
        indeterminate
        color="primary"
        size="64"
        class="mt-8"
      ></v-progress-circular>

      <!-- Error state -->
      <div v-else-if="error" class="d-flex flex-column align-center justify-center h-100 text-medium-emphasis">
        <v-icon size="64" color="blue">mdi-file-word-outline</v-icon>
        <div class="mt-2 text-caption">Failed to load Docx</div>
      </div>

      <!-- Docx render target -->
      <div
        v-show="!loading && !error"
        ref="docxContainer"
        class="w-100 h-100 overflow-auto pa-4"
        style="font-size: 13px;"
      ></div>
    </div>
  `,
});
