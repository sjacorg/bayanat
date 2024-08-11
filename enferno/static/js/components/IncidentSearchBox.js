const IncidentSearchBox = Vue.defineComponent({
  props: {
    modelValue: {
      type: Object,
      required: true,
    },
    users: {
      type: Array,
    },
    extraFilters: {
      type: Boolean,
      default: true,
    },
    roles: {
      type: Array,
    },
  },

  emits: ['update:modelValue', 'search'],
  data: () => {
    return {
      translations: window.translations,
      q: {},
      potentialViolationsCategories: [],
      claimedViolationsCategories: [],
    };
  },
  watch: {
    q: {
      handler(newVal) {
        this.$emit('update:modelValue', newVal);
      },
      deep: true,
    },
    modelValue: function (newVal, oldVal) {
      if (newVal !== oldVal) {
        this.q = newVal;
      }
    },
  },
  created() {
    this.q = this.modelValue;
    this.fetchViolationCategories('potentialviolation', 'potentialViolationsCategories');
    this.fetchViolationCategories('claimedviolation', 'claimedViolationsCategories');
  },
  methods: {
    fetchViolationCategories(endpointSuffix, categoryVarName) {
      axios
        .get(`/admin/api/${endpointSuffix}/`)
        .then((response) => {
          this[categoryVarName] = response.data.items;
        })
        .catch((error) => {
          console.error(`Error fetching data for ${categoryVarName}`);
        });
    },
  },

  template: `
      <v-sheet>
        <v-card class="pa-4">


          <v-container class="fluid">
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
              </v-col>
            </v-row>

            <v-row>
              <v-col  md="12" >
                  <pop-date-range-field
                      :label="translations.createdDate_"
                      v-model="q.created"
                  />
              </v-col>

              <v-col  md="12">
                  <pop-date-range-field
                      :label="translations.updatedDate_"
                      v-model="q.updated"
                  />
              </v-col>
            </v-row>

            <v-row>
            <v-col md="12">
              <v-card>
                <v-toolbar :title=" translations.events_ ">
                  
                </v-toolbar>
                <v-card-text class="d-flex flex-wrap align-enter ga-2">

                  
                  
                  
                  <pop-date-range-field
                      
                      :label="translations.eventDate_"
                      v-model="q.edate"
                      class="mt-1"
                  ></pop-date-range-field>
                  
                  <v-checkbox   :label="translations.singleEvent_"  v-model="q.singleEvent" color="primary" 
                             ></v-checkbox>
                  
                </v-card-text>
                <div class="d-flex flex-wrap align-center ga-2">



                  <search-field
                      
                      class="w-100 mx-2"
                      
                      v-model="q.etype"
                      api="/admin/api/eventtypes/"
                      :query-params="{ typ: 'for_bulletin' }"
                      item-title="title"
                      item-value="id"
                      :multiple="false"
                      :label="translations.eventType_"
                  ></search-field>

                  
                <location-search-field
                    class="w-100 mx-2"
                    
                    v-model="q.elocation"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="false"
                    :label="translations.includeEventLocations_"
                ></location-search-field>

                </div>
              </v-card> 

            </v-col>
          </v-row>


            <v-row>
              <v-col md="9">
                <span class="caption">{{ translations.accessRoles_ }}</span>
                <v-chip-group
                    column
                    multiple
                    v-model="q.roles">
                  <v-chip v-if="roles" :value="role.id" small v-for="role in roles" filter
                          outlined>{{ role.name }}
                  </v-chip>
                </v-chip-group>
              </v-col>
              <v-col md="3">
                <span class="caption">{{ translations.unrestricted_ }}</span>
                <v-switch v-model="q.norole"></v-switch>
              </v-col>
            </v-row>


            <v-row v-if="extraFilters">
              <v-col>
                <span class="caption">{{ translations.assignedUser_ }}</span>


                <v-chip-group
                    column
                    multiple
                    v-model="q.assigned"
                >
                  <v-chip :value="user.id" small label v-for="user in users" filter outlined>{{ user.name }}</v-chip>
                </v-chip-group>
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
                  <v-chip label :value="user.id" small v-for="user in users" filter outlined>{{ user.name }}</v-chip>
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
                  <v-chip :value="status.en" label small v-for="status in translations.statuses" :key="status.en"
                          filter outlined>{{ status.tr }}
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
              <v-col cols="12">
                <span class="caption pt-2">{{ translations.potentialViolationsCategories_ }}</span>
                <v-chip-group
                    column
                    multiple
                    v-model="q.potentialVCats"
                >
                  <v-chip
                      v-for="category in potentialViolationsCategories"
                      :key="category.id"
                      :value="category.id"
                      label
                      small
                      filter
                      outlined>{{ category.title }}
                  </v-chip>
                </v-chip-group>
              </v-col>
            </v-row>

            <v-row>
              <v-col cols="12">
                <span class="caption pt-2">{{ translations.claimedViolationsCategories_ }}</span>
                <v-chip-group
                    column
                    multiple
                    v-model="q.claimedVCats"
                >
                  <v-chip
                      v-for="category in claimedViolationsCategories"
                      :key="category.id"
                      :value="category.id"
                      label
                      small
                      filter
                      outlined>{{ category.title }}
                  </v-chip>
                </v-chip-group>
              </v-col>
            </v-row>

            <v-row>
              <v-col>
                <div class="d-flex">
                  <search-field
                      v-model="q.labels"
                      api="/admin/api/labels/"
                      :query-params="{}"
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
                    :query-params="{}"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.excludeLabels_"
                ></search-field>


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
                      :post-request="true"
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

          </v-container>


        </v-card>


      </v-sheet>
    `,
});
