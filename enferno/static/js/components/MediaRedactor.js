const MediaRedactor = Vue.defineComponent({
  props: {
    modelValue: { type: Boolean, default: false },
    media: { type: Object, default: null },
  },
  emits: ['update:modelValue', 'redacted'],

  data() {
    return {
      loading: false,
      saving: false,
      error: null,
      pages: [],
      boxes: {},
      draft: null,
    };
  },

  computed: {
    show: {
      get() {
        return this.modelValue;
      },
      set(value) {
        this.$emit('update:modelValue', value);
      },
    },
    src() {
      return this.media?.id ? `/admin/api/media/${this.media.id}/proxy` : null;
    },
    mediaKind() {
      const fileType = this.media?.fileType || '';
      if (fileType.includes('pdf')) return 'pdf';
      if (fileType.includes('image')) return 'image';
      const filename = this.media?.filename || '';
      if (filename.toLowerCase().endsWith('.pdf')) return 'pdf';
      if (/\.(jpe?g|png)$/i.test(filename)) return 'image';
      return 'unsupported';
    },
    canSubmit() {
      return Object.values(this.boxes).some(pageBoxes => pageBoxes.length);
    },
  },

  watch: {
    show(value) {
      if (value) this.load();
      else this.reset();
    },
    media() {
      if (this.show) this.load();
    },
  },

  created() {
    this._pdf = null;
  },

  beforeUnmount() {
    this._pdf?.destroy?.();
  },

  methods: {
    reset() {
      this.loading = false;
      this.saving = false;
      this.error = null;
      this.pages = [];
      this.boxes = {};
      this.draft = null;
      this._pdf?.destroy?.();
      this._pdf = null;
    },
    async load() {
      this.reset();
      if (!this.src) return;
      if (this.mediaKind === 'pdf') return this.loadPdf();
      if (this.mediaKind === 'image') {
        this.pages = [{ index: 0, width: 1, height: 1, rendered: true }];
        this.boxes = { 0: [] };
        return;
      }
      this.error = 'Unsupported file type';
    },
    async loadPdf() {
      this.loading = true;
      try {
        await loadScript('/static/js/pdf.js/pdf.min.mjs');
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.js/pdf.worker.min.mjs';
        const pdf = await pdfjsLib.getDocument(this.src).promise;
        this._pdf = pdf;
        const pages = [];
        for (let index = 0; index < pdf.numPages; index++) {
          const page = await pdf.getPage(index + 1);
          const viewport = page.getViewport({ scale: 1 });
          pages.push({ index, width: viewport.width, height: viewport.height, rendered: false });
          this.boxes[index] = [];
          await page.cleanup();
        }
        this.pages = pages;
        await this.$nextTick();
        for (const page of pages) await this.renderPdfPage(page.index);
      } catch (e) {
        console.error('PDF redactor load failed:', e);
        this.error = 'Failed to load document';
      } finally {
        this.loading = false;
      }
    },
    canvasRef(index) {
      const ref = this.$refs[`redactCanvas-${index}`];
      return Array.isArray(ref) ? ref[0] : ref;
    },
    async renderPdfPage(index) {
      const canvas = this.canvasRef(index);
      if (!canvas || !this._pdf) return;
      const pdfPage = await this._pdf.getPage(index + 1);
      const viewport = pdfPage.getViewport({ scale: 1.5 });
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(viewport.width * dpr);
      canvas.height = Math.floor(viewport.height * dpr);
      canvas.style.width = '100%';
      canvas.style.height = 'auto';
      const ctx = canvas.getContext('2d', { alpha: false });
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, viewport.width, viewport.height);
      await pdfPage.render({ canvasContext: ctx, viewport }).promise;
      await pdfPage.cleanup();
      this.pages = this.pages.map(page =>
        page.index === index ? { ...page, width: viewport.width, height: viewport.height, rendered: true } : page
      );
    },
    pageRect(index) {
      return this.$refs[`page-${index}`]?.[0]?.getBoundingClientRect?.()
        || this.$refs[`page-${index}`]?.getBoundingClientRect?.();
    },
    normalizedPoint(index, event) {
      const rect = this.pageRect(index);
      const x = Math.min(Math.max((event.clientX - rect.left) / rect.width, 0), 1);
      const y = Math.min(Math.max((event.clientY - rect.top) / rect.height, 0), 1);
      return { x, y };
    },
    startBox(index, event) {
      if (event.button !== 0) return;
      const point = this.normalizedPoint(index, event);
      this.draft = { page: index, startX: point.x, startY: point.y, x: point.x, y: point.y, w: 0, h: 0 };
    },
    moveBox(index, event) {
      if (!this.draft || this.draft.page !== index) return;
      const point = this.normalizedPoint(index, event);
      const x0 = Math.min(this.draft.startX, point.x);
      const y0 = Math.min(this.draft.startY, point.y);
      const x1 = Math.max(this.draft.startX, point.x);
      const y1 = Math.max(this.draft.startY, point.y);
      this.draft = { ...this.draft, x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    },
    finishBox() {
      if (!this.draft) return;
      if (this.draft.w > 0.005 && this.draft.h > 0.005) {
        const pageBoxes = this.boxes[this.draft.page] || [];
        pageBoxes.push({ x: this.draft.x, y: this.draft.y, w: this.draft.w, h: this.draft.h });
        this.boxes = { ...this.boxes, [this.draft.page]: pageBoxes };
      }
      this.draft = null;
    },
    deleteBox(pageIndex, boxIndex) {
      const pageBoxes = [...(this.boxes[pageIndex] || [])];
      pageBoxes.splice(boxIndex, 1);
      this.boxes = { ...this.boxes, [pageIndex]: pageBoxes };
    },
    visibleBoxes(pageIndex) {
      const boxes = [...(this.boxes[pageIndex] || [])];
      if (this.draft?.page === pageIndex) boxes.push(this.draft);
      return boxes;
    },
    async submit() {
      if (!this.canSubmit) return;
      this.saving = true;
      const pages = Object.entries(this.boxes)
        .filter(([, rects]) => rects.length)
        .map(([page, rects]) => ({ page: Number(page), rects }));
      try {
        const response = await api.post(`/admin/api/media/${this.media.id}/redact`, { pages });
        this.$emit('redacted', response.data.data);
        this.show = false;
      } catch (e) {
        this.error = e.response?.data?.message || 'Failed to create redacted copy';
      } finally {
        this.saving = false;
      }
    },
  },

  template: /*html*/`
    <v-dialog v-model="show" fullscreen scrollable>
      <v-card>
        <v-toolbar density="compact">
          <v-btn icon="mdi-close" variant="text" @click="show = false"></v-btn>
          <v-toolbar-title>{{ media?.title || media?.filename || 'Redact document' }}</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn
            color="primary"
            variant="flat"
            prepend-icon="mdi-marker"
            :disabled="!canSubmit"
            :loading="saving"
            @click="submit"
          >Create redacted copy</v-btn>
        </v-toolbar>

        <v-alert v-if="error" type="error" variant="tonal" class="ma-3">{{ error }}</v-alert>
        <v-card-text class="pa-0 bg-grey-lighten-3">
          <div v-if="loading" class="d-flex align-center justify-center" style="height: 70vh;">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
          </div>
          <div v-else class="d-flex flex-column align-center ga-4 pa-4">
            <div
              v-for="page in pages"
              :key="page.index"
              class="position-relative bg-white elevation-2"
              style="width: min(100%, 960px); line-height: 0; user-select: none;"
              :style="{ aspectRatio: page.width + ' / ' + page.height }"
              :ref="'page-' + page.index"
              @mousedown.prevent="startBox(page.index, $event)"
              @mousemove.prevent="moveBox(page.index, $event)"
              @mouseup.prevent="finishBox"
              @mouseleave="finishBox"
            >
              <canvas
                v-if="mediaKind === 'pdf'"
                :ref="'redactCanvas-' + page.index"
                class="w-100 d-block"
              ></canvas>
              <img
                v-else
                :src="src"
                class="w-100 d-block"
                draggable="false"
                @load="page.width = $event.target.naturalWidth; page.height = $event.target.naturalHeight"
              >

              <div
                v-for="(box, boxIndex) in visibleBoxes(page.index)"
                :key="boxIndex"
                class="position-absolute"
                :style="{
                  left: (box.x * 100) + '%',
                  top: (box.y * 100) + '%',
                  width: (box.w * 100) + '%',
                  height: (box.h * 100) + '%',
                  background: 'rgba(0,0,0,0.82)',
                  border: '1px solid #111',
                  pointerEvents: draft && boxIndex === visibleBoxes(page.index).length - 1 ? 'none' : 'auto',
                }"
                @mousedown.stop
              >
                <v-btn
                  v-if="!(draft && boxIndex === visibleBoxes(page.index).length - 1)"
                  icon="mdi-close"
                  size="x-small"
                  color="white"
                  variant="text"
                  class="position-absolute"
                  style="right: -4px; top: -4px;"
                  @click.stop="deleteBox(page.index, boxIndex)"
                ></v-btn>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  `,
});
