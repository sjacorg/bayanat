const ActorCard = Vue.defineComponent({
  props: {
    actor: { type: Object, required: true },
    active: { type: Boolean, default: false },
    log: { type: Boolean, default: false },
    diff: { type: Boolean, default: false },
    showEdit: { type: Boolean, default: true },
    close: { type: Boolean, default: false },
    hideMap: { type: Boolean, default: false },
    closeIcon: { type: String, default: 'mdi-close' },
    closePosition: { type: String, default: 'append', validator: v => ['append', 'prepend'].includes(v) }
  },
  emits: ['edit', 'close'],
  mixins: [mediaMixin],
  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'actor' });
    this.fetchData();
  },

  methods: {
    fetchData() {
      this.mapLocations = aggregateActorLocations(this.actor);
    },

    getRelatedValues(item, actor) {
      const titleType = actor.id < item.actor.id ? 'title' : 'reverse_title';
      return extractValuesById(this.$root.atoaInfo, [item.related_as], titleType);
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
        return this.$root.editAllowed(this.actor) && this.showEdit;
      }
      return false;
    },
    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/actorhistory/${this.actor.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          console.error(error.body.data);
        })
        .finally(() => {
          this.hloading = false;
        });
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

  computed: {
    groupedIdNumbers() {
      const idNumbers = this.actor.id_number;

      if (!Array.isArray(idNumbers) || idNumbers.length === 0) {
        return {};
      }

      return idNumbers.reduce((acc, { type, number }) => {
        if (!type || !number) return acc;

        const key = type.id; // group by type.id to avoid duplicate keys
        if (!acc[key]) {
          acc[key] = {
            title: type.title || `Unknown Type ${type.id}`,
            title_tr: type.title_tr || null,
            numbers: [],
          };
        }

        acc[key].numbers.push(number);
        return acc;
      }, {});
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
      mediasReady: 0,
    };
  },

  template: `

      <v-card class="rounded-0">
        <v-card variant="flat" class=" mb-4 rounded-0">
          <v-toolbar class="d-flex px-2 ga-2">
            <v-chip size="small">
              {{ translations.id_ }} {{ actor.id }}
            </v-chip>

            <v-tooltip v-if="actor.originid" location="bottom">
                <template v-slot:activator="{ props }">
                    <v-chip 
                        v-bind="props"
                        prepend-icon="mdi-identifier" 
                        :href="actor.source_link" 
                        target="_blank" 
                        label
                        append-icon="mdi-open-in-new"
                        class="ml-1">
                        {{ actor.originid }}

                    </v-chip>
                </template>
                {{ translations.originid_ }}
            </v-tooltip>

            <v-btn variant="tonal" size="small" prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2"
                  @click="$emit('edit',actor)">
              {{ translations.edit_ }}
            </v-btn>

            <v-btn size="small" class="ml-2" variant="tonal" prepend-icon="mdi-graph-outline"
                  @click.stop="$root.$refs.viz.visualize(actor)">
              {{ translations.visualize_ }}
            </v-btn>

            <template #[closePosition]>
              <v-btn variant="text" :icon="closeIcon" v-if="close" @click="$emit('close',$event.target.value)"></v-btn>
            </template>
            
          </v-toolbar>

          <v-sheet v-if="actor.assigned_to || actor.status" variant="flat" class="d-flex pa-0   ga-2">
            <div class="pa-2" v-if="actor.assigned_to">
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-chip 
                      
                      variant="text"
                    v-bind="props"
                    prepend-icon="mdi-account-circle-outline">
                    {{ actor.assigned_to['name'] }}
                  </v-chip>
                </template>
                {{ translations.assignedUser_ }}
              </v-tooltip>
            </div>

            <v-divider v-if="actor.assigned_to" vertical ></v-divider>
            
            <div class="pa-2" v-if="actor.status">
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-chip 
                      variant="text"
                    v-bind="props"
                    prepend-icon="mdi-delta" class="mx-1">
                    {{ actor.status }}
                  </v-chip>
                </template>
                {{ translations.workflowStatus_ }}
              </v-tooltip>
            </div>
          </v-sheet> 

          <v-divider></v-divider>
          <v-card v-if="actor.roles?.length" variant="flat" class="ma-2 d-flex align-center pa-2 flex-grow-1">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-icon color="blue-darken-3" class="mx-2" size="small" v-bind="props">mdi-lock</v-icon>
              </template>
              {{ translations.accessRoles_ }}
            </v-tooltip>
            <v-chip label size="small" v-for="role in actor.roles" :color="role.color" class="mx-1">{{ role.name }}</v-chip>
          </v-card>  
          <v-divider v-if="actor.roles?.length" ></v-divider>
        
          <v-card v-if="actor.tags?.length" variant="flat" class="ma-2 pa-2 flex-grow-1">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-icon color="primary" class="mx-2" size="small" v-bind="props">mdi-tag</v-icon>
              </template>
              {{ translations.tags_ }}
            </v-tooltip>
            <v-chip size="small" v-for="tag in actor.tags" class="caption black--text mx-1 mb-1">{{ tag }}</v-chip>
          </v-card>
          <v-divider v-if="actor.tags?.length" ></v-divider>
      
          <v-card v-if="actor.source_link && actor.source_link !='NA'" variant="flat" class=" pa-2 ma-1 d-flex align-center flex-grow-1">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    
                  v-bind="props"
                  prepend-icon="mdi-link-variant"
                  :href="actor.source_link" 
                  target="_blank" 
                  variant="text"
                  append-icon="mdi-open-in-new"
                  label
                  class="white--text ml-1">
                  {{ actor.source_link }}
                  
                </v-chip>
              </template>
              {{ translations.sourceLink_ }}: {{ actor.source_link }}
            </v-tooltip>
          </v-card> 
          <v-divider v-if="actor.source_link" ></v-divider>
        </v-card>

        <div class="d-flex flex-wrap">
        <template v-for="(field) in $root.cardDynamicFields('actor')">
          <div
            v-if="$root.isFieldActiveAndHasContent(field, 'name', [actor.name, actor.name_ar])"
            :class="$root.fieldClassDrawer(field)"
          >
            <v-sheet class="pa-3 text-center">
              <h2 class="text-subtitle-2">{{ actor.name }} {{ actor.name_ar }}</h2>
            </v-sheet>
            <v-divider class="my-3"></v-divider>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'nickname', [actor.nickname, actor.nickname_ar])"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.nickName_" :english="actor.nickname" :arabic="actor.nickname_ar"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'first_name', [actor.first_name, actor.first_name_ar])"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.firstName_" :english="actor.first_name" :arabic="actor.first_name_ar"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'middle_name', [actor.middle_name, actor.middle_name_ar])"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.middleName_" :english="actor.middle_name" :arabic="actor.middle_name_ar"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'last_name', [actor.last_name, actor.last_name_ar])"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.lastName_" :english="actor.last_name" :arabic="actor.last_name_ar"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'father_name', [actor.father_name, actor.father_name_ar]) || $root.isFieldActiveAndHasContent(field, 'mother_name', [actor.mother_name, actor.mother_name_ar])"
            :class="[...$root.fieldClassDrawer(field), 'd-flex']"
          >
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'father_name', [actor.father_name, actor.father_name_ar])" :caption="translations.fathersName_" :english="actor.father_name" :arabic="actor.father_name_ar"></uni-field>
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'mother_name', [actor.mother_name, actor.mother_name_ar])" :caption="translations.mothersName_" :english="actor.mother_name" :arabic="actor.mother_name_ar"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'sex', actor._sex) || $root.isFieldActiveAndHasContent(field, 'age', actor._age) || $root.isFieldActiveAndHasContent(field, 'civilian', actor._civilian)"
            :class="[...$root.fieldClassDrawer(field), 'd-flex']"
          >
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'sex', actor._sex)" :caption="translations.sex_" :english="actor._sex"></uni-field>
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'age', actor._age)" :caption="translations.age_" :english="actor._age"></uni-field>
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'civilian', actor._civilian)" :caption="translations.civilian_" :english="actor._civilian"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'origin_place', actor.origin_place?.full_string)"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.originPlace_" :english="actor.origin_place.full_string"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'family_status', actor.family_status)"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.familyStatus_" :english="actor.family_status"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'occupation', [actor.occupation, actor.occupation_ar]) || $root.isFieldActiveAndHasContent(field, 'position', [actor.position, actor.position_ar])"
            :class="[...$root.fieldClassDrawer(field), 'd-flex']"
          >
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'occupation', [actor.occupation, actor.occupation_ar])" :caption="translations.occupation_" :english="actor.occupation" :arabic="actor.occupation_ar"></uni-field>
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'position', [actor.position, actor.position_ar])" :caption="translations.position_" :english="actor.position" :arabic="actor.position_ar"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'dialects', actor.dialects)"
            :class="$root.fieldClassDrawer(field)"
          >
            <v-card :subtitle="translations.spokenDialects_" variant="flat" class="mx-2 my-1 pa-2 d-flex align-center">
              <div class="flex-chips">
                <v-chip size="small" v-for="e in actor.dialects" class="flex-chip">{{ e.title }}</v-chip>
              </div>
            </v-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'ethnographies', actor.ethnographies)"
            :class="$root.fieldClassDrawer(field)"
          >
            <v-card :subtitle="translations.ethnographicInfo_" variant="flat" class="mx-2 my-1 pa-2 d-flex align-center">
              <div class="flex-chips">
                <v-chip size="small" v-for="e in actor.ethnographies" class="flex-chip">{{ e.title }}</v-chip>
              </div>
            </v-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'nationalities', actor.nationalities)"
            :class="$root.fieldClassDrawer(field)"
          >
            <v-card :subtitle="translations.nationalities_" variant="flat" class="mx-2 my-1 pa-2 d-flex align-center">
              <div class="flex-chips">
                <v-chip size="small" v-for="n in actor.nationalities" class="flex-chip">{{ n.title }}</v-chip>
              </div>
            </v-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'id_number', actor.id_number)"
            :class="$root.fieldClassDrawer(field)"
          >
            <v-card variant="flat" class="mx-8 my-2">
              <div class="d-flex flex-column">
                <div class="text-subtitle-2 text-medium-emphasis">{{ translations.idNumbers_ }}</div>
                <div class="flex-chips">
                  <template v-for="(group, typeName) in groupedIdNumbers" :key="typeName">
                    <v-chip size="small" class="flex-chip mr-1 mb-1" variant="outlined">
                      <strong>{{ group.title }}:&nbsp;</strong> {{ group.numbers.join(', ') }}
                    </v-chip>
                  </template>
                </div>
              </div>
            </v-card>
          </div>

          <div :class="$root.fieldClassDrawer(field)" v-else-if="field.name === 'actor_profiles'">
            <div v-if="$root.isFieldActiveAndHasContent(field, 'actor_profiles', actor.id)">
              <actor-profiles :actor-id="actor.id" />
            </div>

            <div v-if="!hideMap">
              <v-divider></v-divider>
              <v-card variant="flat">
                <global-map v-model="mapLocations"></global-map>
              </v-card>
              <v-divider></v-divider>
              <v-card variant="flat">
                <new-global-map :entities="[actor]"></new-global-map>
              </v-card>
            </div>
          </div>

          <div v-else-if="$root.isFieldActiveAndHasContent(field, 'events_section', actor.events)" :class="$root.fieldClassDrawer(field)">
            <v-card class="ma-2">
              <v-toolbar density="compact">
                <v-toolbar-title class="text-subtitle-1">{{ translations.events_ }}</v-toolbar-title>
              </v-toolbar>
              <v-card-text class="pt-0 px-2 pb-2">
                <event-card v-for="(event, index) in actor.events" :number="index+1" :key="event.id" :event="event"></event-card>
              </v-card-text>
            </v-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'medias', actor.medias)"
            :class="$root.fieldClassDrawer(field)"
          >
            <v-card class="ma-2">
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
                <media-grid prioritize-videos :medias="actor.medias" @media-click="handleExpandedMedia"></media-grid>
              </v-card-text>
            </v-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'related_bulletins', actor)"
            :class="$root.fieldClassDrawer(field)"
          >
            <related-bulletins-card :entity="actor" :relationInfo="$root.atobInfo"></related-bulletins-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'related_actors', actor)"
            :class="$root.fieldClassDrawer(field)"
          >
            <related-actors-card :entity="actor" :relationInfo="$root.atoaInfo"></related-actors-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'related_incidents', actor)"
            :class="$root.fieldClassDrawer(field)"
          >
            <related-incidents-card :entity="actor" :relationInfo="$root.itoaInfo"></related-incidents-card>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'publish_date', actor.publish_date) || $root.isFieldActiveAndHasContent(field, 'documentation_date', actor.documentation_date)"
            :class="[...$root.fieldClassDrawer(field), 'd-flex']"
          >
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'publish_date', actor.publish_date)" :caption="translations.publishDate_" :english="$root.formatDate(actor.publish_date)"></uni-field>
            <uni-field v-if="$root.isFieldActiveAndHasContent(field, 'documentation_date', actor.documentation_date)" :caption="translations.documentationDate_" :english="$root.formatDate(actor.documentation_date)"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, 'source_link', actor.source_link)"
            :class="$root.fieldClassDrawer(field)"
          >
            <uni-field :caption="translations.sourceLink_" :english="actor.source_link"></uni-field>
          </div>

          <div
            v-else-if="$root.isFieldActiveAndHasContent(field, field.name, actor?.[field.name])"
            :class="$root.fieldClassDrawer(field)"
          >
            <div v-if="Array.isArray(actor?.[field.name]) && actor?.[field.name].length">
              <v-card class="ma-2">
                <v-toolbar density="compact">
                  <v-toolbar-title class="text-subtitle-1">{{ field.title }}</v-toolbar-title>
                </v-toolbar>
                <v-card-text class="pt-0">
                  <div class="flex-chips">
                    <v-chip label size="small" class="flex-chip" v-for="value in actor?.[field.name]" :key="value">
                      {{ $root.findFieldOptionByValue(field, value)?.label ?? value }}
                    </v-chip>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <div v-else-if="field.field_type === 'datetime'">
              <uni-field :caption="field.title" :english="$root.formatDate(actor?.[field.name])"></uni-field>
            </div>

            <div v-else>
              <uni-field :caption="field.title" :english="$root.findFieldOptionByValue(field, actor?.[field.name])?.label ?? actor?.[field.name]"></uni-field>
            </div>
          </div>
        </template>
      </div>

        <v-card v-if="actor.status==='Peer Reviewed'" variant="outlined" elevation="0" class="ma-2" color="teal-lighten-2">
          <v-card-text>
            <div class="px-1 title black--text">{{ translations.review_ }}</div>
            <read-more><div v-html="actor.review" class="pa-1 my-2  "></div></read-more>
            <v-chip class="mt-4" size="small" label color="lime">{{ actor.review_action }}</v-chip>
          </v-card-text>
        </v-card>

        <!-- Log -->
        <v-card v-if="logAllowed()" outline elevation="0" class="ma-2">
          <v-card-text>
            <h3 class="title black--text align-content-center">{{ translations.logHistory_ }}
              <v-btn fab :loading="hloading" @click="loadRevisions" size="small" class="elevation-0 align-content-center">
                <v-icon>mdi-history</v-icon>
              </v-btn>
            </h3>

            <template v-for="(revision,index) in revisions">
              <v-card color="grey" dense flat class="my-1 pa-2 d-flex align-center">
              <span class="caption"><read-more class="mb-2">{{ revision.data['comments'] }}</read-more>
              <v-chip size="small" label color="gv">{{ translate_status(revision.data.status) }}</v-chip> -
                {{ $root.formatDate(revision.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}
                - {{ translations.by_ }} {{ revision.user.username }}</span>
                <v-spacer></v-spacer>

                <v-btn v-if="diffAllowed()" v-show="index!==revisions.length-1" @click="showDiff($event,index)"
                       class="mx-1"
                       color="grey" icon size="small">
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
