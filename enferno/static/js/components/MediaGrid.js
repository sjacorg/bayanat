const MediaGrid = Vue.defineComponent({
  props: {
    medias: Array,
    enableDelete: Boolean,
    horizontal: Boolean,
    prioritizeVideos: Boolean,
    miniMode: Boolean,
  },
  emits: ['remove-media', 'remove-redaction', 'media-click'],
  computed: {
    primaryMedia() {
      const list = this.prioritizeVideos ? this.sortMediaByFileType(this.medias) : (this.medias || []);
      return list.filter(media => !this.isRedaction(media));
    },
    redactionsBySource() {
      const map = {};
      for (const media of (this.medias || [])) {
        if (!this.isRedaction(media)) continue;
        const srcId = media.originalMediaId;
        if (srcId == null) continue;
        if (!map[srcId]) map[srcId] = [];
        map[srcId].push(media);
      }
      return map;
    },
  },
  methods: {
    isRedaction(media) {
      return media?.originalMediaId != null;
    },
    mediaIndex(media) {
      return this.medias.indexOf(media);
    },
    sortMediaByFileType(mediaList) {
      if (!mediaList) return [];
      return [...mediaList].sort((a, b) => {
        if (a?.fileType?.includes('video')) return -1;
        if (b?.fileType?.includes('video')) return 1;
        return 0;
      });
    },
  },
  template: /*html*/`
    <div>
      <v-sheet :class="horizontal ? 'd-flex ga-2 flex-row overflow-x-auto' : 'media-grid'">
        <media-card
          v-for="media in primaryMedia" :key="media.id || media.uuid"
          @media-click="$emit('media-click', $event)"
          @remove-redaction="$emit('remove-redaction', $event)"
          :media="media"
          :mini-mode="miniMode"
          :redactions="redactionsBySource[media.id] || []"
          class="flex-shrink-0"
        >
          <template #actions v-if="enableDelete">
            <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', mediaIndex(media))" color="red"></v-btn>
          </template>
        </media-card>
      </v-sheet>
    </div>
  `,
});
