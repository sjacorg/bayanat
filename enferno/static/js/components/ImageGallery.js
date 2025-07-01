const ImageGallery = Vue.defineComponent({
  props: {
    medias: Array,
    enableDelete: Boolean,
    horizontal: Boolean,
    prioritizeVideos: Boolean
  },
  emits: ['remove-media', 'thumb-click', 'video-click', 'audio-click', 'expand-media'],
  mounted() {
    this.initLightbox();
  },
  unmounted() {
    this.lightboxInstance?.destroy?.();
    this.lightboxInstance = null;
  },
  watch: {
    medias: {
      handler() {
        this.$nextTick(() => {
          this.lightboxInstance?.refresh?.();
        });
      },
      deep: true,
    }
  },
  computed: {
    sortedMedia() {
      if (this.prioritizeVideos) return this.sortMediaByFileType(this.medias);

      return this.medias;
    }
  },
  methods: {
    handleVideo(media){
      this.$emit('video-click', media)
    },
    sortMediaByFileType(mediaList) {
      if (!mediaList) return [];
      // Sort media list by fileType (video first)
      const sortedMediaList = [...mediaList].sort((a, b) => {
        if (a?.fileType?.includes('video')) return -1; // Video should come first
        if (b?.fileType?.includes('video')) return 1; // Then images
        return 0; // Leave unchanged if neither is a video
      });

      return sortedMediaList;
    },
    handleAudio(media){
      this.$emit('audio-click', media)
    },
    initLightbox() {
      const el = this.$refs.galleryContainer;
      if (!el) return;

      this.lightboxInstance = lightGallery(el, {
        plugins: [lgZoom, lgThumbnail, lgRotate],
        download: false,
        showZoomInOutIcons: true,
        actualSize: false,
        speed: 500,
        selector: '.media-item',
      });
    },
  },

  data: function () {
    return {
      lightboxInstance: null
    };
  },

  template: `
      <div ref="galleryContainer">
        <v-sheet :class="horizontal ? 'media-row' : 'media-grid'">
          <v-sheet v-for="(media,index) in sortedMedia" :key="media.id || media.uuid">
            <media-card
              @video-click="handleVideo"
              @audio-click="handleAudio"
              :media="media"
            >
              <template v-slot:top-actions="{ media, mediaType }">
                <slot name="top-actions" :media="media" :mediaType="mediaType"></slot>
              </template>
              <template v-slot:actions v-if="enableDelete">
                <v-divider></v-divider>
                <v-card-actions class="justify-end d-flex py-0" style="min-height: 45px;">
                    <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', index)"  color="red"></v-btn>    
                </v-card-actions>
              </template>
            </media-card>
          </v-sheet>
        </v-sheet>
      </div>
  `,
});