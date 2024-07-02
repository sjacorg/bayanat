const MediaCard = Vue.defineComponent({
  props: {
    media: {},
  },
    emits: ['video-click', 'ready'],
  data: function () {
    return {
      s3url: '',
    };
  },
  mounted() {
    this.init();
  },

  methods: {
    init() {
      axios
        .get(`/admin/api/media/${this.media.filename}`)
        .then((response) => {
          this.s3url = response.data;
          this.media.s3url = response.data;
        })
        .catch((error) => {
          console.error('Error fetching media:', error);
        })
        .finally(() => {
          this.$emit('ready');
        });
    },

    showPDF() {
      this.$root.$refs.pdfViewer.openPDF(this.s3url);
    },

    mediaType(mediaItem) {
      if (['image/jpeg', 'image/png', 'image/gif'].includes(mediaItem.fileType)) {
        return 'image';
      } else if (['video/webm', 'video/mp4', 'video/ogg'].includes(mediaItem.fileType)) {
        return 'video';
      } else if (['application/pdf'].includes(mediaItem.fileType)) {
        return 'pdf';
      } else {
        return 'unknown';
      }
    },
  },
  template: `


    <!--  Image Media Card -->
    <v-card height="300" :disabled="!s3url"
            class=" media-card"
            v-if="mediaType(media) === 'image'">
      
      <a :href="s3url"
         data-pswp-width="2000"
         data-pswp-height="2000"
         target="_blank">
        <img style="width: 250px;height: 140px; object-fit: cover" :src="s3url" alt=""/>
      </a>

      <div class="text-caption pa-2">
        {{ media.title || '&nbsp;' }}  <span v-if="media.time">({{ media.time }})</span>
      </div>
      <v-chip size="small" class="text-caption pa-1 ">
        {{ media.etag }}
      </v-chip>
      <v-card-text class="pa-2 d-flex">
        <slot name="actions"></slot>
      </v-card-text>


    </v-card>

    <!-- Video Media Card  -->
    <v-card height="300" :disabled="!s3url" class="media-card"
            v-else-if="mediaType(media) === 'video'">
      <v-card color="grey-darken-4" width="250" height="140" class="d-flex align-center justify-center">
        <v-btn icon="mdi-play-circle" @click="$emit('video-click',s3url)" variant="plain" size="x-large"></v-btn>


      </v-card>
      <div class="text-caption pa-2">
        {{ media.title }}
      </div>

      <v-chip prepend-icon="mdi-timer" size="small" v-if="media.duration && media.duration.length"
              class="caption pa-2 d-flex align-center">

        {{ media.duration.toHHMMSS() }}

      </v-chip>

      <v-sheet class="ma-2 pa-2  text-caption etag">
        {{ media.etag }}
      </v-sheet>

      <v-card-text class="pa-2 d-flex">
        <slot name="actions"></slot>
      </v-card-text>
    </v-card>


    <v-card height="300" :disabled="!s3url" class="media-card" v-else-if="mediaType(media) === 'pdf'">


      <v-btn @click="showPDF" class="mt-2" variant="plain">
        <v-icon left color="red" size="32">mdi-file-pdf-box</v-icon>
        PDF
      </v-btn>


      <div class="text-caption pa-2">
        {{ media.title }}
      </div>

      <!-- ETAG New Design-->


      <v-sheet class="ma-2 pa-2  text-caption etag">
        {{ media.etag }}
      </v-sheet>


      <v-card-text class="pa-2 d-flex">
        <slot name="actions"></slot>
      </v-card-text>
    </v-card>


    <!-- Other mime types   -->
    <v-card height="300" :disabled="!s3url" class="media-card" v-else-if="mediaType(media) === 'unknown'">

      <v-btn class="ma-3 py-6" :href="s3url" variant="plain" target="_blank">
        <v-icon size="32" color="#666">mdi-file</v-icon>
      </v-btn>

      <div class="text-caption pa-2">
        {{ media.title }}
      </div>


      <v-sheet class="ma-2 pa-2  text-caption etag">
        {{ media.etag }}
      </v-sheet>

      <v-card-text class="pa-2 d-flex">
        <slot name="actions"></slot>
      </v-card-text>
    </v-card>











  `,
});
