const SplitView = Vue.defineComponent({
  props: {
    initialLeftWidth: {
      type: Number,
      default: () => window.innerWidth / 2,
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
      ro: null,
      overlayEl: null,
      isHovering: false,
      isDragging: false,
      leftWidth: this.initialLeftWidth,
      currentX: 0,
      frameRequested: false,
      hasInitialized: false,
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
    this.ro = new ResizeObserver(() => {
      const width = this.$el?.offsetWidth || 0;
      this.currentWidth = width;
  
      // Only set leftWidth the first time (or if needed)
      if (!this.hasInitialized && width > 0) {
        this.leftWidth = width / 2;
        this.hasInitialized = true;
      }
    });
  
    this.ro.observe(this.$el);
  },
  beforeUnmount() {
    if (this.ro) {
      this.ro.disconnect();
    }
  },
  methods: {
    resetToCenter() {
      this.leftWidth = this.currentWidth / 2;
    },
    hoverHandle(e) {
      this.isHovering = true;
    },
    leaveHandle(e) {
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
    
      this.createOverlay?.(); // optional overlay
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
      const mWidth = this.currentWidth * 0.25; // Leave 25% space on each side
      const containerWidth = this.currentWidth; // live value
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
        this.$emit('leftWidthChanged', `${leftWidth + 16}px`);
        this.$emit('rightWidthChanged', `calc(100% - ${leftWidth + 48}px)`);
      }
    },
  },
  template: `
      <div
        class="d-flex"
        :style="containerStyle"
      >
        <div
          v-show="leftSlotVisible"
          :style="{ width: leftWidth + 'px' }"
        >
          <slot name="left" />
        </div>

        <div
            v-if="leftSlotVisible"
            @mousedown="startDrag"
            @mouseenter="hoverHandle"
            @mouseleave="leaveHandle"
            :class="['d-flex justify-center position-relative', dividerClass]"
            style="cursor: ew-resize; width: 24px;"
        >
            <v-btn v-if="isHandleHighlighted" icon="mdi-arrow-split-vertical" class="position-absolute" height="24" width="24" style="top: 24px" :variant="isHandleHighlighted ? 'flat' : 'elevated'" :color="isHandleHighlighted ? 'primary' : undefined"></v-btn>
            <v-divider
                vertical
                :thickness="isHandleHighlighted ? 3 : 1"
                :color="isHandleHighlighted ? 'primary' : undefined"
                :opacity="isHandleHighlighted ? 1 : undefined"
                style="height: 100%"
            ></v-divider>
        </div>

        <div :style="{ width: 'calc(100% - ' + leftWidth + 'px)' }">
          <slot name="right" />
        </div>
      </div>
    `,
});
