const OcrTextLayer = Vue.defineComponent({
  props: {
    imageUrl: { type: String, required: true },
    raw: { type: Object, default: null },
    orientation: { type: Number, default: 0 },
  },
  data() {
    return {
      naturalW: 0,
      naturalH: 0,
      renderW: 0,
      renderH: 0,
      loaded: false,
      showOverlay: true,
      revealed: false,
      scanProgress: 0,
      resizeObserver: null,
    };
  },
  computed: {
    scaleX() {
      if (!this.naturalW) return 1;
      return this.renderW / this.naturalW;
    },
    scaleY() {
      if (!this.naturalH) return 1;
      return this.renderH / this.naturalH;
    },
    paragraphs() {
      if (!this.raw || !this.naturalW) return [];
      const page = this.raw?.responses?.[0]?.fullTextAnnotation?.pages?.[0];
      if (!page) return [];

      const pw = page.width || this.naturalW;
      const ph = page.height || this.naturalH;
      const result = [];

      for (const block of page.blocks || []) {
        if (block.blockType && block.blockType !== 'TEXT') continue;
        for (const para of block.paragraphs || []) {
          const v = para.boundingBox?.vertices;
          if (!v || v.length < 4) continue;

          const xs = v.map(p => p.x || 0);
          const ys = v.map(p => p.y || 0);
          const left = Math.min(...xs) / pw * 100;
          const top = Math.min(...ys) / ph * 100;
          const width = (Math.max(...xs) - Math.min(...xs)) / pw * 100;
          const height = (Math.max(...ys) - Math.min(...ys)) / ph * 100;
          const heightPx = Math.max(...ys) - Math.min(...ys);

          // Estimate line count by looking at word bounding boxes vertical spread
          let singleLineH = heightPx;
          if (para.words && para.words.length > 0) {
            // Collect per-word heights and use median as single-line height estimate
            const wordHeights = para.words.map(w => {
              const wv = w.boundingBox?.vertices;
              if (!wv || wv.length < 4) return null;
              const wys = wv.map(p => p.y || 0);
              return Math.max(...wys) - Math.min(...wys);
            }).filter(h => h !== null && h > 0);

            if (wordHeights.length > 0) {
              wordHeights.sort((a, b) => a - b);
              const mid = Math.floor(wordHeights.length / 2);
              singleLineH = wordHeights.length % 2 !== 0
                ? wordHeights[mid]
                : (wordHeights[mid - 1] + wordHeights[mid]) / 2;
            }
          }

          const words = (para.words || []).map(w =>
            (w.symbols || []).map(s => s.text).join('')
          );

          const lang = para.property?.detectedLanguages?.[0]?.languageCode || '';
          const isRtl = ['ar', 'he', 'fa', 'ur'].includes(lang);

          result.push({ left, top, width, height, heightPx, singleLineH, text: words.join(' '), isRtl });
        }
      }
      // Sort top-to-bottom for scan reveal
      result.sort((a, b) => a.top - b.top);
      return result;
    },
  },
  methods: {
    onImageLoad(e) {
      const rect = e.target.getBoundingClientRect();
      this.naturalW = e.target.naturalWidth;
      this.naturalH = e.target.naturalHeight;
      this.renderW = rect.width;
      this.renderH = rect.height;
      this.loaded = true;

      this.resizeObserver = new ResizeObserver(() => {
        const r = this.$refs.img?.getBoundingClientRect();
        if (r) {
          this.renderW = r.width;
          this.renderH = r.height;
        }
      });
      this.resizeObserver.observe(e.target);

      // Trigger scan animation
      this.$nextTick(() => this.runScan());
    },
    runScan() {
      this.revealed = false;
      this.scanProgress = 0;
      const duration = 800;
      const start = performance.now();

      const tick = (now) => {
        const elapsed = now - start;
        this.scanProgress = Math.min(elapsed / duration, 1);
        if (this.scanProgress < 1) {
          requestAnimationFrame(tick);
        } else {
          this.revealed = true;
        }
      };
      requestAnimationFrame(tick);
    },
    paraVisible(p) {
      if (this.revealed) return true;
      // Paragraph reveals when scan line passes its top edge
      return this.scanProgress * 100 >= p.top;
    },
    paraFontSize(p) {
      const scale = Math.min(this.scaleX, this.scaleY);
      const wordCount = p.text.split(' ').length;
      const multiplier = wordCount > 10 ? 1.0 : 0.85;
      return Math.max(6, p.singleLineH * scale * multiplier);
    },
  },
  beforeUnmount() {
    this.resizeObserver?.disconnect();
  },
  template: /*html*/`
    <div class="position-relative h-100 w-100 d-flex flex-column">
      <div class="d-flex justify-end mb-1">
        <v-btn
          :icon="showOverlay ? 'mdi-eye-outline' : 'mdi-eye-off-outline'"
          size="x-small"
          variant="text"
          @click="showOverlay = !showOverlay"
        ></v-btn>
      </div>

      <div class="flex-1-1 overflow-auto d-flex justify-center align-center" style="min-height: 0;">
        <div
          class="position-relative d-inline-block"
          :style="{
            lineHeight: 0,
            transform: 'rotate(' + (orientation || 0) + 'deg)',
          }"
        >
          <img
            ref="img"
            :src="imageUrl"
            @load="onImageLoad"
            class="d-block"
            :style="{
              maxWidth: '100%',
              maxHeight: 'calc(100vh - 220px)',
              pointerEvents: 'none',
              userSelect: 'none'
            }"
          >

          <template v-if="loaded && showOverlay && paragraphs.length">
            <!-- Scan line -->
            <div
              v-if="!revealed"
              class="position-absolute"
              :style="{
                top: (scanProgress * 100) + '%',
                left: 0,
                width: '100%',
                height: '2px',
                background: 'linear-gradient(90deg, transparent, rgba(0, 200, 83, 0.8), transparent)',
                boxShadow: '0 0 8px rgba(0, 200, 83, 0.6), 0 0 20px rgba(0, 200, 83, 0.3)',
                zIndex: 2,
                transition: 'none',
              }"
            ></div>

            <!-- Paragraph highlights -->
            <div
              class="position-absolute"
              style="top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;"
            >
              <div
                v-for="(p, i) in paragraphs"
                :key="i"
                :dir="p.isRtl ? 'rtl' : 'ltr'"
                :style="{
                  position: 'absolute',
                  left: p.left + '%',
                  top: p.top + '%',
                  width: p.width + '%',
                  height: p.height + '%',
                  overflow: 'hidden',
                  background: paraVisible(p) ? 'rgba(0, 200, 83, 0.1)' : 'transparent',
                  borderLeft: paraVisible(p) ? '2px solid rgba(0, 200, 83, 0.4)' : 'none',
                  borderRadius: '2px',
                  pointerEvents: paraVisible(p) ? 'auto' : 'none',
                  cursor: 'text',
                  userSelect: 'text',
                  opacity: paraVisible(p) ? 1 : 0,
                  transition: 'opacity 0.3s ease, background 0.3s ease',
                }"
              >
                <span
                  :style="{
                    fontSize: paraFontSize(p) + 'px',
                    lineHeight: '1.2',
                    color: 'transparent',
                    whiteSpace: 'normal',
                    wordBreak: 'break-word',
                    display: 'block',
                    width: '100%',
                  }"
                >{{ p.text }}</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  `,
});