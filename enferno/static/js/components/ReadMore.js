const ReadMore = Vue.defineComponent({
  props: {
    previewLines: {
      type: Number,
      default: 5,
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
        const originalStyle = el.style.webkitLineClamp;
        el.style.webkitLineClamp = null;

        const fullHeight = el.scrollHeight;
        const lineHeight = parseFloat(getComputedStyle(el).lineHeight);
        const maxHeight = lineHeight * this.previewLines;

        // Restore clamp style
        el.style.webkitLineClamp = originalStyle;

        this.isTruncated = fullHeight > maxHeight + 1; // Add 1px for rounding
      });
    },
  },
  template: `
    <div>
      <div :style="previewStyle" ref="content">
        <slot />
      </div>

      <v-btn
        v-if="isTruncated"
        @click="toggle"
        variant="plain"
        :ripple="false"
        class="pa-0 mt-1"
        height="fit-content"
        width="fit-content"
        color="primary"
      >
        {{ toggleText }}
      </v-btn>
    </div>
  `,
});
