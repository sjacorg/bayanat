const PdfViewer = Vue.defineComponent({
  props: ['media', 'mediaType'],
  data: () => ({
    pages: [],
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
        if (url) await this.loadPdf(url);
      },
    },
  },
  methods: {
    async loadPdf(url) {
      this.loading = true;
      this.error = false;
      this.pages = [];

      try {
        if (typeof pdfjsLib === 'undefined') {
          await loadScript('/static/js/pdf.js/pdf.min.mjs');
        }
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.js/pdf.worker.min.mjs';

        const pdf = await pdfjsLib.getDocument(url).promise;

        for (let i = 1; i <= pdf.numPages; i++) {
          const page = await pdf.getPage(i);
          const viewport = page.getViewport({ scale: 1.5 });
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          canvas.width = viewport.width;
          canvas.height = viewport.height;
          await page.render({ canvasContext: ctx, viewport }).promise;
          this.pages.push(canvas.toDataURL('image/png'));
          await page.cleanup();
        }

        pdf.destroy();
      } catch (e) {
        console.error('PDF render error:', e);
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
    <div ref="container" class="w-100 h-100 overflow-y-auto d-flex flex-column align-center bg-grey-lighten-3 pa-4 ga-2">
      <v-progress-circular v-if="loading" indeterminate color="primary" size="64" class="mt-8"></v-progress-circular>
      <div v-else-if="error" class="d-flex flex-column align-center justify-center h-100 text-medium-emphasis">
        <v-icon size="64" color="red">mdi-file-pdf-box</v-icon>
        <div class="mt-2 text-caption">Failed to load PDF</div>
      </div>
      <img v-else v-for="(page, i) in pages" :key="i" :src="page" class="w-100 elevation-2 rounded" style="max-width: 900px;" />
    </div>
  `,
});
