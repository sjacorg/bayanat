const MediaGrid = Vue.defineComponent({
  props: {
    medias: Array,
    enableDelete: Boolean,
    horizontal: Boolean,
    prioritizeVideos: Boolean,
    miniMode: Boolean,
  },
  emits: ['remove-media', 'media-click'],
  data() {
    return { showRedactions: false };
  },
  computed: {
    primaryMedia() {
      const list = this.prioritizeVideos ? this.sortMediaByFileType(this.medias) : (this.medias || []);
      return list.filter(media => !this.isRedaction(media));
    },
    redactionMedia() {
      return (this.medias || []).filter(media => this.isRedaction(media));
    },
    visibleMedia() {
      return this.showRedactions ? [...this.primaryMedia, ...this.redactionMedia] : this.primaryMedia;
    },
  },
  methods: {
    isRedaction(media) {
      return media?.category?.title === 'Redaction';
    },
    mediaIndex(media) {
      // Index into the unfiltered list so deletion stays correct regardless of sort/filter
      return this.medias.indexOf(media);
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
  },
  template: /*html*/`
      <div>
        <v-sheet :class="horizontal ? 'd-flex ga-2 flex-row overflow-x-auto' : 'media-grid'">
          <media-card
            v-for="media in primaryMedia" :key="media.id || media.uuid"
            @media-click="$emit('media-click', $event)"
            :media="media"
            :mini-mode="miniMode"
            class="flex-shrink-0"
          >
            <template #actions v-if="enableDelete">
              <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', mediaIndex(media))"  color="red"></v-btn>
            </template>
          </media-card>
        </v-sheet>

        <template v-if="redactionMedia.length">
          <v-btn
            variant="text" size="small" class="mt-2"
            :prepend-icon="showRedactions ? 'mdi-eye-off-outline' : 'mdi-marker'"
            @click="showRedactions = !showRedactions"
          >
            {{ showRedactions ? 'Hide' : 'Show' }} {{ redactionMedia.length }} redacted cop{{ redactionMedia.length > 1 ? 'ies' : 'y' }}
          </v-btn>

          <template v-if="showRedactions">
            <v-divider class="my-2">
              <v-chip size="x-small" color="warning" variant="tonal" prepend-icon="mdi-marker">
                Redacted copies
              </v-chip>
            </v-divider>
            <v-sheet :class="horizontal ? 'd-flex ga-2 flex-row overflow-x-auto' : 'media-grid'">
              <media-card
                v-for="media in redactionMedia" :key="media.id || media.uuid"
                @media-click="$emit('media-click', $event)"
                :media="media"
                :mini-mode="miniMode"
                class="flex-shrink-0"
              >
                <template #actions v-if="enableDelete">
                  <v-btn size="small" variant="text" icon="mdi-delete-sweep" v-if="!media.main" @click="$emit('remove-media', mediaIndex(media))" color="red"></v-btn>
                </template>
              </media-card>
            </v-sheet>
          </template>
        </template>
      </div>
  `,
});
