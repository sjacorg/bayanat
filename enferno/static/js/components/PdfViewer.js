Vue.component('pdf-viewer', {
    data: () => {
        return {
            viewer: false,
            url: null

        }
    },
    methods: {
        openPDF(url) {
            this.viewer = true;
            this.url = url;
        },
        closePDF() {
            this.viewer = false;
            this.url = null;
        }
    },
    template: `
    <v-dialog overlay="false"  min-width="1000" v-model="viewer">
    <v-card height="100%" class="pa-5" v-if="viewer">
   
    <v-card-text class="justify-end text-right">
    <v-btn outlined color="grey darken-2" @click.stop.prevent="closePDF" x-small right
                           top="10" fab>
                        <v-icon>mdi-close</v-icon>
        </v-btn>
    
    </v-card-text>
    <v-card-text>
    
    <iframe v-if="url" id="pdf" width="100%" style="height: 80vh" :src="url" frameborder="0"></iframe>
    </v-card-text>
    </v-card>
    </v-dialog>
    
    `
})