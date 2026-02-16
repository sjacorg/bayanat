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
      openPanels: ['0'],
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

  computed: {
    textSearchCount() {
      let count = 0;
      if (this.q.tsv) count++;
      if (this.q.extsv) count++;
      if (this.q.searchTerms?.length) count++;
      if (this.q.exTerms?.length) count++;
      return count;
    },

    dateCount() {
      let count = 0;
      if (this.q.created) count++;
      if (this.q.updated) count++;
      return count;
    },

    eventCount() {
      let count = 0;
      if (this.q.edate) count++;
      if (this.q.etype) count++;
      if (this.q.elocation) count++;
      if (this.q.singleEvent) count++;
      return count;
    },

    violationsCount() {
      let count = 0;
      if (this.q.potentialVCats?.length) count++;
      if (this.q.claimedVCats?.length) count++;
      return count;
    },

    classificationCount() {
      let count = 0;
      if (this.q.labels?.length) count++;
      if (this.q.exlabels?.length) count++;
      return count;
    },

    workflowCount() {
      let count = 0;
      if (this.q.roles?.length) count++;
      if (this.q.norole) count++;
      if (this.q.assigned?.length) count++;
      if (this.q.unassigned) count++;
      if (this.q.reviewer?.length) count++;
      if (this.q.statuses?.length) count++;
      if (this.q.reviewAction) count++;
      return count;
    },

    locationCount() {
      let count = 0;
      if (this.q.locations?.length) count++;
      if (this.q.exlocations?.length) count++;
      return count;
    },

    dynamicFieldCount() {
      return this.dyn.size;
    },

    totalActiveFilters() {
      return this.textSearchCount + this.dateCount + this.eventCount
        + this.violationsCount + this.classificationCount + this.workflowCount
        + this.locationCount + this.dynamicFieldCount;
    },
  },

  created() {
    this.fetchViolationCategories('potentialviolation', 'potentialViolationsCategories');
    this.fetchViolationCategories('claimedviolation', 'claimedViolationsCategories');
  },

  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'incident' });
    this.$root.fetchSearchableDynamicFields({ entityType: 'incident' });

    (this.q?.dyn || []).forEach(field => {
      this.dyn.set(field.name, field)
    });
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
      <div class="search-box-redesign">

        <!-- Active filters summary -->
        <v-sheet v-if="totalActiveFilters > 0" class="mb-4 pa-3 rounded-lg d-flex align-center" color="primary" variant="tonal">
          <v-icon size="small" class="me-2">mdi-filter-check</v-icon>
          <span class="text-body-2 font-weight-medium">{{ translations.activeFiltersCount_(totalActiveFilters) }}</span>
        </v-sheet>

        <!-- Collapsible search sections -->
        <v-expansion-panels v-model="openPanels" multiple variant="accordion" class="search-panels">

          <!-- 1. TEXT SEARCH (always first, default open) -->
          <v-expansion-panel value="0">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-text-search</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.textSearch_ }}</span>
                <v-badge v-if="textSearchCount > 0" :content="textSearchCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              <v-text-field
                  v-model="q.tsv"
                  :label="translations.contains_"
                  clearable
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-magnify"
                  @keydown.enter="$emit('search',q)"
                  class="mb-1"
              ></v-text-field>

              <v-text-field
                  v-model="q.extsv"
                  :label="translations.notContains_"
                  clearable
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-minus-circle-outline"
                  :hint="translations.separateWordsWithSpaceUseQuotesForExactMatch_"
                  persistent-hint
                  class="mb-1"
              ></v-text-field>

              <!-- Search terms -->
              <v-combobox
                  v-model="q.searchTerms"
                  @update:model-value="val => q.searchTerms = $root.sanitizeCombobox(val)"
                  :label="translations.searchTerms_"
                  multiple
                  chips
                  closable-chips
                  small-chips
                  clearable
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-text-box-search"
              ></v-combobox>

              <div class="d-flex align-center flex-wrap mt-n2 mb-2">
                <v-checkbox :label="translations.any_" density="compact" v-model="q.opTerms" color="primary" class="me-4" hide-details></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" density="compact" v-model="q.termsExact" color="primary" class="me-4" hide-details></v-checkbox>
              </div>

              <v-combobox
                  v-model="q.exTerms"
                  @update:model-value="val => q.exTerms = $root.sanitizeCombobox(val)"
                  :label="translations.excludeTerms_"
                  multiple
                  chips
                  closable-chips
                  clearable
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-text-box-remove"
              ></v-combobox>

              <div class="d-flex align-center mt-n2">
                <v-checkbox :label="translations.all_" density="compact" v-model="q.opExTerms" color="primary" class="me-4" hide-details></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" density="compact" v-model="q.exTermsExact" color="primary" class="me-4" hide-details></v-checkbox>
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 2. DATES -->
          <v-expansion-panel value="1">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-calendar-range</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.dates_ }}</span>
                <v-badge v-if="dateCount > 0" :content="dateCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              <v-row dense>
                <v-col cols="12" md="6">
                  <pop-date-range-field
                      :label="translations.createdDate_"
                      v-model="q.created"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <pop-date-range-field
                      :label="translations.updatedDate_"
                      v-model="q.updated"
                  />
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 3. EVENTS -->
          <v-expansion-panel v-if="$root.isFieldActiveByName('events_section', { entityType: 'incident' })" value="2">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-calendar-alert</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.events_ }}</span>
                <v-badge v-if="eventCount > 0" :content="eventCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              <v-row dense>
                <v-col cols="12" md="8">
                  <pop-date-range-field
                      :label="translations.eventDate_"
                      v-model="q.edate"
                  ></pop-date-range-field>
                </v-col>
                <v-col cols="12" md="4" class="d-flex align-center">
                  <v-checkbox :label="translations.singleEvent_" density="compact" v-model="q.singleEvent" color="primary" hide-details></v-checkbox>
                </v-col>
              </v-row>
              <v-row dense>
                <v-col cols="12" md="6">
                  <search-field
                      v-model="q.etype"
                      api="/admin/api/eventtypes/"
                      :query-params="{ typ: 'for_bulletin' }"
                      item-title="title"
                      item-value="id"
                      :multiple="false"
                      :label="translations.eventType_"
                  ></search-field>
                </v-col>
                <v-col cols="12" md="6">
                  <location-search-field
                      v-model="q.elocation"
                      api="/admin/api/locations/"
                      item-title="full_string"
                      item-value="id"
                      :multiple="false"
                      :label="translations.includeEventLocations_"
                  ></location-search-field>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 4. VIOLATIONS -->
          <v-expansion-panel v-if="$root.isFieldActiveByName('potential_violations', { entityType: 'incident' }) || $root.isFieldActiveByName('claimed_violations', { entityType: 'incident' })" value="3">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-alert-octagon</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.violations_ }}</span>
                <v-badge v-if="violationsCount > 0" :content="violationsCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>

              <!-- Potential Violations -->
              <template v-if="$root.isFieldActiveByName('potential_violations', { entityType: 'incident' })">
                <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.potentialViolationsCategories_ }}</div>
                <v-chip-group column multiple v-model="q.potentialVCats" selected-class="text-primary">
                  <v-chip
                      v-for="category in potentialViolationsCategories"
                      :key="category.id"
                      :value="category.id"
                      size="small"
                      filter
                      variant="outlined"
                  >{{ category.title }}</v-chip>
                </v-chip-group>
              </template>

              <v-divider v-if="$root.isFieldActiveByName('potential_violations', { entityType: 'incident' }) && $root.isFieldActiveByName('claimed_violations', { entityType: 'incident' })" class="my-3"></v-divider>

              <!-- Claimed Violations -->
              <template v-if="$root.isFieldActiveByName('claimed_violations', { entityType: 'incident' })">
                <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.claimedViolationsCategories_ }}</div>
                <v-chip-group column multiple v-model="q.claimedVCats" selected-class="text-primary">
                  <v-chip
                      v-for="category in claimedViolationsCategories"
                      :key="category.id"
                      :value="category.id"
                      size="small"
                      filter
                      variant="outlined"
                  >{{ category.title }}</v-chip>
                </v-chip-group>
              </template>

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 5. CLASSIFICATION (Labels) -->
          <v-expansion-panel v-if="$root.isFieldActiveByName('labels', { entityType: 'incident' })" value="4">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-tag-multiple</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.classification_ }}</span>
                <v-badge v-if="classificationCount > 0" :content="classificationCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>

              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.LABELS_ }}</div>
              <v-card variant="outlined" class="pa-3 border-thin">
                <search-field
                    v-model="q.labels"
                    api="/admin/api/labels/"
                    :query-params="{}"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLabels_"
                ></search-field>
                <div class="d-flex align-center flex-wrap mt-n1">
                  <v-checkbox :label="translations.any_" density="compact" v-model="q.oplabels" color="primary"
                              class="me-4" hide-details></v-checkbox>
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
              </v-card>

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 6. WORKFLOW & ACCESS -->
          <v-expansion-panel v-if="extraFilters" value="5">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-shield-account</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.workflowAndAccess_ }}</span>
                <v-badge v-if="workflowCount > 0" :content="workflowCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>

              <!-- Access Roles -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.accessRoles_ }}</div>
              <v-row dense>
                <v-col cols="12" md="9">
                  <v-chip-group column multiple v-model="q.roles" selected-class="text-primary">
                    <v-chip v-if="roles" :value="role.id" size="small" v-for="role in roles" filter variant="outlined" :key="role.id">{{ role.name }}</v-chip>
                  </v-chip-group>
                </v-col>
                <v-col cols="12" md="3">
                  <v-switch density="compact" color="primary" v-model="q.norole" :label="translations.unrestricted_" hide-details></v-switch>
                </v-col>
              </v-row>

              <v-divider class="my-3"></v-divider>

              <!-- Assigned User -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.assignedUser_ }}</div>
              <v-row dense>
                <v-col cols="12" md="9">
                  <v-chip-group column multiple v-model="q.assigned" selected-class="text-primary">
                    <template v-for="user in users" :key="user.id">
                      <v-chip :value="user.id" v-show="user.display_name" size="small" filter variant="outlined">{{ user.display_name }}</v-chip>
                    </template>
                  </v-chip-group>
                </v-col>
                <v-col cols="12" md="3">
                  <v-switch density="compact" color="primary" v-model="q.unassigned" :label="translations.unassigned_" hide-details></v-switch>
                </v-col>
              </v-row>

              <v-divider class="my-3"></v-divider>

              <!-- Reviewer -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.reviewer_ }}</div>
              <v-chip-group column multiple v-model="q.reviewer" selected-class="text-primary">
                <template v-for="user in users" :key="user.id">
                  <v-chip :value="user.id" size="small" v-show="user.display_name" filter variant="outlined">{{ user.display_name }}</v-chip>
                </template>
              </v-chip-group>

              <v-divider class="my-3"></v-divider>

              <!-- Workflow Status -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.workflowStatus_ }}</div>
              <v-chip-group column multiple v-model="q.statuses" selected-class="text-primary">
                <v-chip :value="status.en" size="small" v-for="status in translations.statuses"
                        filter variant="outlined" :key="status.en">{{ status.tr }}
                </v-chip>
              </v-chip-group>

              <v-divider class="my-3"></v-divider>

              <!-- Review Action -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.reviewAction_ }}</div>
              <v-chip-group column v-model="q.reviewAction" selected-class="text-primary">
                <v-chip :value="translations.noReviewNeeded_" size="small" filter variant="outlined">{{ translations.noReviewNeeded_ }}</v-chip>
                <v-chip :value="translations.needsReview_" size="small" filter variant="outlined">{{ translations.needsReview_ }}</v-chip>
              </v-chip-group>

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- Workflow & Access (non-extra filters version) -->
          <v-expansion-panel v-if="!extraFilters" value="5">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-shield-account</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.accessAndReview_ }}</span>
                <v-badge v-if="workflowCount > 0" :content="workflowCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              <!-- Access Roles -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.accessRoles_ }}</div>
              <v-row dense>
                <v-col cols="12" md="9">
                  <v-chip-group column multiple v-model="q.roles" selected-class="text-primary">
                    <v-chip v-if="roles" :value="role.id" size="small" v-for="role in roles" filter variant="outlined" :key="role.id">{{ role.name }}</v-chip>
                  </v-chip-group>
                </v-col>
                <v-col cols="12" md="3">
                  <v-switch density="compact" color="primary" v-model="q.norole" :label="translations.unrestricted_" hide-details></v-switch>
                </v-col>
              </v-row>

              <v-divider class="my-3"></v-divider>

              <!-- Review Action -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.reviewAction_ }}</div>
              <v-chip-group column v-model="q.reviewAction" selected-class="text-primary">
                <v-chip :value="translations.noReviewNeeded_" size="small" filter variant="outlined">{{ translations.noReviewNeeded_ }}</v-chip>
                <v-chip :value="translations.needsReview_" size="small" filter variant="outlined">{{ translations.needsReview_ }}</v-chip>
              </v-chip-group>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 7. LOCATIONS -->
          <v-expansion-panel v-if="$root.isFieldActiveByName('locations', { entityType: 'incident' })" value="6">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-map-marker-multiple</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.locations_ }}</span>
                <v-badge v-if="locationCount > 0" :content="locationCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>

              <location-search-field
                  v-model="q.locations"
                  api="/admin/api/locations/"
                  item-title="full_string"
                  item-value="id"
                  :multiple="true"
                  :label="translations.includeLocations_"
                  :post-request="true"
              ></location-search-field>
              <div class="d-flex align-center flex-wrap mt-n1 mb-2">
                <v-checkbox :label="translations.any_" density="compact" v-model="q.oplocations" color="primary"
                            class="me-4" hide-details></v-checkbox>
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

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 8. DYNAMIC FIELDS -->
          <v-expansion-panel v-if="this.$root.formBuilder.searchableDynamicFields.incident?.length" value="7">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-form-textbox</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.customFields_ }}</span>
                <v-badge v-if="dynamicFieldCount > 0" :content="dynamicFieldCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              <div v-for="(field, index) in this.$root.formBuilder.searchableDynamicFields.incident" :key="index">
                <v-text-field
                    v-if="['text', 'long_text'].includes(field.field_type)"
                    :label="field.title"
                    clearable
                    variant="outlined"
                    density="comfortable"
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
                <div v-else-if="['select'].includes(field.field_type)">
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
                    <v-checkbox :disabled="!dyn.get(field.name)?.value" :label="translations.any_" density="compact" :model-value="dyn.get(field.name)?.op === 'any'" @update:model-value="updateDynamicField(dyn.get(field.name)?.value, field, $event ? 'any' : null)" color="primary"
                                  class="me-4" hide-details></v-checkbox>
                  </div>
                </div>
                <pop-date-range-field
                  v-else-if="['datetime'].includes(field.field_type)"
                  :label="field.title"
                  :model-value="dyn.get(field.name)?.value"
                  @update:model-value="updateDynamicField($event, field)"
                />
              </div>
            </v-expansion-panel-text>
          </v-expansion-panel>

        </v-expansion-panels>
      </div>
    `,
});