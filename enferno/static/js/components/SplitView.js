const SplitView = Vue.defineComponent({
  props: {
    leftWidthPercent: {
      type: Number,
      default: 25,
    },
    sideSafeAreaPercent: {
      type: Number,
      default: 25,
    },
    leftSlotVisible: {
      type: Boolean,
      default: true,
    },
    dividerClass: {
      type: String,
      default: '',
    },
  },
  emits: ['leftWidthChanged', 'rightWidthChanged'],
  data() {
    return {
      dividerWidth: 24,
      ro: null,
      overlayEl: null,
      isHovering: false,
      isDragging: false,
      leftWidth: window.innerWidth / 2,
      currentWidth: window.innerWidth,
      frameRequested: false,
      hasInitialized: false,
    };
  },
  computed: {
    halfDividerWidth() {
      return this.dividerWidth / 2;
    },
    containerStyle() {
      return {
        width: '100%',
        userSelect: this.isDragging ? 'none' : 'auto',
      };
    },
    isHandleHighlighted() {
      return this.isDragging || this.isHovering;
    },
  },
  mounted() {
    this.ro = new ResizeObserver(() => {
      this.onResize();
    });
    this.ro.observe(this.$el);
  },
  beforeUnmount() {
    if (this.ro) {
      this.ro.disconnect();
    }
  },
  methods: {
    onResize() {
      const width = this.$el?.offsetWidth || 0;
      this.currentWidth = width;

      const min = width * (this.sideSafeAreaPercent / 100);
      const max = width - min;

      if (!this.hasInitialized && width > 0) {
        this.leftWidth = width * (this.leftWidthPercent / 100);
        this.hasInitialized = true;
      }

      if (this.leftWidth < min || this.leftWidth > max) {
        this.resetToCenter();
      }
    },
    resetToCenter() {
      this.leftWidth = this.currentWidth / 2;
    },
    hoverHandle() {
      this.isHovering = true;
    },
    leaveHandle() {
      this.isHovering = false;
    },
    startDrag(e) {
      if (e.button !== 0) return;
      const bounds = this.$el.getBoundingClientRect();
      this.currentX = e.clientX - bounds.left;
      this.isDragging = true;
      document.addEventListener('mousemove', this.queueDragFrame);
      document.addEventListener('mouseup', this.stopDrag);
      document.body.style.cursor = 'ew-resize';
      this.createOverlay?.();
    },
    stopDrag() {
      if (!this.isDragging) return;
      this.isDragging = false;
      this.frameRequested = false;
      document.body.style.cursor = '';
      document.removeEventListener('mousemove', this.queueDragFrame);
      document.removeEventListener('mouseup', this.stopDrag);
      this.removeOverlay?.();
    },
    queueDragFrame(e) {
      if (!this.isDragging) return;
      const bounds = this.$el.getBoundingClientRect();
      this.currentX = e.clientX - bounds.left;
      if (!this.frameRequested) {
        this.frameRequested = true;
        requestAnimationFrame(this.doDrag);
      }
    },
    doDrag() {
      const mWidth = this.currentWidth * (this.sideSafeAreaPercent / 100);
      const containerWidth = this.currentWidth;
      const max = containerWidth - mWidth;
      const newWidth = Math.min(Math.max(this.currentX, mWidth), max);

      if (this.leftWidth !== newWidth) {
        this.leftWidth = newWidth;
      }

      this.frameRequested = false;
    },
    createOverlay() {
      const el = document.createElement('div');
      el.style.position = 'fixed';
      el.style.top = 0;
      el.style.left = 0;
      el.style.right = 0;
      el.style.bottom = 0;
      el.style.zIndex = 9999;
      el.style.cursor = 'ew-resize';
      el.style.pointerEvents = 'all';
      el.style.background = 'transparent';
      document.body.appendChild(el);
      this.overlayEl = el;
    },
    removeOverlay() {
      if (this.overlayEl) {
        document.body.removeChild(this.overlayEl);
        this.overlayEl = null;
      }
    },
  },
  watch: {
    leftWidth: {
      immediate: true,
      handler(leftWidth) {
        this.$emit('leftWidthChanged', `${leftWidth - this.halfDividerWidth}px`);
        this.$emit('rightWidthChanged', `calc(100% - ${leftWidth + this.halfDividerWidth}px)`);
      }
    },
    leftSlotVisible(val) {
      if (val) this.resetToCenter();
    }
  },
  template: `
    <div class="d-flex h-100" :style="containerStyle">
      <div
        v-show="leftSlotVisible"
        class="flex-shrink-0 overflow-y-auto"
        :style="{ width: (leftWidth - halfDividerWidth) + 'px' }"
      >
        <slot name="left" />
      </div>

      <div
        v-if="leftSlotVisible"
        @mousedown="startDrag"
        @mouseenter="hoverHandle"
        @mouseleave="leaveHandle"
        :class="['d-flex justify-center position-relative flex-shrink-0', dividerClass]"
        :style="'cursor: ew-resize; width: ' + dividerWidth + 'px;'"
      >
        <v-btn
          v-if="isHandleHighlighted"
          icon="mdi-arrow-split-vertical"
          class="position-absolute"
          height="24"
          width="24"
          style="top: 24px"
          :variant="isHandleHighlighted ? 'flat' : 'elevated'"
          :color="isHandleHighlighted ? 'primary' : undefined"
        ></v-btn>
        <v-divider
          vertical
          :thickness="isHandleHighlighted ? 3 : 1"
          :color="isHandleHighlighted ? 'primary' : undefined"
          :opacity="isHandleHighlighted ? 1 : undefined"
          style="height: 100%"
        ></v-divider>
      </div>

      <div
        class="flex-shrink-0 overflow-y-auto"
        :style="{ width: leftSlotVisible ? 'calc(100% - ' + (leftWidth + halfDividerWidth) + 'px)' : '100%' }"
      > 
        <slot name="right" />
      </div>
    </div>
  `,
});

export default SplitView;