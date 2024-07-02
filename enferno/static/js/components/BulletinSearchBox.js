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
    },
    showOp: {
      type: Boolean,
      default: true,
    },
    i18n: {
      type: Object,
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

    this.q.locTypes = this.translations.bulletinLocTypes_.map((x) => x.code);
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
                <v-btn small value="and">{{ i18n.and_ }}</v-btn>
                <v-btn small value="or">{{ i18n.or_ }}</v-btn>
              </v-btn-toggle>
            </v-col>
          </v-row>
          <v-row>
            <v-col>

              <v-text-field
                  v-model="q.tsv"
                  :label="i18n.contains_"
                  clearable
                  @keydown.enter="$emit('search',q)"
              ></v-text-field>

              <v-text-field

                  v-model="q.extsv"
                  :label="i18n.notContains_"
                  clearable
              ></v-text-field>
              <div class="d-flex align-center">
                <v-combobox
                    v-model="q.ref"
                    :label="i18n.inRef_"
                    multiple
                    chips
                    closable-chips
                    small-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="i18n.any_" dense v-model="q.opref" color="primary" small
                            class="mx-3"></v-checkbox>
                <v-checkbox label="Exact Match" dense v-model="q.inExact" color="primary" small
                            class="mx-3"></v-checkbox>

              </div>

              <div class="d-flex align-center">

                <v-combobox
                    v-model="q.exref"
                    :label="i18n.exRef_"
                    multiple
                    chips
                    closable-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="i18n.all_" dense v-model="q.opexref" color="primary" small
                            class="mx-3"></v-checkbox>
                <v-checkbox :label="i18n.exactMatch_" dense v-model="q.exExact" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>


            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="translations"
                    ref="publishDateComponent"
                    :label="i18n.publishDate_"
                    v-model="q.pubdate"
                />
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="translations"
                    :label="i18n.documentationDate_"
                    v-model="q.docdate"
                />
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="translations"
                    :label="i18n.createdDate_"
                    v-model="q.created"
                />
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="translations"
                    :label="i18n.updatedDate_"
                    v-model="q.updated"
                />
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">
              <v-card>
                <v-toolbar :title=" i18n.events_ ">
                  
                </v-toolbar>
                <v-card-text class="d-flex align-enter ga-2">

                  
                  
                  
                  <pop-date-range-field
                      :i18n="translations"
                      :label="i18n.eventDate_"
                      v-model="q.edate"
                      class="mt-1"
                  ></pop-date-range-field>
                  
                  <v-checkbox   :label="i18n.singleEvent_" dense v-model="q.singleEvent" color="primary" small
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
                      :label="i18n.eventType_"
                  ></search-field>

                  
                  
                <location-search-field
                    
                    v-model="q.elocation"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="false"
                    :label="i18n.includeEventLocations_"
                ></location-search-field>

                </v-card-text>
              </v-card> 

            </v-col>
          </v-row>

          <v-row v-if="isAdmin">
            <v-col md="9">
              <span class="caption">{{ i18n.accessRoles_ }}</span>
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
              <span class="caption">{{ i18n.unrestricted_ }}</span>
              <v-switch color="primary" v-model="q.norole"></v-switch>
            </v-col>
          </v-row>


          <v-row v-if="extraFilters">

            <v-col md="9">
              <span class="caption">{{ i18n.assignedUser_ }}</span>


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
              <span class="caption">{{ i18n.unassigned_ }}</span>
              <v-switch color="primary" v-model="q.unassigned"></v-switch>
            </v-col>
          </v-row>

          <v-row v-if="extraFilters">
            <v-col cols="12">
              <span class="caption">{{ i18n.reviewer_ }}</span>

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
              <span class="caption pt-2">{{ i18n.workflowStatus_ }}</span>


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
              <span class="caption pt-2">{{ i18n.reviewAction_ }}</span>
              <v-chip-group column v-model="q.reviewAction">
                <v-chip :value="i18n.noReviewNeeded_" label small filter outlined>{{ i18n.noReviewNeeded_ }}</v-chip>
                <v-chip :value="i18n.needsReview_" label small filter outlined>{{ i18n.needsReview_ }}</v-chip>

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
                    :label="i18n.includeSources_"
                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.opsources" color="primary" small
                            class="mx-3"></v-checkbox>

              </div>

              <search-field
                  v-model="q.exsources"
                  api="/admin/api/sources/"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeSources_"

              ></search-field>

              <v-switch color="primary" v-model="q.childsources" :label="i18n.includeChildSources_"></v-switch>


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
                    :label="i18n.includeLabels_"
                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.oplabels" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

              <search-field
                  v-model="q.exlabels"
                  api="/admin/api/labels/"
                  :query-params="{ typ: 'for_bulletin' }"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeLabels_"
              ></search-field>

              <v-switch color="primary" v-model="q.childlabels" :label="i18n.includeChildLabels_"></v-switch>


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
                    :label="i18n.includeVerLabels_"
                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.opvlabels" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

              <search-field
                  v-model="q.exvlabels"
                  api="/admin/api/labels/"
                  :query-params="{ fltr: 'verified', typ: 'for_bulletin' }"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeVerLabels_"
              ></search-field>

              <v-switch color="primary" v-model="q.childverlabels" :label="i18n.includeChildVerLabels_"></v-switch>
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
                    :label="i18n.includeLocations_"

                ></location-search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.oplocations" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>
              <location-search-field
                  v-model="q.exlocations"
                  api="/admin/api/locations/"
                  item-title="full_string"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeLocations_"
                  :post-request="true"
              ></location-search-field>


            </v-col>
          </v-row>

          <v-sheet class="ma-4">
            <span class="caption pt-2">{{ i18n.geospatial_ }}</span>


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
