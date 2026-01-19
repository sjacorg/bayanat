const RelatedBulletinsCard = Vue.defineComponent({
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
      bulletinPage: 1,
      bulletinLM: false,
      extractValuesById: extractValuesById,
    };
  },
  watch: {
    entity: {
      handler(newVal, oldVal) {
          if (newVal && newVal !== oldVal && newVal.id) {
          this.bulletinPage = 1; // Reset page
          this.entity.bulletin_relations = []; // Clear current relations
          this.loadBulletinRelations();
        }
      },
      immediate: true, // Immediate will call the watcher when the component is mounted
      deep: true, // Deep watcher to detect changes within the object
    },
  },
  methods: {
    loadBulletinRelations(page = 1) {
      axios
        .get(
          `/admin/api/${this.entity.class}/relations/${this.entity.id}?class=bulletin&page=${page}`,
        )
        .then((res) => {
          this.entity.bulletin_relations = [...this.entity.bulletin_relations, ...res.data.items];
          this.bulletinPage += 1;
          this.bulletinLM = res.data.more;
        })
        .catch((err) => {
          console.error(err.toJSON());
        });
    },
    probability(item) {
      return this.translations.probs[item.probability].tr;
    },

  },
  computed: {
    getRelTo(){
      const c = this.entity.class.toLowerCase()[0];
      return `relto${c}`;
    }
  },
  template: `
      <v-card class="ma-2" v-if="entity.bulletin_relations && entity.bulletin_relations.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.relatedBulletins_ }}
            <v-btn variant="text" size="x-small" icon="mdi-image-filter-center-focus-strong"
                   :href="'/admin/bulletins/?'+ this.getRelTo + '='+entity.id" target="_self">
            </v-btn>
          </v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <bulletin-result v-for="(item,index) in entity.bulletin_relations" :key="index"
                           :bulletin="item.bulletin">
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
          </bulletin-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto" append-icon="mdi-chevron-down" size="small" variant="tonal" color="grey" 
                 @click="loadBulletinRelations(bulletinPage)"
                 v-if="bulletinLM">{{ translations.loadMore_ }}
            
          </v-btn>
        </v-card-actions>
      </v-card>
    `,
});

export default RelatedBulletinsCard;