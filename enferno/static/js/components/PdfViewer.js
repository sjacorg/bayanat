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
            <object :data="media?.s3url" class="w-100 h-100"></object>
          </v-card-text>
        </v-card>
      </v-dialog>

      <object :data="media?.s3url" class="w-100 h-100"></object>
    </div>
    `,
});
