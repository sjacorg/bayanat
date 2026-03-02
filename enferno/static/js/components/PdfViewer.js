const PdfViewer = Vue.defineComponent({
  props: ['media', 'mediaType'],

  data: () => ({
    pageMap: new Map(),
    loading: false,
    error: false,
  }),

  computed: {
    src() {
      return this.media?.id
        ? `/admin/api/media/${this.media.id}/proxy`
        : null;
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

  created() {
    this._pdf = null; // non-reactive
    this._rendering = new Set(); // prevent double renders
  },

  beforeUnmount() {
    this._pdf?.destroy?.();
    this._pdf = null;
  },

  methods: {
    async loadPdf(url) {
      this.loading = true;
      this.error = false;
      this.pageMap = new Map();

      if (this._pdf) {
        try { await this._pdf.destroy(); } catch {}
        this._pdf = null;
      }

      try {
        if (typeof pdfjsLib === 'undefined') {
          await loadScript('/static/js/pdf.js/pdf.min.mjs');
        }

        pdfjsLib.GlobalWorkerOptions.workerSrc =
          '/static/js/pdf.js/pdf.worker.min.mjs';

        const pdf = await pdfjsLib.getDocument(url).promise;
        this._pdf = pdf;

        // ✅ GET REAL RATIO FROM PAGE 1 ONLY
        const firstPage = await pdf.getPage(1);
        const viewport = firstPage.getViewport({ scale: 1 });

        const ratioWidth = viewport.width;
        const ratioHeight = viewport.height;

        await firstPage.cleanup();

        // ✅ Use same ratio for all placeholders
        for (let i = 1; i <= pdf.numPages; i++) {
          this.pageMap.set(i, {
            pageNumber: i,
            width: ratioWidth,
            height: ratioHeight,
            rendered: false,
            renderError: false,
            img: null,
          });
        }

      } catch (e) {
        console.error('PDF load error:', e);
        this.error = true;
      } finally {
        this.loading = false;
      }
    },

    async renderPage(pageNumber) {
      if (this._rendering.has(pageNumber)) return;

      const selectedPage = this.pageMap.get(pageNumber);
      if (!selectedPage || selectedPage.rendered || selectedPage.renderError) return;
      if (!this._pdf) return;

      this._rendering.add(pageNumber);

      try {
        const page = await this._pdf.getPage(pageNumber);
        const viewport = page.getViewport({ scale: 1.5 });

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');

        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        await page.render({ canvasContext: ctx, viewport }).promise;

        this.pageMap.set(pageNumber, {
          ...selectedPage,
          width: viewport.width,
          height: viewport.height,
          img: canvas.toDataURL('image/png'),
          rendered: true,
        });

        await page.cleanup();
      } catch (e) {
        console.error('Page render error:', e);
        this.pageMap.set(pageNumber, {
          ...selectedPage,
          renderError: true,
        });
      } finally {
        this._rendering.delete(pageNumber);
      }
    },

    onIntersect(isIntersecting, entries, observer, page) {
      if (isIntersecting && !page.rendered && !page.renderError) {
        this.renderPage(page.pageNumber);
      }
    },
  },

  template: `
    <div ref="container"
         class="w-100 h-100 overflow-y-auto d-flex flex-column align-center bg-grey-lighten-3 pa-4 ga-4">

      <!-- GLOBAL LOADING -->
      <v-progress-circular
        v-if="loading"
        indeterminate
        color="primary"
        size="64"
        class="mt-8"
      ></v-progress-circular>

      <!-- GLOBAL LOAD ERROR -->
      <div v-else-if="error"
           class="d-flex flex-column align-center justify-center h-100 text-medium-emphasis">
        <v-icon size="64" color="red">mdi-file-pdf-box</v-icon>
        <div class="mt-2 text-caption">Failed to load PDF</div>
      </div>

      <!-- PDF PAGES -->
      <div v-else
           v-for="(page, i) in Array.from(pageMap.values())"
           :key="i"
           class="w-100 d-flex justify-center">

        <!-- Rendered Image -->
        <img v-if="page.img"
             :src="page.img"
             class="w-100 elevation-2 rounded"
             style="max-width: 900px;" />

        <!-- Render Error -->
        <div v-else-if="page.renderError"
             class="w-100 bg-grey-lighten-2 elevation-2 rounded d-flex flex-column align-center justify-center"
             style="max-width: 900px; min-height: 300px;">
          <v-icon size="48" color="red">mdi-alert-circle</v-icon>
          <div class="mt-2 text-caption">Failed to render page</div>
        </div>

        <!-- Skeleton Placeholder -->
        <div v-else
             v-intersect="(isIntersecting, entries, observer) => onIntersect(isIntersecting, entries, observer, page)"
             :style="{ aspectRatio: page.width + ' / ' + page.height }"
             class="w-100 bg-white elevation-2 d-flex align-center justify-center"
             style="max-width: 900px;">

          <v-skeleton-loader
            type="article, paragraph, paragraph, paragraph"
          ></v-skeleton-loader>

        </div>
      </div>
    </div>
  `,
});