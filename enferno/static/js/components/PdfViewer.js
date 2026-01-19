const PdfViewer = Vue.defineComponent({
  props: ['media', 'mediaType'],
  data: () => {
    return {
      translations: window.translations,
      fullscreen: false,
    };
  },
  methods: {
    requestFullscreen() {
      this.fullscreen = true;
    },
  },
  template: `
    <div>
      <v-dialog
        v-model="fullscreen"
        fullscreen
      >
        <v-card class="overflow-hidden">
          <v-toolbar color="dark-primary">
              <v-toolbar-title>{{ translations.preview_ }}</v-toolbar-title>
              <v-spacer></v-spacer>
          
              <template #append>
                  <v-btn icon="mdi-close" @click.stop.prevent="fullscreen = false"></v-btn>
              </template>
          </v-toolbar>
      
          <v-card-text class="pa-0" style="height: calc(100vh - 64px);">
            <iframe :src="media?.s3url" class="w-100 h-100" allow="fullscreen" allow-fullscreen></iframe>
          </v-card-text>
        </v-card>
      </v-dialog>

      <iframe :src="media?.s3url" class="w-100 h-100"   allowfullscreen allow-fullscreen></iframe>
    </div>
    `,
});

export default PdfViewer;