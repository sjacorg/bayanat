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
      label: '',
      pages: [],
      boxes: {},
      draft: null,
      drag: null,
      resize: null,
      hoveredBox: null,
      activeBox: null,
      spaceDown: false,
      panning: null,
      zoom: 1,
      pinchStartDistance: null,
      pinchStartZoom: 1,
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
    async show(value) {
      if (value) {
        this.load();
        await this.$nextTick();
        const el = this.$refs.scrollPane?.$el ?? this.$refs.scrollPane;
        if (el) {
          this._scrollPane = el;
          el.addEventListener('touchmove', this._touchMoveHandler, { passive: false });
          el.addEventListener('wheel', this._wheelHandler, { passive: false });
        }
        window.addEventListener('keydown', this._keydownHandler);
        window.addEventListener('keyup', this._keyupHandler);
      } else {
        this._scrollPane?.removeEventListener('touchmove', this._touchMoveHandler);
        this._scrollPane?.removeEventListener('wheel', this._wheelHandler);
        this._scrollPane = null;
        window.removeEventListener('keydown', this._keydownHandler);
        window.removeEventListener('keyup', this._keyupHandler);
        this.reset();
      }
    },
    media() {
      if (this.show) this.load();
    },
  },

  created() {
    this._pdf = null;
    this._touchMoveHandler = (e) => this.onTouchMove(e);
    this._wheelHandler = (e) => this.onWheel(e);
    this._keydownHandler = (e) => this.onKeydown(e);
    this._keyupHandler = (e) => this.onKeyup(e);
  },

  beforeUnmount() {
    this._scrollPane?.removeEventListener('touchmove', this._touchMoveHandler);
    this._scrollPane?.removeEventListener('wheel', this._wheelHandler);
    window.removeEventListener('keydown', this._keydownHandler);
    window.removeEventListener('keyup', this._keyupHandler);
    this._pdf?.destroy?.();
  },

  methods: {
    reset() {
      this.loading = false;
      this.saving = false;
      this.error = null;
      this.label = '';
      this.pages = [];
      this.boxes = {};
      this.draft = null;
      this.drag = null;
      this.resize = null;
      this.hoveredBox = null;
      this.activeBox = null;
      this.spaceDown = false;
      this.panning = null;
      this.zoom = 1;
      this.pinchStartDistance = null;
      this.pinchStartZoom = 1;
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
      if (event.button !== 0 || this.spaceDown) return;
      const point = this.normalizedPoint(index, event);
      this.draft = { page: index, startX: point.x, startY: point.y, x: point.x, y: point.y, w: 0, h: 0 };
    },
    startDrag(pageIndex, boxIndex, event) {
      if (event.button !== 0) return;
      event.stopPropagation();
      this.activeBox = { page: pageIndex, box: boxIndex };
      const point = this.normalizedPoint(pageIndex, event);
      const box = this.boxes[pageIndex][boxIndex];
      this.drag = { page: pageIndex, boxIndex, startMouseX: point.x, startMouseY: point.y, origX: box.x, origY: box.y };
    },
    // corner: 'tl' | 'tr' | 'bl' | 'br' — the corner being dragged; opposite corner is the anchor
    startResize(pageIndex, boxIndex, corner, event) {
      if (event.button !== 0) return;
      event.stopPropagation();
      this.activeBox = { page: pageIndex, box: boxIndex };
      const box = this.boxes[pageIndex][boxIndex];
      const anchorX = corner.includes('l') ? box.x + box.w : box.x;
      const anchorY = corner.includes('t') ? box.y + box.h : box.y;
      this.resize = { page: pageIndex, boxIndex, corner, anchorX, anchorY };
    },
    moveBox(index, event) {
      if (this.resize && this.resize.page === index) {
        const point = this.normalizedPoint(index, event);
        const { anchorX, anchorY, boxIndex } = this.resize;
        const x = Math.min(Math.max(Math.min(point.x, anchorX), 0), 1);
        const y = Math.min(Math.max(Math.min(point.y, anchorY), 0), 1);
        const w = Math.min(Math.abs(point.x - anchorX), 1 - x);
        const h = Math.min(Math.abs(point.y - anchorY), 1 - y);
        const pageBoxes = [...(this.boxes[index] || [])];
        pageBoxes[boxIndex] = { x, y, w, h };
        this.boxes = { ...this.boxes, [index]: pageBoxes };
        return;
      }
      if (this.drag && this.drag.page === index) {
        const point = this.normalizedPoint(index, event);
        const dx = point.x - this.drag.startMouseX;
        const dy = point.y - this.drag.startMouseY;
        const pageBoxes = [...(this.boxes[index] || [])];
        const box = pageBoxes[this.drag.boxIndex];
        pageBoxes[this.drag.boxIndex] = {
          ...box,
          x: Math.min(Math.max(this.drag.origX + dx, 0), 1 - box.w),
          y: Math.min(Math.max(this.drag.origY + dy, 0), 1 - box.h),
        };
        this.boxes = { ...this.boxes, [index]: pageBoxes };
        return;
      }
      if (!this.draft || this.draft.page !== index) return;
      const point = this.normalizedPoint(index, event);
      const x0 = Math.min(this.draft.startX, point.x);
      const y0 = Math.min(this.draft.startY, point.y);
      const x1 = Math.max(this.draft.startX, point.x);
      const y1 = Math.max(this.draft.startY, point.y);
      this.draft = { ...this.draft, x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    },
    finishBox() {
      if (this.resize) { this.resize = null; return; }
      if (this.drag) { this.drag = null; return; }
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
      if (this.hoveredBox?.page === pageIndex && this.hoveredBox?.box === boxIndex) this.hoveredBox = null;
      if (this.activeBox?.page === pageIndex && this.activeBox?.box === boxIndex) this.activeBox = null;
    },
    onKeydown(event) {
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (event.code === 'Space' && !this.spaceDown) {
        event.preventDefault();
        this.spaceDown = true;
        return;
      }
      if (event.key !== 'Backspace' && event.key !== 'Delete') return;
      const target = this.activeBox || this.hoveredBox;
      if (!target) return;
      event.preventDefault();
      this.deleteBox(target.page, target.box);
    },
    onKeyup(event) {
      if (event.code === 'Space') {
        this.spaceDown = false;
        this.panning = null;
      }
    },
    onPanStart(event) {
      if (!this.spaceDown || event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      const pane = this._scrollPane;
      if (!pane) return;
      this.panning = { startX: event.clientX, startY: event.clientY, scrollLeft: pane.scrollLeft, scrollTop: pane.scrollTop };
    },
    onPanMove(event) {
      if (!this.panning) return;
      event.preventDefault();
      const pane = this._scrollPane;
      if (!pane) return;
      pane.scrollLeft = this.panning.scrollLeft - (event.clientX - this.panning.startX);
      pane.scrollTop = this.panning.scrollTop - (event.clientY - this.panning.startY);
    },
    onPanEnd() {
      this.panning = null;
    },
    visibleBoxes(pageIndex) {
      const boxes = [...(this.boxes[pageIndex] || [])];
      if (this.draft?.page === pageIndex) boxes.push(this.draft);
      return boxes;
    },
    zoomIn() {
      this.zoom = Math.min(+(this.zoom + 0.25).toFixed(2), 3);
    },
    zoomOut() {
      this.zoom = Math.max(+(this.zoom - 0.25).toFixed(2), 1);
    },
    zoomFit() {
      this.zoom = 1;
    },
    pinchDistance(touches) {
      const dx = touches[0].clientX - touches[1].clientX;
      const dy = touches[0].clientY - touches[1].clientY;
      return Math.sqrt(dx * dx + dy * dy);
    },
    onTouchStart(event) {
      if (event.touches.length === 2) {
        this.pinchStartDistance = this.pinchDistance(event.touches);
        this.pinchStartZoom = this.zoom;
      }
    },
    onTouchMove(event) {
      if (event.touches.length === 2 && this.pinchStartDistance) {
        event.preventDefault();
        const scale = this.pinchDistance(event.touches) / this.pinchStartDistance;
        const next = Math.min(Math.max(this.pinchStartZoom * scale, 1), 3);
        const midX = (event.touches[0].clientX + event.touches[1].clientX) / 2;
        const midY = (event.touches[0].clientY + event.touches[1].clientY) / 2;
        this.applyZoom(next, midX, midY);
      }
    },
    onTouchEnd() {
      this.pinchStartDistance = null;
    },
    applyZoom(nextZoom, anchorX, anchorY) {
      const pane = this._scrollPane;
      if (!pane) { this.zoom = nextZoom; return; }
      const rect = pane.getBoundingClientRect();
      const localX = anchorX !== undefined ? anchorX - rect.left : pane.clientWidth / 2;
      const localY = anchorY !== undefined ? anchorY - rect.top : pane.clientHeight / 2;
      const worldX = pane.scrollLeft + localX;
      const worldY = pane.scrollTop + localY;
      const ratio = nextZoom / this.zoom;
      this.zoom = nextZoom;
      this.$nextTick(() => {
        pane.scrollLeft = worldX * ratio - localX;
        pane.scrollTop = worldY * ratio - localY;
      });
    },
    onWheel(event) {
      if (!event.ctrlKey) return;
      event.preventDefault();
      const factor = Math.exp(-event.deltaY * 0.005);
      const next = Math.min(Math.max(this.zoom * factor, 1), 3);
      this.applyZoom(next, event.clientX, event.clientY);
    },
    async submit() {
      if (!this.canSubmit) return;
      this.saving = true;
      const pages = Object.entries(this.boxes)
        .filter(([, rects]) => rects.length)
        .map(([page, rects]) => ({ page: Number(page), rects }));
      try {
        const response = await api.post(`/admin/api/media/${this.media.id}/redact`, { pages, title: this.label.trim() });
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
    <v-dialog v-model="show" fullscreen scrollable  persistent @keydown.esc.prevent no-click-animation>
      <v-card>
        <v-toolbar color="dark-primary">
          <v-toolbar-title>{{ media?.title || media?.filename || 'Redact document' }}</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-text-field
            v-model="label"
            density="comfortable"
            variant="solo"
            hide-details
            label="Label this copy (e.g. detainee name)"
            style="max-width: 320px;"
            class="mx-3"
          ></v-text-field>
          <v-btn
            prepend-icon="mdi-marker"
            variant="elevated"
            :disabled="!canSubmit"
            :loading="saving"
            @click="submit"
            class="mr-2"
          >Create redacted copy</v-btn>
          <template #append>
            <v-btn icon="mdi-close" @click="show = false"></v-btn>
          </template>
        </v-toolbar>
        <v-toolbar density="compact">
          <v-spacer></v-spacer>
          <v-btn icon="mdi-minus" variant="tonal" density="compact" :disabled="zoom <= 1" @click="zoomOut"></v-btn>
          <span class="text-body-2 mx-1" style="min-width: 44px; text-align: center;">{{ Math.round(zoom * 100) }}%</span>
          <v-btn icon="mdi-plus" variant="tonal" density="compact" :disabled="zoom >= 3" @click="zoomIn"></v-btn>
          <v-btn variant="tonal" density="compact" size="large" class="mx-1" @click="zoomFit">Fit</v-btn>
          <v-spacer></v-spacer>
        </v-toolbar>

        <v-alert v-if="error" type="error" variant="tonal" class="ma-3">{{ error }}</v-alert>
        <v-card-text
          ref="scrollPane"
          class="pa-0 bg-grey-lighten-3"
          style="overflow: auto;"
          :style="{ touchAction: zoom > 1 ? 'pan-x pan-y' : 'pan-y', cursor: panning ? 'grabbing' : spaceDown ? 'grab' : 'default' }"
          @mousedown="onPanStart"
          @mousemove="onPanMove"
          @mouseup="onPanEnd"
          @mouseleave="onPanEnd"
          @touchstart="onTouchStart"
          @touchend="onTouchEnd"
          @touchcancel="onTouchEnd"
        >
          <div v-if="loading" class="d-flex align-center justify-center" style="height: 70vh;">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
          </div>
          <div v-else
            class="d-flex flex-column align-center ga-4 pa-4"
            :style="{ width: zoom > 1 ? (zoom * 960) + 'px' : '100%', minWidth: '100%' }"
          >
            <div
              v-for="page in pages"
              :key="page.index"
              class="position-relative bg-white elevation-2"
              :style="{ width: zoom !== 1 ? '100%' : 'min(100%, 960px)', lineHeight: 0, userSelect: 'none', aspectRatio: page.width + ' / ' + page.height }"
              :ref="'page-' + page.index"
              @mousedown.prevent="activeBox = null; startBox(page.index, $event)"
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
                  padding: '9px',
                  margin: '-9px',
                  boxSizing: 'content-box',
                  pointerEvents: draft && boxIndex === visibleBoxes(page.index).length - 1 ? 'none' : 'auto',
                  zIndex: 5,
                }"
                @mousedown.prevent="startDrag(page.index, boxIndex, $event)"
                @mouseenter="hoveredBox = { page: page.index, box: boxIndex }"
                @mouseleave="hoveredBox = null"
              >
                <div
                  class="position-relative"
                  :style="{
                    width: '100%',
                    height: '100%',
                    background: 'rgba(0,0,0,0.82)',
                    border: (hoveredBox?.page === page.index && hoveredBox?.box === boxIndex) || (activeBox?.page === page.index && activeBox?.box === boxIndex) ? '2px solid rgb(var(--v-theme-primary))' : '1px solid #111',
                    cursor: 'move',
                  }"
                >
                  <template v-if="!(draft && boxIndex === visibleBoxes(page.index).length - 1) && ((hoveredBox?.page === page.index && hoveredBox?.box === boxIndex) || (activeBox?.page === page.index && activeBox?.box === boxIndex))">
                    <div
                      v-for="corner in ['tl','tr','bl','br']"
                      :key="corner"
                      class="position-absolute bg-white"
                      :style="{
                        width: '10px', height: '10px',
                        top: corner.includes('t') ? '-5px' : 'auto',
                        bottom: corner.includes('b') ? '-5px' : 'auto',
                        left: corner.includes('l') ? '-5px' : 'auto',
                        right: corner.includes('r') ? '-5px' : 'auto',
                        cursor: corner === 'tl' || corner === 'br' ? 'nwse-resize' : 'nesw-resize',
                        border: '2px solid #333',
                        borderRadius: '2px',
                        zIndex: 20,
                      }"
                      @mousedown.prevent.stop="startResize(page.index, boxIndex, corner, $event)"
                    ></div>
                  </template>
                </div>
                <v-fade-transition>
                  <v-btn
                    v-if="!(draft && boxIndex === visibleBoxes(page.index).length - 1) && ((hoveredBox?.page === page.index && hoveredBox?.box === boxIndex) || (activeBox?.page === page.index && activeBox?.box === boxIndex))"
                    size="18"
                    color="error"
                    variant="flat"
                    class="position-absolute"
                    style="top: -18px; left: 50%; transform: translateX(-50%);"
                    @click.stop="deleteBox(page.index, boxIndex)"
                  >
                    <v-icon size="10">mdi-close</v-icon>
                  </v-btn>
                </v-fade-transition>
              </div>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  `,
});
