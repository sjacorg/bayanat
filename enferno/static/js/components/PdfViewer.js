const PdfViewer = Vue.defineComponent({
  props: {
    dialogProps: {
      type: Object,
      default: null
    }
  },
  data: () => {
    return {
      translations: window.translations,
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
        <v-toolbar color="dark-primary">
            <v-toolbar-title>{{ translations.preview_ }}</v-toolbar-title>
            <v-spacer></v-spacer>
        
            <template #append>
                <v-btn icon="mdi-close" @click.stop.prevent="closePDF"></v-btn>
            </template>
        </v-toolbar>
    
        <v-card-text>
          <object id="pdf" v-if="url" style="width: 100%;height: 80vh" :data='url'></object>
        </v-card-text>
      </v-card>
    </v-dialog>
    
    `,
});
