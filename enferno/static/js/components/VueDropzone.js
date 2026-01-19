const VueDropzone = Vue.defineComponent({
  props: {
    options: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ['vdropzone-error', 'vdropzone-removed-file', 'vdropzone-file-added', 'vdropzone-success'],
  mounted() {
    // Initialize Dropzone on the current element with provided options
    this.dz = new Dropzone(this.$el, { ...this.options });

    // Register event listeners to emit custom Vue events
    this.dz.on('error', (file, response) => {
      this.$emit('vdropzone-error', file, response);
    });

    this.dz.on('removedfile', (file) => {
      this.$emit('vdropzone-removed-file', file);
    });

    this.dz.on('addedfile', (file) => {
      this.$emit('vdropzone-file-added', file);
    });

    this.dz.on('success', (file, response) => {
      this.$emit('vdropzone-success', file, response);
    });
  },
  template: `
    <div class="dropzone" v-bind="$attrs"></div>
  `,
});

export default VueDropzone;
