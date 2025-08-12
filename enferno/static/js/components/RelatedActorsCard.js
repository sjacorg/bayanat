const RelatedActorsCard = Vue.defineComponent({
  props: {
    entity: {
      type: Object,
      required: true,
    },
    relationInfo: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      translations: window.translations,
      actorPage: 1, // Now managed internally for actor relations pagination
      actorLM: false, // Initially false, updated based on API response for actor relations
      extractValuesById: extractValuesById, // Reuse the existing method for extracting values by ID
    };
  },
  watch: {
    entity: {
      handler(newVal, oldVal) {
        if (newVal && newVal !== oldVal && newVal.id) {
          this.bulletinPage = 1; // Reset page
          this.entity.actor_relations = []; // Clear current relations
          this.loadActorRelations();
        }
      },
      immediate: true, // Immediate will call the watcher when the component is mounted
      deep: true, // Deep watcher to detect changes within the object
    },
  },
  methods: {
    loadActorRelations(page = 1) {
      axios
        .get(`/admin/api/${this.entity.class}/relations/${this.entity.id}?class=actor&page=${page}`)
        .then((res) => {
          // Properly append to existing actor relations
          this.entity.actor_relations = [...this.entity.actor_relations, ...res.data.items];
          this.actorPage += 1; // Increment page for next potential fetch
          this.actorLM = res.data.more; // Update "load more" flag based on response
        })
        .catch((err) => {
          console.error(err.toJSON());
        });
    },
    probability(item) {
      // Ensure this method correctly accesses the 'probs' object within 'translations' for actors
      return this.translations.probs[item.probability].tr;
    }
  },
  computed: {
    getRelTo(){
      const c = this.entity.class.toLowerCase()[0];
      return `relto${c}`;
    }
  },
  template: `
      <v-card class="ma-2" v-if="entity.actor_relations && entity.actor_relations.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.relatedActors_ }}
            <v-btn icon="mdi-image-filter-center-focus-strong" variant="text" size="x-small"
                   :href="'/admin/actors/?'+this.getRelTo+'='+entity.id" target="_self">
            </v-btn>
          </v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <actor-result v-for="(item,index) in entity.actor_relations" :key="index"
                        :actor="item.actor">
            <template v-slot:header>
              <v-sheet class="pa-2 border-b d-flex flex-column ga-1">
                <v-list-item-title variant="flat"  class="text-caption mt-2">{{ translations.relationshipInfo_ }}</v-list-item-title>
                <div class="mb-2">
                  <div class="text-caption font-weight-bold mt-2">{{ translations.probability_ }}</div>
                  <v-chip v-if="item.probability !== null" size="small" label class="flex-chip">{{ probability(item) }}</v-chip>
                  <div class="text-caption font-weight-bold mt-2">Related as</div>
                  <div class="flex-chips">
                    <v-chip v-if="item?.related_as" v-for="r in extractValuesById(relationInfo, item.related_as, 'title')" class="flex-chip" size="small" label>{{ r }}</v-chip>
                  </div>
                  <div class="text-caption font-weight-bold mt-2">Comments</div>
                  <div v-if="item.comment" class="text-caption"><read-more>{{ item.comment }}</read-more></div>
                </div>
              </v-sheet>
            </template>
          </actor-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto" size="small"
                 variant="tonal"  append-icon="mdi-chevron-down" color="grey"
                 @click="loadActorRelations(actorPage)"
                 v-if="actorLM">{{ translations.loadMore_ }}
          </v-btn>
        </v-card-actions>
      </v-card>
    `,
});
