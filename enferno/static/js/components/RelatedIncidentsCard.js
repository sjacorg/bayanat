const RelatedIncidentsCard = Vue.defineComponent({
  props: {
    entity: {
      type: Object,
      required: true,
    },
     relationInfo: {
      type: Array,
      required: true,
    }
  },
  data() {
    return {
      translations: window.translations,
      incidentPage: 1, // Pagination for incident relations
      incidentLM: false, // Load more flag for incidents
      extractValuesById: extractValuesById, // Reuse the existing method for extracting values by ID
    };
  },
  watch: {
     entity: {
      handler(newVal, oldVal) {
      if (newVal && newVal !== oldVal && newVal.id) {

          this.incidentPage = 1; // Reset page
          this.entity.incident_relations = []; // Clear current relations
          this.loadIncidentRelations();
        }
      },
      immediate: true, // Immediate will call the watcher when the component is mounted
      deep: true, // Deep watcher to detect changes within the object
    },
  },
  methods: {
    loadIncidentRelations(page = 1) {
      axios
        .get(`/admin/api/${this.entity.class}/relations/${this.entity.id}?class=incident&page=${page}`)
        .then((res) => {
          // Append to existing incident relations
          this.entity.incident_relations = [...this.entity.incident_relations, ...res.data.items];
          this.incidentPage += 1; // Update page for next fetch
          this.incidentLM = res.data.more; // Update load more flag
        })
        .catch((err) => {
          console.error(err.toJSON());
        });
    },
    probability(item) {
      // Access 'probs' object for incident probabilities
      return this.translations.probs[item.probability].tr;
    }
  },
  computed: {
    getRelTo(){
      const c = this.entity.class.toLowerCase()[0];
      return `relto${c}`;
    },
  },
  template: `
    <v-card class="ma-2" v-if="entity.incident_relations && entity.incident_relations.length">
      <v-toolbar density="compact">
        <v-toolbar-title class="text-subtitle-1">{{ translations.relatedIncidents_ }}
          <v-btn icon="mdi-image-filter-center-focus-strong" size="x-small" variant="text"
                 :href="'/admin/incidents/?'+this.getRelTo+'='+entity.id" target="_self">
          </v-btn>
        </v-toolbar-title>
      </v-toolbar>
      <v-card-text>
        <incident-result v-for="(item, index) in entity.incident_relations" :key="index"
                         :incident="item.incident">
          <template v-slot:header>
            <div class="bd-relation-meta">
              <v-chip v-if="item.probability !== null" size="x-small" label variant="flat" color="blue-grey-lighten-5" prepend-icon="mdi-signal-cellular-3">{{ probability(item) }}</v-chip>
              <v-chip v-if="item?.related_as" v-for="r in extractValuesById(relationInfo, item.related_as, 'title')" size="x-small" label variant="flat" color="grey-lighten-4" prepend-icon="mdi-link-variant">{{ r }}</v-chip>
              <span v-if="item.comment" class="bd-relation-comment"><v-icon size="x-small">mdi-comment-text-outline</v-icon> {{ item.comment }}</span>
            </div>
          </template>
        </incident-result>
      </v-card-text>
      <v-card-actions>
        <v-btn class="ma-auto" variant="tonal" append-icon="mdi-chevron-down" color="grey" elevation="0"
               @click="loadIncidentRelations(incidentPage)" v-if="incidentLM">{{ translations.loadMore_ }}
        </v-btn>
      </v-card-actions>
    </v-card>
  `,
});
