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
          height: '100vh',
          userSelect: this.isDragging ? 'none' : 'auto',
        };
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
        this.isDragging = true;
        this.currentX = e.clientX;
        document.body.style.cursor = 'ew-resize';
      },
      stopDrag() {
        if (!this.isDragging) return;
        this.isDragging = false;
        this.frameRequested = false;
        document.body.style.cursor = '';
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
        const containerWidth = this.$el.offsetWidth;
        const max = containerWidth - this.minWidth;
        const newWidth = Math.min(Math.max(this.currentX, this.minWidth), max);
        this.leftWidth = newWidth;
        this.frameRequested = false;
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
        
        style="cursor: ew-resize; width: 15px; ">
            <v-divider vertical :thickness="isDragging || isHovering ? 3 : 1" :color="isDragging || isHovering ? 'primary' : undefined" :opacity="isDragging || isHovering ? 1 : undefined"
            style="height: 100%"
            ></v-divider>
        </div>

        <div class="flex-grow-1">
          <slot name="right" />
        </div>
      </div>
    `,
});
