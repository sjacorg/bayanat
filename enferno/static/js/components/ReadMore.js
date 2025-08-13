const ReadMore = Vue.defineComponent({
  props: {
    previewLines: {
      type: Number,
      default: 15,
    },
  },
  data() {
    return {
      translations: window.translations,
      expanded: false,
      isTruncated: false,
      mutationObserver: null,
    };
  },
  computed: {
    toggleText() {
      return this.expanded ? this.translations.showLess_ : this.translations.showMore_;
    },
    previewStyle() {
      if (this.expanded) {
        return {}; // no clamp when expanded
      }
      return {
        display: '-webkit-box',
        WebkitLineClamp: this.previewLines,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
      };
    },
  },
  mounted() {
    this.checkTruncation();
    window.addEventListener('resize', this.checkTruncation);
    this.mutationObserver = new MutationObserver(() => {
      this.checkTruncation();
    });
    this.mutationObserver.observe(this.$refs.content, { childList: true, subtree: true, characterData: true });
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.checkTruncation);
    this.mutationObserver.disconnect();
    this.mutationObserver = null;
  },
  methods: {
    toggle() {
      this.expanded = !this.expanded;
    },
    checkTruncation() {
      this.$nextTick(() => {
        const el = this.$refs.content;
        if (!el) return;
        // Temporarily remove the clamp style to get the full height
        el.classList.add('no-clamp');

        const fullHeight = el.scrollHeight;
        const lineHeight = parseFloat(getComputedStyle(el).lineHeight);
        const maxHeight = lineHeight * this.previewLines;

        // Restore clamp style
        el.classList.remove('no-clamp');

        this.isTruncated = fullHeight > maxHeight + 1; // Add 1px for rounding
      });
    },
  },
  template: `
    <div>
      <div :style="previewStyle" ref="content">
        <slot />
      </div>

      <div class="pa-4 d-flex justify-center" v-if="isTruncated">
        <v-btn
          @click="toggle"
          variant="tonal" :append-icon="expanded ? 'mdi-chevron-up' : 'mdi-chevron-down'" color="grey" elevation="0"
        >
          {{ toggleText }}
        </v-btn>
      </div>
    </div>
  `,
});
