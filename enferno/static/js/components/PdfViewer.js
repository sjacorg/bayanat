const PdfViewer = Vue.defineComponent({
  props: {
    dialogProps: {
      type: Object,
      default: null
    }
  },
  data: () => {
    return {
      viewer: false,
      url: null,
    };
  },
  methods: {
    openPDF(url) {
      this.viewer = true;
      this.url = url;
    },
    closePDF() {
      this.viewer = false;
      this.url = null;
    },
  },
  template: `
    <v-dialog
      overlay="false"
      v-bind="dialogProps"
      v-model="viewer"
    >
      <v-card v-if="viewer">
        <v-toolbar>
          <v-spacer></v-spacer>
          <v-btn
              @click.stop.prevent="closePDF"
              icon="mdi-close"
              variant="text"
          ></v-btn>
        </v-toolbar>
    
        <v-card-text>
          <object id="pdf" v-if="url" style="width: 100%;height: 80vh" :data='url'></object>
        </v-card-text>
      </v-card>
    </v-dialog>
    
    `,
});
