const REDACTOR_MAX_ZOOM = 6;

const MediaRedactor = Vue.defineComponent({
  props: {
    modelValue: { type: Boolean, default: false },
    media: { type: Object, default: null },
  },
  emits: ['update:modelValue', 'redacted'],

  data() {
    return {
      REDACTOR_MAX_ZOOM,
      loading: false,
      saving: false,
      error: null,
      translations: window.translations,
      redactionMode: 'redact',
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
      baseWidth: 0,
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
      if (!this.media?.id) return null;
      // Bust the browser cache when a copy is re-edited in place (filename stays, bytes change).
      const v = this.media.etag ? `?v=${this.media.etag}` : '';
      return `/admin/api/media/${this.media.id}/proxy${v}`;
    },
    isRedactedCopy() {
      return !!(this.media?.isRedaction || this.media?.originalMediaId);
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
    isMobileView() {
      return !!this.$vuetify?.display?.mobile;
    },
    isDarkTheme() {
      return !!this.$vuetify?.theme?.current?.dark;
    },
    scrollPaneClasses() {
      return this.isDarkTheme ? 'bg-grey-darken-4' : 'bg-grey-lighten-3';
    },
    modeHint() {
      return this.redactionMode === 'reveal'
        ? {
            boxHint: this.translations.clickDragToDrawAVisibleWindow_,
          }
        : {
            boxHint: this.translations.clickDragToDrawABlackBox_,
          };
    },
    orientation() {
      return this.media?.orientation || 0;
    },
    imageStyle() {
      return (page) => {
        const o = this.orientation;
        if ((o === 90 || o === 270) && page.width && page.height) {
          // Container: width=CW, height=CW*(W/H) (swapped aspect-ratio H/W).
          // Image pre-rotation must be W×H to visually fill CW×(CW*W/H) after rotating.
          // width as % of CW: W/H * 100%
          // height as % of containerHeight (CW*W/H): need CW → CW/(CW*W/H) = H/W → (H/W)*100%
          return {
            position: 'absolute',
            top: '50%',
            left: '50%',
            width: `${(page.width / page.height) * 100}%`,
            height: `${(page.height / page.width) * 100}%`,
            objectFit: 'fill',
            transform: `translate(-50%, -50%) rotate(${o}deg)`,
          };
        }
        return { transform: `rotate(${o}deg)`, width: '100%' };
      };
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
        window.addEventListener('resize', this._resizeHandler);
        this._resizeObserver?.observe?.(this._scrollPane || document.body);
      } else {
        this._scrollPane?.removeEventListener('touchmove', this._touchMoveHandler);
        this._scrollPane?.removeEventListener('wheel', this._wheelHandler);
        this._scrollPane = null;
        window.removeEventListener('keydown', this._keydownHandler);
        window.removeEventListener('keyup', this._keyupHandler);
        window.removeEventListener('resize', this._resizeHandler);
        this._resizeObserver?.disconnect?.();
        this.reset();
      }
    },
    media() {
      if (this.show) this.load();
    },
  },

  created() {
    this._pdf = null;
    this._loadId = 0;
    this._touchMoveHandler = (e) => this.onTouchMove(e);
    this._wheelHandler = (e) => this.onWheel(e);
    this._keydownHandler = (e) => this.onKeydown(e);
    this._keyupHandler = (e) => this.onKeyup(e);
    this._resizeHandler = () => this.onViewportResize();
    this._resizeObserver = typeof ResizeObserver !== 'undefined'
      ? new ResizeObserver(() => this.onViewportResize())
      : null;
  },

  beforeUnmount() {
    this._scrollPane?.removeEventListener('touchmove', this._touchMoveHandler);
    this._scrollPane?.removeEventListener('wheel', this._wheelHandler);
    window.removeEventListener('keydown', this._keydownHandler);
    window.removeEventListener('keyup', this._keyupHandler);
    window.removeEventListener('resize', this._resizeHandler);
    this._resizeObserver?.disconnect?.();
    this._pdf?.destroy?.();
  },

  methods: {
    reset() {
      this._loadId++;
      this.loading = false;
      this.saving = false;
      this.error = null;
      this.redactionMode = 'redact';
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
      this.baseWidth = 0;
      this.pinchStartDistance = null;
      this.pinchStartZoom = 1;
      this._pdf?.destroy?.();
      this._pdf = null;
    },
    onViewportResize() {
      this.baseWidth = 0;
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
      this.error = this.translations.unsupportedFileType_;
    },
    async loadPdf() {
      const loadId = this._loadId;
      this.loading = true;
      try {
        await loadScript('/static/js/pdf.js/pdf.min.mjs');
        pdfjsLib.GlobalWorkerOptions.workerSrc = '/static/js/pdf.js/pdf.worker.min.mjs';
        const pdf = await pdfjsLib.getDocument({ url: this.src, disableStream: true, disableRange: true }).promise;
        if (loadId !== this._loadId) { pdf.destroy(); return; }
        this._pdf = pdf;
        const pages = [];
        for (let index = 0; index < pdf.numPages; index++) {
          const page = await pdf.getPage(index + 1);
          if (loadId !== this._loadId) return;
          const viewport = page.getViewport({ scale: 1 });
          pages.push({ index, width: viewport.width, height: viewport.height });
          this.boxes[index] = [];
          await page.cleanup();
        }
        if (loadId !== this._loadId) return;
        this.pages = pages;
        this.loading = false;
        await this.$nextTick();
        for (const page of pages) {
          if (loadId !== this._loadId) return;
          await this.renderPdfPage(page.index);
        }
      } catch (e) {
        if (loadId !== this._loadId) return;
        console.error('PDF redactor load failed:', e);
        this.error = this.translations.failedToLoadDocument_;
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
        page.index === index ? { ...page, width: viewport.width, height: viewport.height } : page
      );
    },
    pageRect(index) {
      return this.$refs[`page-${index}`]?.[0]?.getBoundingClientRect?.()
        || this.$refs[`page-${index}`]?.getBoundingClientRect?.();
    },
    normalizedPoint(index, event) {
      const rect = this.pageRect(index);
      const source = event.changedTouches?.[0] || event.touches?.[0] || event;
      const x = Math.min(Math.max((source.clientX - rect.left) / rect.width, 0), 1);
      const y = Math.min(Math.max((source.clientY - rect.top) / rect.height, 0), 1);
      return { x, y };
    },
    startBox(index, event) {
      if (this.isMobileView) return;
      if ((event.button !== undefined && event.button !== 0) || this.spaceDown) return;
      event.currentTarget?.setPointerCapture?.(event.pointerId);
      const point = this.normalizedPoint(index, event);
      this.draft = { page: index, startX: point.x, startY: point.y, x: point.x, y: point.y, w: 0, h: 0 };
    },
    startDrag(pageIndex, boxIndex, event) {
      if (this.isMobileView) return;
      if (event.pointerType === 'touch') return;
      if (event.button !== undefined && event.button !== 0) return;
      event.stopPropagation();
      event.currentTarget?.setPointerCapture?.(event.pointerId);
      this.activeBox = { page: pageIndex, box: boxIndex };
      const point = this.normalizedPoint(pageIndex, event);
      const box = this.boxes[pageIndex][boxIndex];
      this.drag = { page: pageIndex, boxIndex, startMouseX: point.x, startMouseY: point.y, origX: box.x, origY: box.y };
    },
    // corner: 'tl' | 'tr' | 'bl' | 'br' — the corner being dragged; opposite corner is the anchor
    startResize(pageIndex, boxIndex, corner, event) {
      if (this.isMobileView) return;
      if (event.pointerType === 'touch') return;
      if (event.button !== undefined && event.button !== 0) return;
      event.stopPropagation();
      event.currentTarget?.setPointerCapture?.(event.pointerId);
      this.activeBox = { page: pageIndex, box: boxIndex };
      const box = this.boxes[pageIndex][boxIndex];
      const anchorX = corner.includes('l') ? box.x + box.w : box.x;
      const anchorY = corner.includes('t') ? box.y + box.h : box.y;
      this.resize = { page: pageIndex, boxIndex, anchorX, anchorY };
    },
    moveBox(index, event) {
      if (this.isMobileView) return;
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
    finishBox(event) {
      if (this.isMobileView) return;
      if (event?.currentTarget?.hasPointerCapture?.(event.pointerId)) {
        event.currentTarget.releasePointerCapture(event.pointerId);
      }
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
      if (this.isMobileView) return;
      const pageBoxes = [...(this.boxes[pageIndex] || [])];
      pageBoxes.splice(boxIndex, 1);
      this.boxes = { ...this.boxes, [pageIndex]: pageBoxes };
      if (this.hoveredBox?.page === pageIndex && this.hoveredBox?.box === boxIndex) this.hoveredBox = null;
      if (this.activeBox?.page === pageIndex && this.activeBox?.box === boxIndex) this.activeBox = null;
    },
    onKeydown(event) {
      if (this.isMobileView) return;
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
      if (!this.spaceDown || (event.button !== undefined && event.button !== 0)) return;
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
    revealOverlayPath(pageIndex) {
      const boxes = this.visibleBoxes(pageIndex);
      const path = ['M 0 0 H 100 V 100 H 0 Z'];
      for (const box of boxes) {
        const left = +(box.x * 100).toFixed(4);
        const top = +(box.y * 100).toFixed(4);
        const right = +((box.x + box.w) * 100).toFixed(4);
        const bottom = +((box.y + box.h) * 100).toFixed(4);
        path.push(`M ${left} ${top} H ${right} V ${bottom} H ${left} Z`);
      }
      return path.join(' ');
    },
    normalizeRect(rect) {
      const x0 = Math.max(0, Math.min(rect.x, 1));
      const y0 = Math.max(0, Math.min(rect.y, 1));
      const x1 = Math.max(x0, Math.min(rect.x + rect.w, 1));
      const y1 = Math.max(y0, Math.min(rect.y + rect.h, 1));
      return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    },
    mergeRects(rects) {
      const epsilon = 0.000001;
      let current = rects.map(rect => this.normalizeRect(rect)).filter(rect => rect.w > epsilon && rect.h > epsilon);
      let changed = true;
      while (changed) {
        current.sort((a, b) => (a.y - b.y) || (a.x - b.x) || (a.h - b.h) || (a.w - b.w));
        changed = false;
        const next = [];
        const used = new Array(current.length).fill(false);
        for (let i = 0; i < current.length; i++) {
          if (used[i]) continue;
          let rect = current[i];
          for (let j = i + 1; j < current.length; j++) {
            if (used[j]) continue;
            const other = current[j];
            const sameRow = Math.abs(rect.y - other.y) < epsilon && Math.abs(rect.h - other.h) < epsilon;
            const touchesHorizontally = sameRow && Math.abs(rect.x + rect.w - other.x) < epsilon;
            const sameColumn = Math.abs(rect.x - other.x) < epsilon && Math.abs(rect.w - other.w) < epsilon;
            const touchesVertically = sameColumn && Math.abs(rect.y + rect.h - other.y) < epsilon;
            if (touchesHorizontally) {
              rect = { x: rect.x, y: rect.y, w: rect.w + other.w, h: rect.h };
              used[j] = true;
              changed = true;
            } else if (touchesVertically) {
              rect = { x: rect.x, y: rect.y, w: rect.w, h: rect.h + other.h };
              used[j] = true;
              changed = true;
            }
          }
          used[i] = true;
          next.push(rect);
        }
        current = next;
      }
      return current;
    },
    revealRectsToRedactionRects(rects) {
      if (!rects.length) return [];
      const normalizedRects = this.mergeRects(rects);
      const xEdges = Array.from(new Set([0, 1, ...normalizedRects.flatMap(rect => [rect.x, rect.x + rect.w])])).sort((a, b) => a - b);
      const yEdges = Array.from(new Set([0, 1, ...normalizedRects.flatMap(rect => [rect.y, rect.y + rect.h])])).sort((a, b) => a - b);
      const maskedRects = [];

      for (let yi = 0; yi < yEdges.length - 1; yi++) {
        for (let xi = 0; xi < xEdges.length - 1; xi++) {
          const x0 = xEdges[xi];
          const x1 = xEdges[xi + 1];
          const y0 = yEdges[yi];
          const y1 = yEdges[yi + 1];
          if (x1 <= x0 || y1 <= y0) continue;
          const midX = (x0 + x1) / 2;
          const midY = (y0 + y1) / 2;
          const insideReveal = normalizedRects.some(rect =>
            midX >= rect.x && midX <= rect.x + rect.w && midY >= rect.y && midY <= rect.y + rect.h
          );
          if (!insideReveal) {
            maskedRects.push({ x: x0, y: y0, w: x1 - x0, h: y1 - y0 });
          }
        }
      }

      return this.mergeRects(maskedRects);
    },
    toggleRevealMode() {
      this.redactionMode = this.redactionMode === 'reveal' ? 'redact' : 'reveal';
    },
    zoomIn() {
      this.zoom = Math.min(+(this.zoom + 0.25).toFixed(2), REDACTOR_MAX_ZOOM);
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
        const next = Math.min(Math.max(this.pinchStartZoom * scale, 1), REDACTOR_MAX_ZOOM);
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
      if (!this.baseWidth) {
        const wrapper = pane.querySelector('.redactor-pages');
        this.baseWidth = wrapper ? wrapper.getBoundingClientRect().width : pane.clientWidth;
      }
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
      const next = Math.min(Math.max(this.zoom * factor, 1), REDACTOR_MAX_ZOOM);
      this.applyZoom(next, event.clientX, event.clientY);
    },
    async submit(overwrite = false) {
      if (!this.canSubmit) return;
      this.saving = true;
      const pages = Object.entries(this.boxes)
        .filter(([, rects]) => rects.length)
        .map(([page, rects]) => {
          const sourceRects = this.mergeRects(rects);
          // Reveal mode is a client-side UX layer: users draw visible windows,
          // then we convert them into standard blackout rects before saving.
          return {
            page: Number(page),
            mode: this.redactionMode,
            rects: this.redactionMode === 'reveal' ? this.revealRectsToRedactionRects(sourceRects) : sourceRects,
            revealRects: this.redactionMode === 'reveal' ? sourceRects : undefined,
          };
        });
      try {
        const response = await api.post(`/admin/api/media/${this.media.id}/redact`, {
          mode: this.redactionMode,
          pages,
          title: this.label.trim(),
          overwrite,
        });
        this.$emit('redacted', response.data.data);
        this.show = false;
      } catch (e) {
        this.$root.showSnack(e.response?.data?.message || this.translations.failedToSaveRedaction_);
      } finally {
        this.saving = false;
      }
    },
  },

  template: /*html*/`
    <v-dialog v-model="show" fullscreen scrollable persistent @keydown.esc.prevent no-click-animation>
      <v-card>
        <v-toolbar color="dark-primary" :density="$vuetify.display.mobile ? 'comfortable' : 'default'">
          <v-icon icon="mdi-marker" class="ml-3 mr-2" size="20"></v-icon>
          <v-toolbar-title style="min-width: 0;" :class="$vuetify.display.mobile ? 'me-2' : ''">
            <div :class="$vuetify.display.mobile ? 'text-subtitle-1' : 'font-weight-medium'" class="text-truncate">{{ translations.redactionTool_ }}</div>
            <div class="font-weight-regular opacity-70 text-truncate" :class="$vuetify.display.mobile ? 'text-caption' : 'text-body-2'">{{ media?.title || media?.filename || translations.document_ }}</div>
          </v-toolbar-title>
          <v-spacer></v-spacer>
          <v-text-field
            v-if="!isMobileView"
            v-model="label"
            density="comfortable"
            variant="solo"
            hide-details
            :label="translations.copyName_"
            prepend-inner-icon="mdi-tag-outline"
            class="mx-3"
            max-width="300"
          ></v-text-field>
          <v-tooltip location="bottom" :disabled="canSubmit">
            <template #activator="{ props }">
              <div v-if="!isMobileView" v-bind="props" class="d-flex align-center">
                <v-btn
                  v-if="isRedactedCopy"
                  prepend-icon="mdi-content-save-edit-outline"
                  variant="elevated"
                  :disabled="!canSubmit"
                  :loading="saving"
                  @click="submit(true)"
                  class="mr-2"
                >{{ translations.saveChanges_ }}</v-btn>
                <v-btn
                  :prepend-icon="isRedactedCopy ? 'mdi-content-save-plus-outline' : 'mdi-content-save-outline'"
                  :variant="isRedactedCopy ? 'tonal' : 'elevated'"
                  :disabled="!canSubmit"
                  :loading="saving"
                  @click="submit(false)"
                  class="mr-2"
                >{{ isRedactedCopy ? translations.saveAsNewCopy_ : translations.saveCopy_ }}</v-btn>
              </div>
            </template>
            <span v-if="!isMobileView">{{ redactionMode === 'reveal' ? translations.drawAtLeastOneRevealWindowOnTheDocumentToSave_ : translations.drawAtLeastOneBlackBoxOnTheDocumentToSave_ }}</span>
          </v-tooltip>
          <template #append>
            <v-btn icon="mdi-close" variant="text" @click="show = false"></v-btn>
          </template>
        </v-toolbar>

        <v-toolbar density="compact" class="border-b" :class="$vuetify.display.mobile ? 'px-2 py-2' : ''">
          <div class="d-flex align-center w-100" :class="$vuetify.display.mobile ? 'flex-wrap ga-2' : 'ga-1'">
          <v-btn
            v-if="!isMobileView"
            :color="redactionMode === 'reveal' ? 'success' : 'default'"
            :variant="redactionMode === 'reveal' ? 'flat' : 'outlined'"
            :prepend-icon="redactionMode === 'reveal' ? 'mdi-check' : 'mdi-selection-search'"
            class="ml-4"
            @click="toggleRevealMode"
          >{{ translations.revealMode_ }}</v-btn>
          <v-chip v-if="!isMobileView" size="small" variant="text" class="text-caption opacity-70">{{ modeHint.boxHint }}</v-chip>
          <v-chip v-if="!isMobileView" size="small" variant="text" prepend-icon="mdi-arrow-all" class="text-caption opacity-70">{{ translations.dragBoxToReposition_ }}</v-chip>
          <v-chip v-if="!isMobileView" size="small" variant="text" prepend-icon="mdi-delete-outline" class="text-caption opacity-70">{{ translations.clickBoxThenDeleteToRemove_ }}</v-chip>
          <v-chip v-if="!isMobileView" size="small" variant="text" prepend-icon="mdi-hand-back-right-outline" class="text-caption opacity-70">{{ translations.holdSpaceAndDragToPan_ }}</v-chip>
          <v-spacer></v-spacer>
          <v-btn icon="mdi-minus" variant="tonal" density="compact" :disabled="zoom <= 1" @click="zoomOut"></v-btn>
          <span class="text-body-2 mx-1" style="min-width: 44px; text-align: center;">{{ Math.round(zoom * 100) }}%</span>
          <v-btn icon="mdi-plus" variant="tonal" density="compact" :disabled="zoom >= REDACTOR_MAX_ZOOM" @click="zoomIn"></v-btn>
          <v-btn variant="tonal" density="compact" size="large" :class="$vuetify.display.mobile ? '' : 'mx-2'" @click="zoomFit">{{ translations.fit_ }}</v-btn>
          </div>
        </v-toolbar>

        <v-alert v-if="error" type="error" variant="tonal" class="ma-3">{{ error }}</v-alert>
        <v-card-text
          ref="scrollPane"
          class="pa-0"
          :class="scrollPaneClasses"
          style="overflow: auto;"
          :style="{
            touchAction: zoom > 1 ? 'pan-x pan-y' : 'pan-y',
            cursor: panning ? 'grabbing' : spaceDown ? 'grab' : 'default',
          }"
          @mousedown="onPanStart"
          @mousemove="onPanMove"
          @mouseup="onPanEnd"
          @mouseleave="onPanEnd"
          @touchstart="onTouchStart"
          @touchend="onTouchEnd"
          @touchcancel="onTouchEnd"
        >
          <div
            v-if="isMobileView"
            class="px-3 pt-3"
          >
            <v-alert
              type="info"
              variant="tonal"
              density="compact"
              rounded="lg"
              class="mb-0"
            >{{ translations.redactionEditingIsAvailableOnDesktopOnly_ }}</v-alert>
          </div>
          <div v-if="loading" class="d-flex align-center justify-center" style="height: 70vh;">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
          </div>
          <div v-else
            class="d-flex flex-column align-center ga-4 redactor-pages"
            :class="$vuetify.display.mobile ? 'pa-2' : 'pa-4'"
            :style="{ width: zoom > 1 ? (zoom * baseWidth) + 'px' : '100%', minWidth: '100%' }"
          >
            <div
              v-for="page in pages"
              :key="page.index"
              class="position-relative bg-white elevation-2"
              :style="{ width: '100%', lineHeight: 0, userSelect: 'none', aspectRatio: (orientation === 90 || orientation === 270) ? page.height + ' / ' + page.width : page.width + ' / ' + page.height }"
              :ref="'page-' + page.index"
              style="touch-action: none;"
              @pointerdown.prevent="activeBox = null; startBox(page.index, $event)"
              @pointermove.prevent="moveBox(page.index, $event)"
              @pointerup.prevent="finishBox"
              @pointercancel="finishBox"
            >
              <canvas
                v-if="mediaKind === 'pdf'"
                :ref="'redactCanvas-' + page.index"
                class="w-100 d-block"
              ></canvas>
              <img
                v-else
                :src="src"
                class="d-block"
                draggable="false"
                :style="imageStyle(page)"
                @load="page.width = $event.target.naturalWidth; page.height = $event.target.naturalHeight"
              >

              <svg
                v-if="redactionMode === 'reveal'"
                class="position-absolute"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                style="inset: 0; width: 100%; height: 100%; pointer-events: none; z-index: 1;"
              >
                <path
                  :d="revealOverlayPath(page.index)"
                  fill="rgba(0,0,0,0.76)"
                  fill-rule="evenodd"
                ></path>
              </svg>

              <template v-for="(pageBoxes, _) in [visibleBoxes(page.index)]" :key="0">
              <div
                v-for="(box, boxIndex) in pageBoxes"
                :key="boxIndex"
                class="position-absolute"
                :style="{
                  left: (box.x * 100) + '%',
                  top: (box.y * 100) + '%',
                  width: (box.w * 100) + '%',
                  height: (box.h * 100) + '%',
                  padding: '7px',
                  margin: '-7px',
                  boxSizing: 'content-box',
                  pointerEvents: draft && boxIndex === pageBoxes.length - 1 ? 'none' : 'auto',
                  zIndex: 5,
                }"
                @pointerdown.prevent="startDrag(page.index, boxIndex, $event)"
                @mouseenter="hoveredBox = { page: page.index, box: boxIndex }"
                @mouseleave="hoveredBox = null"
              >
                <div
                  class="position-relative"
                  :style="{
                    width: '100%',
                    height: '100%',
                    background: redactionMode === 'reveal' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.82)',
                    border: (hoveredBox?.page === page.index && hoveredBox?.box === boxIndex) || (activeBox?.page === page.index && activeBox?.box === boxIndex) ? '2px solid rgb(var(--v-theme-primary))' : '1px solid #111',
                    cursor: 'move',
                    boxShadow: redactionMode === 'reveal' ? '0 0 0 1px rgba(255,255,255,0.9) inset' : 'none',
                  }"
                >
                  <template v-if="!(draft && boxIndex === pageBoxes.length - 1) && ((hoveredBox?.page === page.index && hoveredBox?.box === boxIndex) || (activeBox?.page === page.index && activeBox?.box === boxIndex))">
                    <div
                      v-for="corner in ['tl','tr','bl','br']"
                      :key="corner"
                      class="position-absolute bg-white"
                      :style="{
                        width: '7px', height: '7px',
                        top: corner.includes('t') ? '-4px' : 'auto',
                        bottom: corner.includes('b') ? '-4px' : 'auto',
                        left: corner.includes('l') ? '-4px' : 'auto',
                        right: corner.includes('r') ? '-4px' : 'auto',
                        cursor: corner === 'tl' || corner === 'br' ? 'nwse-resize' : 'nesw-resize',
                        border: '1.5px solid #333',
                        borderRadius: '1px',
                        zIndex: 20,
                      }"
                      @pointerdown.prevent.stop="startResize(page.index, boxIndex, corner, $event)"
                    ></div>
                  </template>
                </div>
                <v-fade-transition>
                  <v-btn
                    v-if="!(draft && boxIndex === pageBoxes.length - 1) && ((hoveredBox?.page === page.index && hoveredBox?.box === boxIndex) || (activeBox?.page === page.index && activeBox?.box === boxIndex))"
                    size="18"
                    color="error"
                    variant="flat"
                    class="position-absolute"
                    style="top: -18px; left: 50%; transform: translateX(-50%);"
                    @pointerdown.stop
                    @click.stop="deleteBox(page.index, boxIndex)"
                  >
                    <v-icon size="10">mdi-close</v-icon>
                  </v-btn>
                </v-fade-transition>
              </div>
              </template>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>
  `,
});
