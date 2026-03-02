const PdfViewer = Vue.defineComponent({
  props: ['media', 'mediaType'],

  data: () => ({
    pageMap: new Map(),
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

  created() {
    this._pdf = null;               // non-reactive PDFDocumentProxy
    this._rendering = new Set();    // guard against double render
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
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.js/pdf.worker.min.mjs';

        const pdf = await pdfjsLib.getDocument(url).promise;
        this._pdf = pdf;

        // Use page 1 dimensions as the aspect ratio placeholder for all pages
        const firstPage = await pdf.getPage(1);
        const firstVp = firstPage.getViewport({ scale: 1 });
        const ratioWidth = firstVp.width;
        const ratioHeight = firstVp.height;
        await firstPage.cleanup();

        for (let i = 1; i <= pdf.numPages; i++) {
          this.pageMap.set(i, {
            pageNumber: i,
            width: ratioWidth,
            height: ratioHeight,
            rendered: false,
            renderError: false,
          });
        }
      } catch (e) {
        console.error('PDF load error:', e);
        this.error = true;
      } finally {
        this.loading = false;
      }
    },

    getCanvasEl(pageNumber) {
      // With v-for + :ref, Vue may store refs as arrays
      const ref = this.$refs[`pageCanvas-${pageNumber}`];
      return Array.isArray(ref) ? ref[0] : ref;
    },

    async renderPage(pageNumber) {
      if (this._rendering.has(pageNumber)) return;

      const pageState = this.pageMap.get(pageNumber);
      if (!pageState || pageState.rendered || pageState.renderError) return;
      if (!this._pdf) return;

      const canvas = this.getCanvasEl(pageNumber);
      if (!canvas) return; // not in DOM (scrolled away / destroyed)

      this._rendering.add(pageNumber);

      try {
        const page = await this._pdf.getPage(pageNumber);

        const scale = 1.5;
        const viewport = page.getViewport({ scale });

        // HiDPI support
        const dpr = window.devicePixelRatio || 1;

        // Size canvas backing store in physical pixels
        canvas.width = Math.floor(viewport.width * dpr);
        canvas.height = Math.floor(viewport.height * dpr);

        // Size canvas element in CSS pixels
        canvas.style.width = '100%';
        canvas.style.height = 'auto';

        const ctx = canvas.getContext('2d', { alpha: false });

        // Reset transform then scale for DPR
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        // Fill white BEFORE rendering to prevent black flash on canvas resize
        ctx.fillStyle = '#fff';
        ctx.fillRect(0, 0, viewport.width, viewport.height);

        await page.render({ canvasContext: ctx, viewport }).promise;

        // Update to actual rendered dimensions and mark as done
        this.pageMap.set(pageNumber, {
          ...pageState,
          width: viewport.width,
          height: viewport.height,
          rendered: true,
        });

        await page.cleanup();
      } catch (e) {
        console.error('Page render error:', e);
        this.pageMap.set(pageNumber, { ...pageState, renderError: true });
      } finally {
        this._rendering.delete(pageNumber);
      }
    },

    onIntersect(isIntersecting, entries, observer, page) {
      if (isIntersecting && !page.rendered && !page.renderError) {
        this.renderPage(page.pageNumber);
      }
    },

    requestFullscreen() {
      this.$refs.container?.requestFullscreen?.();
    },
  },

  template: `
    <div ref="container" class="w-100 h-100 overflow-y-auto d-flex flex-column align-center bg-grey-lighten-3 pa-4 ga-4">

      <v-progress-circular
        v-if="loading"
        indeterminate
        color="primary"
        size="64"
        class="mt-8"
      ></v-progress-circular>

      <div v-else-if="error" class="d-flex flex-column align-center justify-center h-100 text-medium-emphasis">
        <v-icon size="64" color="red">mdi-file-pdf-box</v-icon>
        <div class="mt-2 text-caption">Failed to load PDF</div>
      </div>

      <div v-else v-for="page in Array.from(pageMap.values())" :key="page.pageNumber" class="w-100 d-flex justify-center">
        <div
          class="w-100 bg-white elevation-2 rounded overflow-hidden"
          style="max-width: 900px;"
          v-intersect="(isIntersecting, entries, observer) => onIntersect(isIntersecting, entries, observer, page)"
          :style="{ aspectRatio: page.width + ' / ' + page.height }"
        >
          <div v-if="page.renderError" class="pa-6 d-flex flex-column align-center justify-center">
            <v-icon size="48" color="red">mdi-alert-circle</v-icon>
            <div class="mt-2 text-caption">Failed to render page</div>
          </div>

          <template v-else>
            <!--
              Canvas is always in the DOM so the ref is available when
              onIntersect fires. It stays hidden (via opacity) until rendered
              to avoid the black flash from an unpainted canvas backing store.
            -->
            <canvas
              :ref="'pageCanvas-' + page.pageNumber"
              class="w-100"
              :style="{
                display: 'block',
                background: '#fff',
                opacity: page.rendered ? 1 : 0,
                position: page.rendered ? 'static' : 'absolute',
              }"
            ></canvas>

            <!-- Skeleton placeholder shown until the page is painted -->
            <div v-if="!page.rendered" class="pa-4">
              <v-skeleton-loader type="article, paragraph, paragraph, paragraph"></v-skeleton-loader>
            </div>
          </template>
        </div>
      </div>
    </div>
  `,
});