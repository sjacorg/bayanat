const SplitView = Vue.defineComponent({
  props: {
    initialLeftWidth: {
      type: Number,
      default: () => window.innerWidth / 2,
    },
    minWidth: {
      type: Number,
      default: 100,
    },
  },
  data() {
    return {
      overlayEl: null,
      isHovering: false,
      isDragging: false,
      leftWidth: this.initialLeftWidth,
      currentX: 0,
      frameRequested: false,
    };
  },
  computed: {
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
    document.addEventListener('mousemove', this.queueDragFrame);
    document.addEventListener('mouseup', this.stopDrag);
  },
  beforeUnmount() {
    document.removeEventListener('mousemove', this.queueDragFrame);
    document.removeEventListener('mouseup', this.stopDrag);
  },
  methods: {
    hoverHandle(e) {
      this.isHovering = true;
    },
    leaveHandle(e) {
      this.isHovering = false;
    },
    startDrag(e) {
      if (e.button !== 0) return;

      this.isDragging = true;
      this.currentX = e.clientX;
      this.containerWidth = this.$el.offsetWidth;
      document.body.style.cursor = 'ew-resize';
      this.createOverlay();
    },
    stopDrag() {
      if (!this.isDragging) return;
      this.isDragging = false;
      this.frameRequested = false;
      document.body.style.cursor = '';
      this.removeOverlay();
    },
    queueDragFrame(e) {
      if (!this.isDragging) return;
      this.currentX = e.clientX;

      if (!this.frameRequested) {
        this.frameRequested = true;
        requestAnimationFrame(this.doDrag);
      }
    },
    doDrag() {
      const max = this.containerWidth - this.minWidth;
      const newWidth = Math.min(Math.max(this.currentX, this.minWidth), max);

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
  template: `
      <div
        class="d-flex"
        :style="containerStyle"
      >
        <div
          :style="{ width: leftWidth + 'px' }"
        >
          <slot name="left" />
        </div>

        <div
            @mousedown="startDrag"
            @mouseenter="hoverHandle"
            @mouseleave="leaveHandle"
            class="mx-4 d-flex justify-center"
        
        style="cursor: ew-resize; width: 24px; ">
            <v-divider
                vertical
                :thickness="isHandleHighlighted ? 3 : 1"
                :color="isHandleHighlighted ? 'primary' : undefined"
                :opacity="isHandleHighlighted ? 1 : undefined"
                style="height: 100%"
            ></v-divider>
        </div>

        <div class="flex-grow-1">
          <slot name="right" />
        </div>
      </div>
    `,
});
