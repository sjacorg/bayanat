const MediaGrid = Vue.defineComponent({
  props: {
    medias: Array,
    enableDelete: Boolean,
    horizontal: Boolean,
    prioritizeVideos: Boolean,
    miniMode: Boolean,
  },
  emits: ['remove-media', 'media-click'],
  computed: {
    sortedMedia() {
      if (this.prioritizeVideos) return this.sortMediaByFileType(this.medias);

      return this.medias;
    }
  },
  methods: {
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
  },
  template: /*html*/`
      <div>
        <v-sheet :class="horizontal ? 'd-flex ga-2 flex-row overflow-x-auto' : 'media-grid'">
          <media-card
            v-for="(media,index) in sortedMedia" :key="media.id || media.uuid"
            @media-click="$emit('media-click', $event)"
            :media="media"
            :mini-mode="miniMode"
            class="flex-shrink-0"
          >
            <template #actions v-if="enableDelete">
              <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', index)"  color="red"></v-btn>    
            </template>
          </media-card>
        </v-sheet>
      </div>
  `,
});

export default MediaGrid;