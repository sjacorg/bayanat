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
    i18n: {
      type: Object,
      required: true,
    },
  },
  data() {
    return {
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
      // Ensure this method correctly accesses the 'probs' object within 'i18n' for actors
      return this.i18n.probs[item.probability].tr;
    }
  },
  template: `
      <v-card class="ma-2" v-if="entity.actor_relations && entity.actor_relations.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ i18n.relatedActors_ }}
            <v-btn icon="mdi-image-filter-center-focus-strong" variant="text" size="x-small"
                   :href="'/admin/actors/?reltob='+entity.id" target="_self">
            </v-btn>
          </v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <actor-result :i18n="i18n" v-for="(item,index) in entity.actor_relations" :key="index"
                        :actor="item.actor">
            <template v-slot:header>
              <v-sheet color="yellow" class="pa-2">
                <v-list-item-title variant="flat"  class="text-caption my-2">{{ i18n.relationshipInfo_ }}</v-list-item-title>
                <v-chip v-if="item.probability !== null" size="small" label>{{ probability(item) }}
                </v-chip>
                <v-chip class="ma-1" v-for="r in extractValuesById(relationInfo, item.related_as, 'title')"
                        color="grey" size="small" label>{{ r }}
                </v-chip>
                <v-chip v-if="item.comment" color="grey" size="small" label>{{ item.comment }}</v-chip>
              </v-sheet>
            </template>
          </actor-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto" size="small"
                 variant="tonal"  append-icon="mdi-chevron-down" color="grey"
                 @click="loadActorRelations(actorPage)"
                 v-if="actorLM">{{ i18n.loadMore_ }}
          </v-btn>
        </v-card-actions>
      </v-card>
    `,
});
