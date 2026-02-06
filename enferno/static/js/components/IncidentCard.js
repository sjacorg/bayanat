const IncidentCard = Vue.defineComponent({
  props: ['incident', 'close', 'log', 'diff', 'showEdit'],
  emits: ['edit', 'close'],
  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'incident' });
  },
  methods: {
    async loadGeoMap() {
      this.geoMapLoading = true;
      this.geoMapOn = true;

      try {
        const [bulletinsRes, actorsRes] = await Promise.all([
          axios.get(`/admin/api/incident/relations/${this.incident.id}?class=bulletin&page=1&per_page=1000`),
          axios.get(`/admin/api/incident/relations/${this.incident.id}?class=actor&page=1&per_page=1000`),
        ]);

        const baseLocations = aggregateIncidentLocations(this.incident);

        let bulletinLocations = [];
        if (bulletinsRes.data.items?.length) {
          bulletinLocations = await getBulletinLocations(bulletinsRes.data.items.map(x => x.bulletin.id));
          bulletinLocations = bulletinLocations?.flat()?.map(location => ({ ...location, show_parent_id: true }))
        }

        let actorLocations = [];
        if (actorsRes.data.items?.length) {
          actorLocations = await getActorLocations(actorsRes.data.items.map(x => x.actor.id));
          actorLocations = actorLocations?.flat()?.map(location => ({ ...location, show_parent_id: true }))
        }

        // 🔥 Combine bulletins and actor locations
        this.mapLocations = baseLocations.concat(bulletinLocations, actorLocations);

      } catch (err) {
        console.error(err);
        this.geoMapOn = false;
      } finally {
        this.geoMapLoading = false;
      }
    },

    translate_status(status) {
      return translate_status(status);
    },

    logAllowed() {
      return this.$root.currentUser.view_simple_history && this.log;
    },

    diffAllowed() {
      return this.$root.currentUser.view_full_history && this.diff;
    },

    editAllowed() {
      if (typeof this.$root.editAllowed === 'function') {
        return this.$root.editAllowed(this.incident) && this.showEdit;
      }
      return false;
    },

    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/incidenthistory/${this.incident.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          console.log(error.body.data);
        })
        .finally(() => {
          this.hloading = false;
        });
    },

    getBulletinsByIdList(ids) {
      return Promise.all(
        ids.map((id) => api.get(`/admin/api/bulletin/${id}?mode=3`).then((res) => res.data)),
      );
    },

    getActorsByIdList(ids) {
      return Promise.all(
        ids.map((id) => api.get(`/admin/api/actor/${id}?mode=3`).then((res) => res.data)),
      );
    },

    showDiff(e, index) {
      this.diffDialog = true;
      //calculate diff
      const dp = this.$jsondiffpatch.create({
        arrays: {
          detectMove: true,
        },
        objectHash: function (obj, index) {
          return obj.name || obj.id || obj._id || '$$index:' + index;
        },
      });

      const delta = dp.diff(this.revisions[index + 1].data, this.revisions[index].data);
      if (!delta) {
        this.diffResult = 'Both items are Identical :)';
      } else {
        this.diffResult = this.$htmlFormatter.format(delta);
      }
    },
  },
  data: function () {
    return {
      translations: window.translations,
      geoMapLoading: false,
      geoMapOn: false,
      diffResult: '',
      diffDialog: false,
      revisions: null,
      show: false,
      hloading: false,
      //global map
      mapLocations: [],
    };
  },

  template: `
      <v-card class="mx-auto">
        <v-toolbar class="d-flex px-2 ga-2">
          <v-chip size="small">
            {{ translations.id_ }} {{ incident.id }}
          </v-chip>

          <v-btn variant="tonal" size="small" prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2"
                 @click="$emit('edit',incident)">
            {{ translations.edit_ }}
          </v-btn>

          <v-btn size="small" class="ml-2" variant="tonal" prepend-icon="mdi-graph-outline"
                 @click.stop="$root.$refs.viz.visualize(incident)">
            {{ translations.visualize_ }}
          </v-btn>

          <template #append>
            <v-btn variant="text" icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)">
          </v-btn>
          </template>
        </v-toolbar>

        <v-sheet v-if="incident.assigned_to || incident.status" variant="flat" class="d-flex pa-0   ga-2">
          <div class="pa-2" v-if="incident.assigned_to">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    
                    variant="text"
                  v-bind="props"
                  prepend-icon="mdi-account-circle-outline">
                  {{ incident.assigned_to['name'] }}
                </v-chip>
              </template>
              {{ translations.assignedUser_ }}
            </v-tooltip>
          </div>

          <v-divider v-if="incident.assigned_to" vertical ></v-divider>
          
          <div class="pa-2" v-if="incident.status">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    variant="text"
                  v-bind="props"
                  prepend-icon="mdi-delta" class="mx-1">
                  {{ incident.status }}
                </v-chip>
              </template>
              {{ translations.workflowStatus_ }}
            </v-tooltip>
          </div>
        </v-sheet> 

        <v-divider></v-divider>
        <v-card v-if="incident.roles?.length" variant="flat" class="ma-2 d-flex align-center pa-2 flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="blue-darken-3" class="mx-2" size="small" v-bind="props">mdi-lock</v-icon>
            </template>
            {{ translations.accessRoles_ }}
          </v-tooltip>
          <v-chip label size="small" v-for="role in incident.roles" :color="role.color" class="mx-1">{{ role.name }}</v-chip>
        </v-card>  
        <v-divider v-if="incident.roles?.length" ></v-divider>

        <div class="d-flex flex-wrap">
          <template v-for="(field, index) in $root.cardDynamicFields('incident')">
            <div v-if="$root.isFieldActiveAndHasContent(field, 'title', [incident.title, incident.title_ar])" :class="$root.fieldClassDrawer(field)">
              <uni-field :caption="translations.title_" :english="incident.title" :arabic="incident.title_ar"></uni-field>
            </div>

            <div v-else-if="$root.isFieldActiveAndHasContent(field, 'description', incident.description)" :class="$root.fieldClassDrawer(field)">
              <v-card class="ma-2 pa-2">
                <div class="caption grey--text mb-2">{{ translations.description_ }}</div>
                <read-more><div class="rich-description" v-html="incident.description"></div></read-more>
              </v-card>
            </div>

            <div v-else-if="$root.isFieldActiveAndHasContent(field, 'potential_violations', incident.potential_violations)" :class="$root.fieldClassDrawer(field)">
              <v-card class="ma-2">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.potentialViolationsCategories_ }}</div>
                  <div class="flex-chips">
                    <v-chip class="flex-chip" v-for="item in incident.potential_violations" :key="item.id">{{ item.title }}</v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <div v-else-if="$root.isFieldActiveAndHasContent(field, 'claimed_violations', incident.claimed_violations)" :class="$root.fieldClassDrawer(field)">
              <v-card class="ma-2">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.claimedViolationsCategories_ }}</div>
                  <div class="flex-chips">
                    <v-chip class="flex-chip" v-for="item in incident.claimed_violations" :key="item.id">{{ item.title }}</v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <div v-else-if="$root.isFieldActiveAndHasContent(field, 'labels', incident.labels)" :class="$root.fieldClassDrawer(field)">
              <v-card class="ma-2">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.labels_ }}</div>
                  <div class="flex-chips">
                    <v-chip class="flex-chip" v-for="label in incident.labels" :key="label.id">{{ label.title }}</v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <div v-else-if="$root.isFieldActiveAndHasContent(field, 'locations', incident.locations)" :class="$root.fieldClassDrawer(field)">
              <v-card class="ma-2">
                <v-card-text>
                  <div class="px-1 title black--text">{{ translations.locations_ }}</div>
                  <div class="flex-chips">
                    <v-chip class="flex-chip" v-for="item in incident.locations" :key="item.id">{{ item.title }}</v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <div v-else-if="$root.isFieldActiveAndHasContent(field, 'events_section', incident.events)" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.events_ }}</v-toolbar-title>
              </v-toolbar>
              <v-card-text class="pt-0 px-2 pb-2">
                <event-card v-for="(event, index) in incident.events" :number="index+1" :key="event.id" :event="event"></event-card>
              </v-card-text>
            </v-card>
          </div>

            <div v-else-if="$root.isFieldActive(field, 'related_bulletins')" :class="$root.fieldClassDrawer(field)">
              <related-bulletins-card v-if="incident" :entity="incident" :relationInfo="$root.itobInfo"></related-bulletins-card>
            </div>

            <div v-else-if="$root.isFieldActive(field, 'related_actors')" :class="$root.fieldClassDrawer(field)">
              <related-actors-card v-if="incident" :entity="incident" :relationInfo="$root.itoaInfo"></related-actors-card>
            </div>

            <div v-else-if="$root.isFieldActive(field, 'related_incidents')" :class="$root.fieldClassDrawer(field)">
              <related-incidents-card v-if="incident" :entity="incident" :relationInfo="$root.itoiInfo"></related-incidents-card>
            </div>

            <div v-else-if="$root.isFieldActive(field)" :class="$root.fieldClassDrawer(field)">
              <div v-if="Array.isArray(incident?.[field.name])">
                <v-card class="ma-2" v-if="$root.isFieldActiveAndHasContent(field, field.name, incident?.[field.name])">
                  <v-toolbar density="compact">
                    <v-toolbar-title class="text-subtitle-1">{{ field.title }}</v-toolbar-title>
                  </v-toolbar>
                  <v-card-text class="pt-0">
                    <div class="flex-chips">
                      <v-chip label size="small" class="flex-chip" v-for="value in incident?.[field.name]" :key="value">
                        {{ $root.findFieldOptionByValue(field, value)?.label ?? value }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>
              </div>
              <div v-else-if="field.field_type === 'datetime'">
                <uni-field v-if="$root.isFieldActiveAndHasContent(field, field.name, incident?.[field.name])" :caption="field.title" :english="$root.formatDate(incident?.[field.name])"></uni-field>
              </div>
              <div v-else>
                <uni-field v-if="$root.isFieldActiveAndHasContent(field, field.name, incident?.[field.name])" :caption="field.title" :english="$root.findFieldOptionByValue(field, incident?.[field.name])?.label ?? incident?.[field.name]"></uni-field>
              </div>
            </div>

            <div v-if="index === 1" class="w-100">
              <v-card :loading="geoMapLoading" class="ma-2 pa-2">
                <v-btn :loading="geoMapLoading" :disabled="geoMapOn" @click="loadGeoMap" block elevation="0" color="primary lighten-2">
                  <v-icon left>mdi-map</v-icon>
                  {{ translations.loadGeoMap_ }}
                </v-btn>
                <v-card-text v-if="geoMapOn">
                  <global-map :model-value="mapLocations"></global-map>
                </v-card-text>
              </v-card>
            </div>
          </template>
        </div>

        <v-card v-if="incident.status==='Peer Reviewed'" variant="" elevation="0" class="ma-3"
                color="teal-lighten-2">
          <v-card-text>
            <div class="px-1 title black--text">{{ translations.review_ }}</div>
            <read-more><div v-html="incident.review" class="pa-1 my-2 grey--text text--darken-2"></div></read-more>
            <v-chip class="mt-4" label color="lime">{{ incident.review_action }}</v-chip>
          </v-card-text>
        </v-card>


        <v-card v-if="logAllowed()" outline elevation="0" class="ma-2">
          <v-card-text>
            <h3 class="title black--text align-content-center">{{ translations.logHistory_ }}
              <v-btn fab :loading="hloading" @click="loadRevisions" class="elevation-0 align-content-center">
                <v-icon>mdi-history</v-icon>
              </v-btn>
            </h3>

            <template v-for="(revision,index) in revisions">
              <v-card color="grey lighten-4" flat class="my-1 pa-2 d-flex align-center">
                            <span class="caption"><read-more class="mb-2">{{ revision.data['comments'] }}</read-more>
                            <v-chip label
                            >{{ translate_status(revision.data.status) }}</v-chip> - {{ $root.formatDate(revision.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}
                              - By {{ revision.user.username }}</span>
                <v-spacer></v-spacer>

                <v-btn v-if="diffAllowed()" v-show="index!==revisions.length-1" @click="showDiff($event,index)"
                       class="mx-1">
                  <v-icon>mdi-compare</v-icon>
                </v-btn>
              </v-card>


            </template>
          </v-card-text>

        </v-card>
        <v-dialog
            v-model="diffDialog"
            max-width="770px"
        >
          <v-card class="diff-dialog-content pa-5">
            <v-card-text>
              <div v-html="diffResult">

              </div>
            </v-card-text>
          </v-card>

        </v-dialog>


        <!-- Root Card   -->
      </v-card>
    `,
});
