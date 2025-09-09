const BulletinCard = Vue.defineComponent({
  props: ['bulletin', 'close', 'thumb-click', 'active', 'log', 'diff', 'showEdit'],
  emits: ['edit', 'close'],
  mixins: [mediaMixin],
  watch: {
    bulletin: function (val, old) {

      this.mapLocations = aggregateBulletinLocations(this.bulletin);
    },
  },

  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'bulletin' })

    if (this.bulletin?.id) {
      this.mapLocations = aggregateBulletinLocations(this.bulletin);
    }
  },

  methods: {
    translate_status(status) {
      return translate_status(status);
    },

    showReview(bulletin) {
      return bulletin.status === 'Peer Reviewed' && bulletin.review;
    },

    logAllowed() {
      return this.$root.currentUser.view_simple_history && this.log;
    },

    diffAllowed() {
      return this.$root.currentUser.view_full_history && this.diff;
    },

    editAllowed() {
      if (typeof this.$root.editAllowed === 'function') {
        return this.$root.editAllowed(this.bulletin) && this.showEdit;
      }
      return false;

    },

    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/bulletinhistory/${this.bulletin.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          if (error.response) {
            console.log(error?.response?.data);
          }
        })
        .finally(() => {
          this.hloading = false;
        });
    },

    viewThumb(s3url) {
      this.$emit('thumb-click', s3url);
    },

    showDiff(e, index) {
      this.diffDialog = true;
      //calculate diff
      const dp = jsondiffpatch.create({
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
        this.diffResult = jsondiffpatch.formatters.html.format(delta);
      }
    },
  },

  data: function () {
    return {
      translations: window.translations,
      diffResult: '',
      diffDialog: false,
      revisions: null,
      show: false,
      hloading: false,
      mapLocations: [],

      // image viewer
      lightbox: null,
      mediasReady: 0,
    };
  },

  template: `

    <v-card class="rounded-0">
      <v-card variant="flat" class=" mb-4 rounded-0">
        <v-toolbar class="d-flex px-2 ga-2">
          <v-chip size="small">
            {{ translations.id_ }} {{ bulletin.id }}
          </v-chip>

          <v-tooltip v-if="bulletin.originid" location="bottom">
              <template v-slot:activator="{ props }">
                  <v-chip 
                      v-bind="props"
                      prepend-icon="mdi-identifier" 
                      :href="bulletin.source_link" 
                      target="_blank" 
                      label
                      append-icon="mdi-open-in-new"
                      class="ml-1">
                      {{ bulletin.originid }}

                  </v-chip>
              </template>
              {{ translations.originid_ }}
          </v-tooltip>

          <v-btn variant="tonal" size="small" prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2"
                 @click="$emit('edit',bulletin)">
            {{ translations.edit_ }}
          </v-btn>

          <v-btn size="small" class="ml-2" variant="tonal" prepend-icon="mdi-graph-outline"
                 @click.stop="$root.$refs.viz.visualize(bulletin)">
            {{ translations.visualize_ }}
          </v-btn>

          <template #append>
            <v-btn variant="text" icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)">
          </v-btn>
          </template>
          
        </v-toolbar>

        <v-sheet v-if="bulletin.assigned_to || bulletin.status" variant="flat" class="d-flex pa-0   ga-2">
          <div class="pa-2" v-if="bulletin.assigned_to">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    
                    variant="text"
                  v-bind="props"
                  prepend-icon="mdi-account-circle-outline">
                  {{ bulletin.assigned_to['name'] }}
                </v-chip>
              </template>
              {{ translations.assignedUser_ }}
            </v-tooltip>
          </div>

          <v-divider v-if="bulletin.assigned_to" vertical ></v-divider>
          
          <div class="pa-2" v-if="bulletin.status">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    variant="text"
                  v-bind="props"
                  prepend-icon="mdi-delta" class="mx-1">
                  {{ bulletin.status }}
                </v-chip>
              </template>
              {{ translations.workflowStatus_ }}
            </v-tooltip>
          </div>
        </v-sheet> 

        <v-divider></v-divider>
        <v-card v-if="bulletin.roles?.length" variant="flat" class="ma-2 d-flex align-center pa-2 flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="blue-darken-3" class="mx-2" size="small" v-bind="props">mdi-lock</v-icon>
            </template>
            {{ translations.accessRoles_ }}
          </v-tooltip>
          <v-chip label size="small" v-for="role in bulletin.roles" :color="role.color" class="mx-1">{{ role.name }}</v-chip>
        </v-card>  
        <v-divider v-if="bulletin.roles?.length" ></v-divider>
        
        <v-card v-if="bulletin.tags?.length" variant="flat" class="ma-2 pa-2 flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="primary" class="mx-2" size="small" v-bind="props">mdi-tag</v-icon>
            </template>
            {{ translations.ref_ }}
          </v-tooltip>
          <v-chip size="small" v-for="e in bulletin.tags" class="caption black--text mx-1 mb-1">{{ e }}</v-chip>
        </v-card>
        <v-divider v-if="bulletin.tags?.length" ></v-divider>
    
        <v-card v-if="bulletin.source_link && bulletin.source_link !='NA'" variant="flat" class=" pa-2 ma-1 d-flex align-center flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-chip 
                  
                v-bind="props"
                prepend-icon="mdi-link-variant"
                :href="bulletin.source_link" 
                target="_blank" 
                variant="text"
                append-icon="mdi-open-in-new"
                label
                class="white--text ml-1">
                {{ bulletin.source_link }}
                
              </v-chip>
            </template>
            {{ translations.sourceLink_ }}: {{ bulletin.source_link }}
          </v-tooltip>
        </v-card> 
        <v-divider v-if="bulletin.source_link" ></v-divider>
      </v-card>

      <div class="d-flex flex-wrap">
        <template v-for="(field) in $root.dynamicFieldsBulletinCard">
          <div v-if="$root.isFieldActive(field, 'title')" :class="$root.fieldClassDrawer(field)">
            <uni-field :caption="translations.originalTitle_" :english="bulletin.title" :arabic="bulletin.title_ar"></uni-field>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'sjac_title')" :class="$root.fieldClassDrawer(field)">
            <uni-field :caption="translations.title_" :english="bulletin.sjac_title" :arabic="bulletin.sjac_title_ar"></uni-field>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'description')" :class="$root.fieldClassDrawer(field)">
            <v-card v-if="bulletin.description" class="ma-2 mb-4">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.description_ }}</v-toolbar-title>
              </v-toolbar>

              <v-card-text class="text-body-2 pt-0"><read-more><div v-html="bulletin.description"></div></read-more></v-card-text>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'global_map')" :class="$root.fieldClassDrawer(field)">
            <v-card variant="flat">
              <global-map v-model="mapLocations"></global-map>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'sources')" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2"  v-if="bulletin.sources && bulletin.sources.length">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.sources_ }}</v-toolbar-title>

              </v-toolbar>
              <v-card-text class="pt-0">
                <div class="flex-chips">
                  <v-chip size="small" class="flex-chip" v-for="source in bulletin.sources"
                          :key="source.id">
                    {{ source.title }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'events_section')" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2" v-if="bulletin.events && bulletin.events.length">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.events_ }}</v-toolbar-title>
              </v-toolbar>

              <v-card-text class="pt-0 px-2 pb-2">
                <event-card v-for="(event, index) in bulletin.events" :number="index+1" :key="event.id"
                            :event="event"></event-card>
              </v-card-text>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'labels')" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2" v-if="bulletin.labels && bulletin.labels.length">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.labels_ }}</v-toolbar-title>
              </v-toolbar>

              <v-card-text class="pt-0">
                <div class="flex-chips">
                  <v-chip label size="small" class="flex-chip" v-for="label in bulletin.labels"
                          :key="label.id">
                    {{ label.title }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'ver_labels')" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2" v-if="bulletin.verLabels && bulletin.verLabels.length">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.verifiedLabels_ }}</v-toolbar-title>
              </v-toolbar>
              <v-card-text class="pt-0">
                <div class="flex-chips">
                  <v-chip label size="small" class="flex-chip" v-for="vlabel in bulletin.verLabels"
                          :key="vlabel.id">
                    {{ vlabel.title }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'locations')" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2"  v-if="bulletin.locations && bulletin.locations.length">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.locations_ }}</v-toolbar-title>
              </v-toolbar>
              <v-card-text class="pt-0">
                <div class="flex-chips">
                  <v-chip label size="small" prepend-icon="mdi-map-marker" class="flex-chip" v-for="location in bulletin.locations"
                          :key="location.id">
                    {{ location.full_string }}
                  </v-chip>
                </div>
              </v-card-text>
            </v-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'related_bulletins')" :class="$root.fieldClassDrawer(field)">
            <related-bulletins-card v-if="bulletin" :entity="bulletin"
                              :relationInfo="$root.btobInfo"> </related-bulletins-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'related_actors')" :class="$root.fieldClassDrawer(field)">
            <related-actors-card v-if="bulletin" :entity="bulletin"
                                :relationInfo="$root.atobInfo" ></related-actors-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'related_incidents')" :class="$root.fieldClassDrawer(field)">
            <related-incidents-card v-if="bulletin" :entity="bulletin"
                                      :relationInfo="$root.itobInfo"></related-incidents-card>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'publish_date')" :class="$root.fieldClassDrawer(field)">
            <uni-field :caption="translations.publishDate_" :english="$root.formatDate(bulletin.publish_date)"></uni-field>
          </div>
          <div v-else-if="$root.isFieldActive(field, 'documentation_date')" :class="$root.fieldClassDrawer(field)">
            <uni-field :caption="translations.documentationDate_" :english="$root.formatDate(bulletin.documentation_date)"></uni-field>
          </div>
          <div v-else-if="$root.isFieldActive(field)" :class="$root.fieldClassDrawer(field)">
            <div v-if="Array.isArray(bulletin?.[field.name])">
              <v-card class="ma-2" v-if="bulletin?.[field.name] && bulletin?.[field.name].length">
                <v-toolbar density="compact">
                    <v-toolbar-title class="text-subtitle-1">{{ field.title }}</v-toolbar-title>
                </v-toolbar>
                <v-card-text class="pt-0">
                  <div class="flex-chips">
                    <v-chip label size="small" class="flex-chip" v-for="value in bulletin?.[field.name]" :key="value">
                      {{ $root.findFieldOptionByValue(field, value)?.label ?? value }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </div>
            <div v-else-if="field.field_type === 'datetime'">
              <uni-field v-if="bulletin?.[field.name]" :caption="field.title" :english="$root.formatDate(bulletin?.[field.name])"></uni-field>
            </div>
            <div v-else>
              <uni-field v-if="bulletin?.[field.name]" :caption="field.title" :english="$root.findFieldOptionByValue(field, bulletin?.[field.name])?.label ?? bulletin?.[field.name]"></uni-field>
            </div>
          </div>
        </template>
      </div>

      <!-- Media -->
      <v-card class="ma-2" v-if="bulletin.medias && bulletin.medias.length">
        <v-toolbar density="compact">
            <v-toolbar-title class="text-subtitle-1">{{ translations.media_ }}</v-toolbar-title>
        </v-toolbar>

        <inline-media-renderer
          :media="expandedMedia"
          :media-type="expandedMediaType"
          ref="inlineMediaRendererRef"
          @fullscreen="handleFullscreen"
          @close="closeExpandedMedia"
        ></inline-media-renderer>
        
        <v-card-text>
          
          <media-grid prioritize-videos :medias="bulletin.medias" @media-click="handleExpandedMedia"></media-grid>
        </v-card-text>
      </v-card>

      <!-- Review -->
      <v-card v-if="showReview(bulletin)" variant="outlined" elevation="0" class="ma-3" color="teal-lighten-2">
        <v-card-text>
          <div class="px-1">{{ translations.review_ }}</div>
          <read-more>
            <div v-html="bulletin.review" class="pa-1 my-2 grey--text text--darken-2">
            </div>
          </read-more>
          <v-chip class="mt-4" color="primary">{{ bulletin.review_action }}</v-chip>
        </v-card-text>
      </v-card>

      <!-- Log -->
      <v-card v-if="logAllowed()" variant="flat">
        <v-toolbar density="compact">
          <v-toolbar-title>
          <v-btn variant="plain" class="text-subtitle-2" append-icon="mdi-history" :loading="hloading"
                 @click="loadRevisions">
            {{ translations.logHistory_ }}
            
          </v-btn>
            </v-toolbar-title>
        </v-toolbar>
        
        <v-card-text> 


          <template v-for="(revision,index) in revisions">
            <v-sheet class="my-1 pa-3  align-center d-flex">
              <span class="caption"><read-more class="mb-2">{{ revision.data['comments'] }}</read-more>
                <v-chip label size="small"
                >{{ translate_status(revision.data.status) }}</v-chip> -
                {{ $root.formatDate(revision.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}
                - {{ translations.by_ }} {{ revision.user.username }}</span>
              <v-spacer></v-spacer>

              <v-btn icon="mdi-vector-difference" v-if="diffAllowed()" v-show="index!=revisions.length-1"
                     @click="showDiff($event,index)"
                     class="mx-1" variant="flat" size="small"
              >

              </v-btn>

            </v-sheet>

          </template>

        </v-card-text>

      </v-card>
      <v-dialog
          v-model="diffDialog"
          max-width="770px"
      >
        <v-card class="pa-5">
          <v-card-text>
            <div v-html="diffResult">
            </div>
          </v-card-text>
        </v-card>

      </v-dialog>
      <!-- Root card -->
    </v-card>


  `,
});
