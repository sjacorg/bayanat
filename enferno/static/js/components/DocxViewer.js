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
  },
  template: `
    <div class="w-100 h-100 d-flex align-center justify-center bg-grey-lighten-3">
      <!-- Loading state -->
      <div v-if="loading" class="d-flex align-center justify-center" style="height:100%;">
        <v-progress-circular indeterminate color="blue"></v-progress-circular>
      </div>

      <!-- Error state -->
      <div v-else-if="error" class="d-flex flex-column align-center justify-center ga-2 text-medium-emphasis" style="height:100%;">
        <v-icon icon="mdi-alert-circle-outline" color="error" size="48"></v-icon>
        <div class="text-caption">Failed to load document</div>
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
