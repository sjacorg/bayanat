const ActorSearchBox = Vue.defineComponent({
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
    showOp: {
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
      searches: [],
      repr: '',
      q: {},
      qName: '',
      id_number: {
        type: null,
        number: null,
      },
      idNumberTypes: [],
      dyn: new Map(),
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
        this.id_number = {
          type: this.q?.id_number?.type || null,
          number: this.q?.id_number?.number || null,
        };

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

  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'actor' });
    this.$root.fetchSearchableDynamicFields({ entityType: 'actor' });
    this.fetchIdNumberTypes();
    this.q.locTypes = this.q.locTypes || this.translations.actorLocTypes_.map((x) => x.code);
    if ('id_number' in this.q) {
      this.id_number = {
        type: this.q?.id_number?.type || null,
        number: this.q?.id_number?.number || null,
      };
    }

    (this.q?.dyn || []).forEach(field => {
      this.dyn.set(field.name, field)
    });
  },

  computed: {
    showGeoMap() {
      return this.q.locTypes?.length > 0;
    },

    textSearchCount() {
      let count = 0;
      if (this.q.tsv) count++;
      if (this.q.extsv) count++;
      if (this.q.originid) count++;
      if (this.q.searchTerms?.length) count++;
      if (this.q.exTerms?.length) count++;
      if (this.q.tags?.length) count++;
      if (this.q.exTags?.length) count++;
      return count;
    },

    dateCount() {
      let count = 0;
      if (this.q.pubdate) count++;
      if (this.q.docdate) count++;
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

    personalInfoCount() {
      let count = 0;
      if (this.q.first_name) count++;
      if (this.q.middle_name) count++;
      if (this.q.last_name) count++;
      if (this.q.nickname) count++;
      if (this.q.father_name) count++;
      if (this.q.mother_name) count++;
      if (this.q.sex) count++;
      if (this.q.age) count++;
      if (this.q.civilian) count++;
      if (this.q.type) count++;
      if (this.q.occupation) count++;
      if (this.q.position) count++;
      if (this.q.family_status) count++;
      if (this.q.dialects?.length) count++;
      if (this.q.ethnography?.length) count++;
      if (this.q.nationality?.length) count++;
      if (this.q.id_number?.type || this.q.id_number?.number) count++;
      return count;
    },

    classificationCount() {
      let count = 0;
      if (this.q.sources?.length) count++;
      if (this.q.exsources?.length) count++;
      if (this.q.labels?.length) count++;
      if (this.q.exlabels?.length) count++;
      if (this.q.vlabels?.length) count++;
      if (this.q.exvlabels?.length) count++;
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
      if (this.q.originLocations?.length) count++;
      if (this.q.exOriginLocations?.length) count++;
      if (this.q.latlng) count++;
      return count;
    },

    dynamicFieldCount() {
      return this.dyn.size;
    },

    totalActiveFilters() {
      return this.textSearchCount + this.dateCount + this.eventCount
        + this.personalInfoCount + this.classificationCount + this.workflowCount
        + this.locationCount + this.dynamicFieldCount;
    },
  },

  
  methods: {
    fetchIdNumberTypes() {
      // If already loaded then exit
      if (this.idNumberTypes.length) return

      // Fetch and cache IDNumberType data for ID number display and editing
      api.get('/admin/api/idnumbertypes/').then(res => {
          this.idNumberTypes = res.data.items || [];
      }).catch(err => {
          this.idNumberTypes = [];
          console.error('Error fetching id number types:', err);
          this.showSnack(handleRequestError(err));
      })
    },

    updateIdNumber(field, value) {
      this.id_number[field] = value;

      // Create a filtered copy of newVal omitting null values
      const filteredIdNumber = Object.fromEntries(
        Object.entries(this.id_number)
          .filter(([_, v]) => v !== null)
          .map(([key, value]) => [key, value.toString().trim()]),
      );

      this.q = {
        ...this.q,
        id_number: filteredIdNumber,
      };
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

        <!-- AND/OR operator toggle -->
        <v-sheet v-if="showOp" class="mb-4 pa-3 rounded-lg" color="blue-grey-lighten-5">
          <div class="d-flex align-center justify-space-between">
            <div>
              <div class="text-subtitle-2 font-weight-medium">{{ translations.searchLogic_ }}</div>
              <div class="text-caption text-medium-emphasis">{{ translations.howToCombineFilters_ }}</div>
            </div>
            <v-btn-toggle mandatory v-model="q.op" density="comfortable" color="primary" variant="outlined" divided>
              <v-btn value="and">
                <v-icon start size="small">mdi-set-all</v-icon>
                {{ translations.and_ }}
              </v-btn>
              <v-btn value="or">
                <v-icon start size="small">mdi-set-split</v-icon>
                {{ translations.or_ }}
              </v-btn>
            </v-btn-toggle>
          </div>
        </v-sheet>

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

              <v-text-field
                  v-model="q.originid"
                  :label="translations.originId_"
                  clearable
                  variant="outlined"
                  density="comfortable"
                  prepend-inner-icon="mdi-identifier"
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

              <div class="d-flex align-center mt-n2 mb-2">
                <v-checkbox :label="translations.all_" density="compact" v-model="q.opExTerms" color="primary" class="me-4" hide-details></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" density="compact" v-model="q.exTermsExact" color="primary" class="me-4" hide-details></v-checkbox>
              </div>
              <!-- End terms -->

              <template v-if="$root.isFieldActiveByName('tags', { entityType: 'actor' })">
                <v-divider class="my-3"></v-divider>
                <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.TAGS_ }}</div>

                <v-combobox
                    v-model="q.tags"
                    @update:model-value="val => q.tags = $root.sanitizeCombobox(val)"
                    :label="translations.inTagsAll_"
                    multiple
                    chips
                    closable-chips
                    clearable
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-tag-plus"
                ></v-combobox>

                <div class="d-flex align-center flex-wrap mt-n2 mb-2">
                  <v-checkbox :label="translations.any_" density="compact" v-model="q.opTags" color="primary"
                              class="me-4" hide-details></v-checkbox>
                  <v-checkbox :label="translations.exactMatch_" density="compact" v-model="q.inExact" color="primary"
                              class="me-4" hide-details></v-checkbox>
                </div>

                <v-combobox
                    v-model="q.exTags"
                    @update:model-value="val => q.exTags = $root.sanitizeCombobox(val)"
                    :label="translations.exTagsAny_"
                    multiple
                    chips
                    closable-chips
                    clearable
                    variant="outlined"
                    density="comfortable"
                    prepend-inner-icon="mdi-tag-minus"
                ></v-combobox>

                <div class="d-flex align-center mt-n2">
                  <v-checkbox :label="translations.all_" density="compact" v-model="q.opExTags" color="primary"
                              class="me-4" hide-details></v-checkbox>
                  <v-checkbox :label="translations.exactMatch_" density="compact" v-model="q.exExact" color="primary"
                              class="me-4" hide-details></v-checkbox>
                </div>
              </template>
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
                <v-col v-if="$root.isFieldActiveByName('publish_date', { entityType: 'actor' })" cols="12" md="6">
                  <pop-date-range-field
                      :label="translations.publishDate_"
                      v-model="q.pubdate"
                  ></pop-date-range-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('documentation_date', { entityType: 'actor' })" cols="12" md="6">
                  <pop-date-range-field 
                      :label="translations.documentationDate_"
                      v-model="q.docdate"
                  ></pop-date-range-field>
                </v-col>
                <v-col cols="12" md="6">
                  <pop-date-range-field 
                      :label="translations.createdDate_"
                      v-model="q.created"
                  ></pop-date-range-field>
                </v-col>
                <v-col cols="12" md="6">
                  <pop-date-range-field
                      :label="translations.updatedDate_"
                      v-model="q.updated"
                  ></pop-date-range-field>
                </v-col>
              </v-row>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 3. EVENTS -->
          <v-expansion-panel v-if="$root.isFieldActiveByName('events_section', { entityType: 'actor' })" value="2">
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
                      persistent-hint
                      :hint="translations.selEventType_"
                      v-model="q.etype"
                      api="/admin/api/eventtypes/"
                      :query-params="{ typ: 'for_actor' }"
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

          <!-- 4. PERSONAL INFORMATION -->
          <v-expansion-panel value="3">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-account-details</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.personalInformation_ }}</span>
                <v-badge v-if="personalInfoCount > 0" :content="personalInfoCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              
              <!-- Name Fields -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.NAMEINFORMATION_ }}</div>
              <v-row dense>
                <v-col v-if="$root.isFieldActiveByName('first_name', { entityType: 'actor' })" cols="12" md="6">
                  <v-text-field
                      v-model="q.first_name"
                      :label="translations.firstName_"
                      clearable
                      variant="outlined"
                      density="comfortable"
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('middle_name', { entityType: 'actor' })" cols="12" md="6">
                  <v-text-field
                      v-model="q.middle_name"
                      :label="translations.middleName_"
                      clearable
                      variant="outlined"
                      density="comfortable"
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('last_name', { entityType: 'actor' })" cols="12" md="6">
                  <v-text-field
                      v-model="q.last_name"
                      :label="translations.lastName_"
                      clearable
                      variant="outlined"
                      density="comfortable"
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('nickname', { entityType: 'actor' })" cols="12" md="6">
                  <v-text-field
                      v-model="q.nickname"
                      :label="translations.nickName_"
                      clearable
                      variant="outlined"
                      density="comfortable"
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('father_name', { entityType: 'actor' })" cols="12" md="6">
                  <v-text-field
                      v-model="q.father_name"
                      :label="translations.fathersName_"
                      clearable
                      variant="outlined"
                      density="comfortable"
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('mother_name', { entityType: 'actor' })" cols="12" md="6">
                  <v-text-field
                      v-model="q.mother_name"
                      :label="translations.mothersName_"
                      clearable
                      variant="outlined"
                      density="comfortable"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>

              <!-- Demographics -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.DEMOGRAPHICS_ }}</div>
              <v-row dense>
                <v-col v-if="$root.isFieldActiveByName('sex', { entityType: 'actor' })" cols="12" md="3">
                  <v-select
                      :items="translations.actorSex"
                      item-title="tr"
                      item-value="en"
                      clearable
                      v-model="q.sex"
                      :label="translations.sex_"
                      variant="outlined"
                      density="comfortable"
                  ></v-select>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('age', { entityType: 'actor' })" cols="12" md="3">
                  <v-select
                      :items="translations.actorAge"
                      item-title="tr"
                      item-value="en"
                      clearable
                      v-model="q.age"
                      :label="translations.minorAdult_"
                      variant="outlined"
                      density="comfortable"
                  ></v-select>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('civilian', { entityType: 'actor' })" cols="12" md="3">
                  <v-select
                      :items="translations.actorCivilian"
                      item-title="tr"
                      item-value="en"
                      clearable
                      v-model="q.civilian"
                      :label="translations.civilian_"
                      variant="outlined"
                      density="comfortable"
                  ></v-select>
                </v-col>
                <v-col cols="12" md="3">
                  <v-select
                      item-title="tr"
                      item-value="en"
                      clearable
                      :items="translations.actorTypes"
                      v-model="q.type"
                      :label="translations.actorType_"
                      variant="outlined"
                      density="comfortable"
                  ></v-select>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>

              <!-- Professional & Family -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.PROFESSIONALANDFAMILY_ }}</div>
              <v-row dense>
                <v-col v-if="$root.isFieldActiveByName('occupation', { entityType: 'actor' })" cols="12" md="4">
                  <v-text-field
                      :label="translations.occupation_"
                      v-model="q.occupation"
                      variant="outlined"
                      density="comfortable"
                      clearable
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('position', { entityType: 'actor' })" cols="12" md="4">
                  <v-text-field
                      :label="translations.position_"
                      v-model="q.position"
                      variant="outlined"
                      density="comfortable"
                      clearable
                  ></v-text-field>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('family_status', { entityType: 'actor' })" cols="12" md="4">
                  <v-select
                      item-title="tr"
                      item-value="en"
                      clearable
                      :items="translations.actorFamilyStatuses"
                      v-model="q.family_status"
                      :label="translations.familyStatus_"
                      variant="outlined"
                      density="comfortable"
                  ></v-select>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>

              <!-- Cultural Information -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.CULTURALINFORMATION_ }}</div>
              <v-row dense>
                <v-col v-if="$root.isFieldActiveByName('dialects', { entityType: 'actor' })" cols="12">
                  <search-field
                      api="/admin/api/dialects/"
                      :multiple="true"
                      clearable
                      item-title="title"
                      item-value="title"
                      v-model="q.dialects"
                      :label="translations.spokenDialects_"
                  ></search-field>
                  <div class="d-flex align-center flex-wrap mt-n1">
                    <v-checkbox :label="translations.any_" density="compact" v-model="q.opDialects" color="primary"
                                class="me-4" hide-details></v-checkbox>
                  </div>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('ethnographies', { entityType: 'actor' })" cols="12">
                  <search-field
                      api="/admin/api/ethnographies/"
                      :multiple="true"
                      clearable
                      item-title="title"
                      item-value="title"
                      v-model="q.ethnography"
                      :label="translations.ethnography_"
                  ></search-field>
                  <div class="d-flex align-center flex-wrap mt-n1">
                    <v-checkbox :label="translations.any_" density="compact" v-model="q.opEthno" color="primary"
                                class="me-4" hide-details></v-checkbox>
                  </div>
                </v-col>
                <v-col v-if="$root.isFieldActiveByName('nationalities', { entityType: 'actor' })" cols="12">
                  <search-field
                      v-model="q.nationality"
                      api="/admin/api/countries/"
                      item-title="title"
                      item-value="title"
                      :multiple="true"
                      clearable
                      :label="translations.nationality_"
                  ></search-field>
                  <div class="d-flex align-center flex-wrap mt-n1">
                    <v-checkbox :label="translations.any_" density="compact" v-model="q.opNat" color="primary"
                                class="me-4" hide-details></v-checkbox>
                  </div>
                </v-col>
              </v-row>

              <v-divider class="my-4"></v-divider>

              <!-- ID Number -->
              <div v-if="$root.isFieldActiveByName('id_number', { entityType: 'actor' })">
                <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.IDNUMBER_ }}</div>
                <v-card variant="outlined" class="pa-3 border-thin">
                  <v-row dense>
                    <v-col cols="12" sm="6">
                      <v-select
                          :model-value="Number(id_number.type) || null"
                          :items="idNumberTypes"
                          item-title="title"
                          item-value="id"
                          :label="translations.idType_"
                          @update:model-value="updateIdNumber('type', $event)"
                          :hint="translations.leaveBlankToIncludeAllTypes_"
                          persistent-hint
                          clearable
                          variant="outlined"
                          density="comfortable"
                      ></v-select>
                    </v-col>
                    <v-col cols="12" sm="6">
                      <v-text-field
                          :model-value="id_number.number || null"
                          :label="translations.number_"
                          @update:model-value="updateIdNumber('number', $event)"
                          @keydown.enter="$event.target.blur()"
                          clearable
                          variant="outlined"
                          density="comfortable"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </v-card>
              </div>

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 5. CLASSIFICATION (Sources, Labels, Verified Labels) -->
          <v-expansion-panel
            v-if="$root.isFieldActiveByName('sources', { entityType: 'actor' }) || $root.isFieldActiveByName('labels', { entityType: 'actor' }) || $root.isFieldActiveByName('ver_labels', { entityType: 'actor' })"
            value="4"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-tag-multiple</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.classification_ }}</span>
                <v-badge v-if="classificationCount > 0" :content="classificationCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>

              <!-- Sources -->
            <template v-if="$root.isFieldActiveByName('sources', { entityType: 'actor' })">
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.SOURCES_ }}</div>
              <v-card variant="outlined" class="mb-3 pa-3 border-thin">
                <search-field
                    v-model="q.sources"
                    api="/admin/api/sources/"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeSources_"
                ></search-field>
                <div class="d-flex align-center flex-wrap mt-n1">
                  <v-checkbox :label="translations.any_" density="compact" v-model="q.opsources" color="primary"
                              class="me-4" hide-details></v-checkbox>
                </div>
                <search-field
                    v-model="q.exsources"
                    api="/admin/api/sources/"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.excludeSources_"
                ></search-field>
                <v-switch density="compact" color="primary" v-model="q.childsources" :label="translations.includeChildSources_" hide-details></v-switch>
              </v-card>
            </template>

              <!-- Labels -->
            <template v-if="$root.isFieldActiveByName('labels', { entityType: 'actor' })">
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2 mt-2">{{ translations.LABELS_ }}</div>
              <v-card variant="outlined" class="mb-3 pa-3 border-thin">
                <search-field
                    v-model="q.labels"
                    api="/admin/api/labels/"
                    :query-params="{ typ: 'for_actor' }"
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
                    :query-params="{ typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.excludeLabels_"
                ></search-field>
                <v-switch density="compact" color="primary" v-model="q.childlabels" :label="translations.includeChildLabels_" hide-details></v-switch>
              </v-card>
            </template>

              <!-- Verified Labels -->
            <template v-if="$root.isFieldActiveByName('ver_labels', { entityType: 'actor' })">
              <div class="text-caption font-weight-medium text-medium-emphasis mb-2 mt-2">{{ translations.VERIFIEDLABELS_ }}</div>
              <v-card variant="outlined" class="mb-3 pa-3 border-thin">
                <search-field
                    v-model="q.vlabels"
                    api="/admin/api/labels/"
                    :query-params="{ fltr: 'verified', typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeVerLabels_"
                ></search-field>
                <div class="d-flex align-center flex-wrap mt-n1">
                  <v-checkbox :label="translations.any_" density="compact" v-model="q.opvlabels" color="primary"
                              class="me-4" hide-details></v-checkbox>
                </div>
                <search-field
                    v-model="q.exvlabels"
                    api="/admin/api/labels/"
                    :query-params="{ fltr: 'verified', typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.excludeVerLabels_"
                ></search-field>
                <v-switch density="compact" color="primary" v-model="q.childverlabels" :label="translations.includeChildVerLabels_" hide-details></v-switch>
              </v-card>
            </template>

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
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.ACCESSROLES_ }}</div>
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
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.ASSIGNEDUSER_ }}</div>
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
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.REVIEWER_ }}</div>
              <v-chip-group column multiple v-model="q.reviewer" selected-class="text-primary">
                <template v-for="user in users" :key="user.id">
                  <v-chip :value="user.id" size="small" v-show="user.display_name" filter variant="outlined">{{ user.display_name }}</v-chip>
                </template>
              </v-chip-group>

              <v-divider class="my-3"></v-divider>

              <!-- Workflow Status -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.WORKFLOWSTATUS_ }}</div>
              <v-chip-group column multiple v-model="q.statuses" selected-class="text-primary">
                <v-chip :value="status.en" size="small" v-for="status in translations.statuses"
                        filter variant="outlined" :key="status.en">{{ status.tr }}
                </v-chip>
              </v-chip-group>

              <v-divider class="my-3"></v-divider>

              <!-- Review Action -->
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.REVIEWACTION_ }}</div>
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
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.ACCESSROLES_ }}</div>
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
              <div class="text-caption font-weight-medium text-medium-emphasis mb-1">{{ translations.REVIEWACTION_ }}</div>
              <v-chip-group column v-model="q.reviewAction" selected-class="text-primary">
                <v-chip :value="translations.noReviewNeeded_" size="small" filter variant="outlined">{{ translations.noReviewNeeded_ }}</v-chip>
                <v-chip :value="translations.needsReview_" size="small" filter variant="outlined">{{ translations.needsReview_ }}</v-chip>
              </v-chip-group>
            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 7. LOCATIONS & GEO -->
          <v-expansion-panel value="6">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-map-marker-multiple</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.locations_ }}</span>
                <v-badge v-if="locationCount > 0" :content="locationCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text>

              <template v-if="$root.isFieldActiveByName('origin_place', { entityType: 'actor' })">
                <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.ORIGINLOCATIONS_ }}</div>
                <location-search-field
                    v-model="q.originLocations"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeOriginLocations_"
                ></location-search-field>

                <location-search-field
                    v-model="q.exOriginLocations"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="true"
                    :label="translations.excludeOriginLocations_"
                ></location-search-field>
              </template>

              <v-divider v-if="$root.isFieldActiveByName('origin_place', { entityType: 'actor' })" class="my-4"></v-divider>

              <div class="text-caption font-weight-medium text-medium-emphasis mb-2">{{ translations.GEOSPATIAL_ }}</div>
              <v-chip-group multiple column mandatory v-model="q.locTypes" selected-class="text-primary">
                <v-chip
                    v-for="type in translations.actorLocTypes_"
                    :value="type.code"
                    size="small"
                    filter
                    variant="outlined"
                    :key="type.code"
                >{{ type.tr }}</v-chip>
              </v-chip-group>
              
              <geo-map v-if="showGeoMap"
                       class="flex-grow-1 mt-2"
                       v-model="q.latlng"
                       :map-height="200"
                       :radius-controls="true"/>

            </v-expansion-panel-text>
          </v-expansion-panel>

          <!-- 8. DYNAMIC FIELDS -->
          <v-expansion-panel v-if="this.$root.formBuilder.searchableDynamicFields.actor?.length" value="7">
            <v-expansion-panel-title>
              <div class="d-flex align-center ga-2 w-100">
                <v-icon size="small" color="primary">mdi-form-textbox</v-icon>
                <span class="text-subtitle-2 font-weight-medium">{{ translations.customFields_ }}</span>
                <v-badge v-if="dynamicFieldCount > 0" :content="dynamicFieldCount" color="primary" inline></v-badge>
              </div>
            </v-expansion-panel-title>
            <v-expansion-panel-text eager>
              <div v-for="(field, index) in this.$root.formBuilder.searchableDynamicFields.actor" :key="index">
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