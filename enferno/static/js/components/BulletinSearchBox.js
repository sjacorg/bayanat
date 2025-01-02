const BulletinSearchBox = Vue.defineComponent({
  props: {
    modelValue: {
      type: Object,
      required: true,
    },
    users: {
      type: Array,
    },
    roles: {
      type: Array,
    },
    extraFilters: {
      type: Boolean,
      default: true,
    },
    showOp: {
      type: Boolean,
      default: true,
    },
    isAdmin: {
      type: Boolean,
      default: false,
    },
  },

  emits: ['update:modelValue', 'search'],
  data: () => {
    return {
      translations: window.translations,
      searches: [],
      saveDialog: false,
      repr: '',
      q: {},
      qName: '',
    };
  },

  created() {
    this.q = this.modelValue;
  },

  mounted() {

    this.q.locTypes = this.q.locTypes || this.translations.bulletinLocTypes_.map((x) => x.code);

  },

  watch: {
    q: {
      handler(newVal) {
        this.$emit('update:modelValue', newVal);
      },
      deep: true,
    },
    modelValue (newVal, oldVal) {
      if (newVal !== oldVal) {
        this.q = newVal;
      }
    },
  },

  computed: {
    showGeomap() {
      return this.q.locTypes?.length > 0;
    },
  },

  methods: {},

  template: `
    <v-card>
      <v-card-text>
        <v-container fluid>
          <v-row v-if="showOp">
            <v-col>
              <v-btn-toggle mandatory v-model="q.op">
                <v-btn small value="and">{{ translations.and_ }}</v-btn>
                <v-btn small value="or">{{ translations.or_ }}</v-btn>
              </v-btn-toggle>
            </v-col>
          </v-row>
          <v-row>
            <v-col>

              <v-text-field
                  v-model="q.tsv"
                  :label="translations.contains_"
                  clearable
                  @keydown.enter="$emit('search',q)"
              ></v-text-field>

              <v-text-field

                  v-model="q.extsv"
                  :label="translations.notContains_"
                  clearable
              ></v-text-field>
              <div class="d-flex align-center">
                <v-combobox
                    v-model="q.tags"
                    :label="translations.inRef_"
                    multiple
                    chips
                    closable-chips
                    small-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="translations.any_" dense v-model="q.opTags" color="primary" small
                            class="mx-3"></v-checkbox>
                <v-checkbox label="Exact Match" dense v-model="q.inExact" color="primary" small
                            class="mx-3"></v-checkbox>

              </div>

              <div class="d-flex align-center">

                <v-combobox
                    v-model="q.exTags"
                    :label="translations.exRef_"
                    multiple
                    chips
                    closable-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="translations.all_" dense v-model="q.opExTags" color="primary" small
                            class="mx-3"></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" dense v-model="q.exExact" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>


            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    ref="publishDateComponent"
                    :label="translations.publishDate_"
                    v-model="q.pubdate"
                />
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :label="translations.documentationDate_"
                    v-model="q.docdate"
                />
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :label="translations.createdDate_"
                    v-model="q.created"
                />
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :label="translations.updatedDate_"
                    v-model="q.updated"
                />
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">
              <v-card>
                <v-toolbar :title=" translations.events_ ">
                  
                </v-toolbar>
                <v-card-text class="d-flex align-enter ga-2">

                  
                  
                  
                  <pop-date-range-field
                      :label="translations.eventDate_"
                      v-model="q.edate"
                      class="mt-1"
                  ></pop-date-range-field>
                  
                  <v-checkbox   :label="translations.singleEvent_" dense v-model="q.singleEvent" color="primary" small
                             ></v-checkbox>
                  
                </v-card-text>
                <v-card-text class="d-flex align-center ga-2">



                  <search-field
                      
                      v-model="q.etype"
                      api="/admin/api/eventtypes/"
                      :query-params="{ typ: 'for_bulletin' }"
                      item-title="title"
                      item-value="id"
                      :multiple="false"
                      :label="translations.eventType_"
                  ></search-field>

                  
                  
                <location-search-field
                    
                    v-model="q.elocation"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="false"
                    :label="translations.includeEventLocations_"
                ></location-search-field>

                </v-card-text>
              </v-card> 

            </v-col>
          </v-row>

          <v-row>
            <v-col md="9">
              <span class="caption">{{ translations.accessRoles_ }}</span>
              <v-chip-group
                  column
                  multiple
                  v-model="q.roles"
              >
                <v-chip v-if="roles" :value="role.id" small v-for="role in roles" filter
                        outlined>{{ role.name }}
                </v-chip>
              </v-chip-group>
            </v-col>
            <v-col md="3">
              <span class="caption">{{ translations.unrestricted_ }}</span>
              <v-switch color="primary" v-model="q.norole"></v-switch>
            </v-col>
          </v-row>


          <v-row v-if="extraFilters">

            <v-col md="9">
              <span class="caption">{{ translations.assignedUser_ }}</span>


              <v-chip-group
                  column
                  multiple
                  v-model="q.assigned"

              >
                <template v-for="user in users" :key="user.id">
                  <v-chip :value="user.id" v-show="user.name"


                          filter
                  >{{ user.name }}
                  </v-chip>
                </template>
              </v-chip-group>
            </v-col>
            <v-col md="3">
              <span class="caption">{{ translations.unassigned_ }}</span>
              <v-switch color="primary" v-model="q.unassigned"></v-switch>
            </v-col>
          </v-row>

          <v-row v-if="extraFilters">
            <v-col cols="12">
              <span class="caption">{{ translations.reviewer_ }}</span>

              <v-chip-group
                  column
                  multiple
                  v-model="q.reviewer"
              >
                <template v-for="user in users" :key="user.id">
                  <v-chip :value="user.id" label small v-show="user.name" filter
                  >{{ user.name }}
                  </v-chip>
                </template>
              </v-chip-group>
            </v-col>
          </v-row>


          <v-row v-if="extraFilters">
            <v-col cols="12">
              <span class="caption pt-2">{{ translations.workflowStatus_ }}</span>


              <v-chip-group
                  column
                  multiple
                  v-model="q.statuses"
              >
                <v-chip :value="status.en" label small v-for="status in translations.statuses"
                        filter outlined :key="status.en">{{ status.tr }}
                </v-chip>
              </v-chip-group>

            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
              <span class="caption pt-2">{{ translations.reviewAction_ }}</span>
              <v-chip-group column v-model="q.reviewAction">
                <v-chip :value="translations.noReviewNeeded_" label small filter outlined>{{ translations.noReviewNeeded_ }}</v-chip>
                <v-chip :value="translations.needsReview_" label small filter outlined>{{ translations.needsReview_ }}</v-chip>

              </v-chip-group>

            </v-col>
          </v-row>
          <v-row>

            <v-col>
              <div class="d-flex">

                <search-field

                    v-model="q.sources"
                    api="/admin/api/sources/"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeSources_"
                ></search-field>
                <v-checkbox :label="translations.any_" dense v-model="q.opsources" color="primary" small
                            class="mx-3"></v-checkbox>

              </div>

              <search-field
                  v-model="q.exsources"
                  api="/admin/api/sources/"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="translations.excludeSources_"

              ></search-field>

              <v-switch color="primary" v-model="q.childsources" :label="translations.includeChildSources_"></v-switch>


            </v-col>
          </v-row>

          <v-row>
            <v-col>
              <div class="d-flex">
                <search-field
                    v-model="q.labels"
                    api="/admin/api/labels/"
                    :query-params="{ typ: 'for_bulletin' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLabels_"
                ></search-field>
                <v-checkbox :label="translations.any_" dense v-model="q.oplabels" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

              <search-field
                  v-model="q.exlabels"
                  api="/admin/api/labels/"
                  :query-params="{ typ: 'for_bulletin' }"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="translations.excludeLabels_"
              ></search-field>

              <v-switch color="primary" v-model="q.childlabels" :label="translations.includeChildLabels_"></v-switch>


            </v-col>
          </v-row>
          <v-row>
            <v-col>
              <div class="d-flex">
                <search-field
                    v-model="q.vlabels"
                    api="/admin/api/labels/"
                    :query-params="{ fltr: 'verified', typ: 'for_bulletin' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeVerLabels_"
                ></search-field>
                <v-checkbox :label="translations.any_" dense v-model="q.opvlabels" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

              <search-field
                  v-model="q.exvlabels"
                  api="/admin/api/labels/"
                  :query-params="{ fltr: 'verified', typ: 'for_bulletin' }"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="translations.excludeVerLabels_"
              ></search-field>

              <v-switch color="primary" v-model="q.childverlabels" :label="translations.includeChildVerLabels_"></v-switch>
            </v-col>
          </v-row>

          <v-row>
            <v-col>
              <div class="d-flex">
                <location-search-field
                    v-model="q.locations"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLocations_"

                ></location-search-field>
                <v-checkbox :label="translations.any_" dense v-model="q.oplocations" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>
              <location-search-field
                  v-model="q.exlocations"
                  api="/admin/api/locations/"
                  item-title="full_string"
                  item-value="id"
                  :multiple="true"
                  :label="translations.excludeLocations_"
                  :post-request="true"
              ></location-search-field>


            </v-col>
          </v-row>

          <v-sheet class="ma-4">
            <span class="caption pt-2">{{ translations.geospatial_ }}</span>


            <v-chip-group
                multiple
                column
                mandatory
                v-model="q.locTypes"
            >
              <v-chip
                  v-for="type in translations.bulletinLocTypes_"
                  :value="type.code"
                  label
                  small
                  filter
                  outlined
                  :key="type.code"
              >
                {{ type.tr }}
              </v-chip>
            </v-chip-group>

            <geo-map v-if="showGeomap"
                     class="flex-grow-1"
                     v-model="q.latlng"
                     :map-height="200"
                     :radius-controls="true"/>
          </v-sheet>

        </v-container>
      </v-card-text>

    </v-card>



  `,
});
