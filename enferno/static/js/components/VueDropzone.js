const VueDropzone = Vue.defineComponent({
  props: {
    options: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ['ready', 'vdropzone-error', 'vdropzone-removed-file', 'vdropzone-file-added', 'vdropzone-success'],
  async mounted() {
    await loadAsset('/static/css/dropzone.min.css')
    await loadAsset('/static/js/dropzone.min.js')

    // Initialize Dropzone on the current element with provided options
    this.dz = new Dropzone(this.$el, { ...this.options });

    this.$emit('ready', this.dz);
  
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

  methods: {
    initDropzone() {}
  },

  beforeUnmount() {
    this.dz?.destroy();
    this.dz = null;
  },

  template: `
    <div class="dropzone" v-bind="$attrs"></div>
  `,
});
