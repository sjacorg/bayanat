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
      dyn: new Map(),
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
    modelValue: {
      handler(newVal, oldVal) {
        this.q = newVal;

        // Reset dyn if data cleared
        if (!newVal || !Object.keys(newVal).length) {
          this.dyn = new Map();
          return;
        }

        // If dyn exists and is iterable, rebuild map
        if (Array.isArray(newVal.dyn)) {
          const newMap = new Map();
          for (const query of newVal.dyn) {
            newMap.set(query.name, query);
          }
          this.dyn = newMap;
        } else {
          this.dyn = new Map();
        }
      },
      immediate: true
    }
  },
  created() {
    this.fetchViolationCategories('potentialviolation', 'potentialViolationsCategories');
    this.fetchViolationCategories('claimedviolation', 'claimedViolationsCategories');
  },
  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'incident' });
    this.$root.fetchSearchableDynamicFields({ entityType: 'incident' });
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
    updateDynamicField(value, field, operator) {
      const normalized = Array.isArray(value)
        ? value.filter((item) => item !== undefined && item !== null && item !== '')
        : value;

      if (normalized === undefined || normalized === null || normalized === '' || (Array.isArray(normalized) && normalized.length === 0)) {
        this.dyn.delete(field.name)
      } else {
        this.dyn.set(field.name, {
          name: field.name,
          op: operator ?? this.$root.getSearchOperatorFromFieldType(field),
          value: normalized
        })
      }

      this.buildAndEmitDyn();
    },

    buildAndEmitDyn: debounce(function () {
      const dynamicFieldList = Array.from(this.dyn.values())

      const newQ = { ...this.q }
      if (dynamicFieldList.length) {
        newQ.dyn = dynamicFieldList
      } else {
        delete newQ.dyn
      }

      this.$emit('update:modelValue', newQ)
    }, 350),
  },

  template: `
      <div>
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

            <!-- Search terms -->
            <v-combobox
                v-model="q.searchTerms"
                :label="translations.searchTerms_"
                multiple
                chips
                closable-chips
                small-chips
                clearable
            ></v-combobox>
                  
            <div class="d-flex align-center flex-wrap">
              <v-checkbox :label="translations.any_" v-model="q.opTerms" color="primary" class="me-4"></v-checkbox>
              <v-checkbox :label="translations.exactMatch_" v-model="q.termsExact" color="primary" class="me-4"></v-checkbox>
            </div>
            
            <v-combobox
                v-model="q.exTerms"
                :label="translations.excludeTerms_"
                multiple
                chips
                closable-chips
                clearable
            ></v-combobox>
                  
            <div class="d-flex align-center">
              <v-checkbox :label="translations.all_" v-model="q.opExTerms" color="primary" class="me-4"></v-checkbox>
              <v-checkbox :label="translations.exactMatch_" v-model="q.exTermsExact" color="primary" class="me-4"></v-checkbox>
            </div>
            <!-- End terms -->

            <v-row>
              <v-col  cols="12" >
                  <pop-date-range-field
                      :label="translations.createdDate_"
                      v-model="q.created"
                  />
              </v-col>

              <v-col  cols="12">
                  <pop-date-range-field
                      :label="translations.updatedDate_"
                      v-model="q.updated"
                  />
              </v-col>
            </v-row>

            <v-row>
            <v-col v-if="$root.isFieldActiveByName('events_section', { entityType: 'incident' })" cols="12">
              <v-card class="mb-4">
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
              <v-col v-if="$root.isFieldActiveByName('potential_violations', { entityType: 'incident' })" cols="12">
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
              <v-col v-if="$root.isFieldActiveByName('claimed_violations', { entityType: 'incident' })" cols="12">
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
              <v-col v-if="$root.isFieldActiveByName('labels', { entityType: 'incident' })">
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
              <v-col v-if="$root.isFieldActiveByName('locations', { entityType: 'incident' })">
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

            <div>
              <div v-for="(field, index) in this.$root.formBuilder.searchableDynamicFields.incident" :key="index">
                <v-text-field
                    v-if="['text', 'long_text'].includes(field.field_type)"
                    :label="field.title"
                    clearable
                    :model-value="dyn.get(field.name)?.value"
                    @update:model-value="updateDynamicField($event, field)"
                ></v-text-field>
                <v-number-input
                    v-else-if="['number'].includes(field.field_type)"
                    :label="field.title"
                    clearable
                    :model-value="dyn.get(field.name)?.value"
                    @update:model-value="updateDynamicField($event, field)"
                    control-variant="hidden"
                    :min="-2147483648"
                    :max="2147483647"
                ></v-number-input>
                <div
                  v-else-if="['select'].includes(field.field_type)"
                >
                  <v-autocomplete
                    :model-value="dyn.get(field.name)?.value"
                    @update:model-value="updateDynamicField(field.field_type === 'select' && field?.schema_config?.allow_multiple ? $event : [$event], field)"
                    item-color="secondary"
                    :label="field.title"
                    :items="field.options"
                    item-title="label"
                    item-value="id"
                    :multiple="Boolean(field?.schema_config?.allow_multiple)"
                    chips
                    clearable
                    :closable-chips="Boolean(field?.schema_config?.allow_multiple)"
                    prepend-inner-icon="mdi-magnify"
                    :return-object="false"
                  ></v-autocomplete>
                  <div v-if="Boolean(field?.schema_config?.allow_multiple)" class="d-flex align-center flex-wrap">
                    <v-checkbox :disabled="!dyn.get(field.name)?.value" :label="translations.any_" dense :model-value="dyn.get(field.name)?.op === 'any'" @update:model-value="updateDynamicField(dyn.get(field.name)?.value, field, $event ? 'any' : null)" color="primary" small
                                  class="me-4"></v-checkbox>
                  </div>
                </div>
                <pop-date-range-field
                  v-else-if="['datetime'].includes(field.field_type)"
                  :label="field.title"
                  :model-value="dyn.get(field.name)?.value"
                  @update:model-value="updateDynamicField($event, field)"
                />
              </div>
            </div>

          </v-container>
      </div>
    `,
});
