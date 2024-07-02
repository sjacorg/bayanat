const RelatedIncidentsCard = Vue.defineComponent({
  props: {
    entity: {
      type: Object,
      required: true,
    },
    i18n: {
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
      incidentPage: 1, // Pagination for incident relations
      incidentLM: false, // Load more flag for incidents
      extractValuesById: extractValuesById, // Reuse the existing method for extracting values by ID
    };
  },
  watch: {
     entity: {
      handler(newVal, oldVal) {
      if (newVal && newVal !== oldVal && newVal.id) {

          this.bulletinPage = 1; // Reset page
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
      return this.i18n.probs[item.probability].tr;
    }
  },
  template: `
    <v-card class="ma-2" v-if="entity.incident_relations && entity.incident_relations.length">
      <v-toolbar density="compact">
        <v-toolbar-title class="text-subtitle-1">{{ i18n.relatedIncidents_ }}
          <v-btn icon="mdi-image-filter-center-focus-strong" size="x-small" variant="text"
                 :href="'/admin/incidents/?reltob='+entity.id" target="_self">
          </v-btn>
        </v-toolbar-title>
      </v-toolbar>
      <v-card-text>
        <incident-result :i18n="i18n" v-for="(item, index) in entity.incident_relations" :key="index"
                         :incident="item.incident">
          <template v-slot:header>
            <v-sheet  class="pa-2">
              <v-list-item-title variant="flat"  class="text-caption my-2">{{ i18n.relationshipInfo_ }}</v-list-item-title>
              <v-chip v-if="item.probability !== null"  size="small" label>{{ probability(item) }}</v-chip>
              <v-chip v-for="r in extractValuesById(relationInfo, [item.related_as], 'title')" v-if="item.related_as"
                     class="mx-2" color="grey" size="small" label>{{ r }}</v-chip>
              <v-chip v-if="item.comment" color="grey" size="small" label>{{ item.comment }}</v-chip>
            </v-sheet>
          </template>
        </incident-result>
      </v-card-text>
      <v-card-actions>
        <v-btn class="ma-auto" variant="tonal" append-icon="mdi-chevron-down"   color="grey" elevation="0"
               @click="loadIncidentRelations(incidentPage)" v-if="incidentLM">{{ i18n.loadMore_ }}
        </v-btn>
      </v-card-actions>
    </v-card>
  `,
});
