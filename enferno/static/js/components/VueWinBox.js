const VueWinBox = Vue.defineComponent({
  props: {
    options: {
      type: Object,
      required: true,
    },
    openOnMount: {
      type: Boolean,
      default: true,
    },
  },
  emits: ['move', 'resize', 'close', 'focus', 'blur'],
  data() {
    return {
      selector: `vuewinbox-${Math.random().toString(36).substr(2, 8)}`,
      winbox: null,
      initialized: false,
    }
  },
  methods: {
    initialize() {
      if (this.initialized) {
        console.error('Please close the window first before reinitializing.')
        return
      }

      this.winbox = new WinBox({
        ...this.options,
        title: this.$slots?.title ? '' : this.options?.title,
        id: this.selector,
        onresize: (width, height) => {
          this.$emit('resize', {
            id: this.winbox?.id,
            width,
            height,
          })
        },
        onclose: (force) => {
            const shouldClose = force ? null : confirm("Are you sure?");

            if (force || shouldClose) {
                this.$emit('close', { id: this.winbox?.id })
                this.initialized = false
                this.winbox = null
                return false
            } else {
                return true
            }
        },
        onfocus: () => {
          this.$emit('focus', { id: this.winbox?.id })
        },
        onblur: () => {
          this.$emit('blur', { id: this.winbox?.id })
        },
        onmove: (x, y) => {
          this.$emit('move', {
            id: this.winbox?.id,
            x,
            y,
          })
        },
      })
      this.winbox.addControl({
        class: 'wb-prepend-controls'
      })

      this.initialized = true
    },
    forceClose() {
        this.winbox.close(true)
        this.$emit('close', { id: this.winbox?.id })
        this.initialized = false
        this.winbox = null
    }
  },
  mounted() {
    if (this.openOnMount) {
      this.initialize()
    }
  },
  unmounted() {
    if (this.winbox) {
      this.winbox.close()
    }
  },
  template: `
    <div v-if="initialized">
        <teleport :to="'#' + selector + ' .wb-body'">
            <slot name="default" :winbox="winbox" />
        </teleport>

        <teleport :to="'#' + selector + ' .wb-title'">
            <slot name="title" :winbox="winbox" />
        </teleport>

        <teleport :to="'#' + selector + ' .wb-prepend-controls'">
            <slot name="prepend-controls" :winbox="winbox" />
        </teleport>
    </div>
    `
})  
