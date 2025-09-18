const ScrollableCard = Vue.defineComponent({
  inheritAttrs: false,
  props: {
    containerProps: {
      type: Object,
      default: () => ({}),
    },
    cardProps: {
      type: Object,
      default: () => ({}),
    },
  },
  data: () => ({
    topEnabled: false,
    bottomEnabled: false,
    isOverflow: false,
  }),
  mounted() {
    this.checkOverflow();
    window.addEventListener("resize", this.checkOverflow);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.checkOverflow);
  },
  methods: {
    checkOverflow() {
      const el = this.$refs.scrollContainer;
      if (!el) return;

      this.isOverflow = el.scrollHeight > el.clientHeight
      this.topEnabled = el.scrollTop > 0;
      this.bottomEnabled = el.scrollHeight > el.clientHeight + el.scrollTop;
    },
    scroll(to) {
        const el = this.$refs.scrollContainer;
        if (!el) return;

        if (to === 'top') {
            el.scrollTo({ top: 0, behavior: 'smooth' });
        } else if (to === 'bottom') {
            el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
        }

        this.$nextTick(this.checkOverflow);
    },
  },
  template: /*html*/ `
      <v-card
        class="position-relative"
        v-bind="cardProps"
      >
        <!-- Top button -->
        <v-btn
            v-if="isOverflow"
            :disabled="!topEnabled"
            icon="mdi-chevron-up"
            size="x-small"
            variant="outlined"
            class="d-flex mx-auto mb-2"
            @click="scroll('top')"
        ></v-btn>
        <div ref="scrollContainer" @scroll="checkOverflow" class="overflow-auto" v-bind="containerProps">
            <slot></slot>
        </div>
        <!-- Bottom button -->
        <v-btn
            v-if="isOverflow"
            :disabled="!bottomEnabled"
            icon="mdi-chevron-down"
            size="x-small"
            variant="outlined"
            class="d-flex mx-auto mt-2"
            @click="scroll('bottom')"
        ></v-btn>
      </v-card>
  `,
});
