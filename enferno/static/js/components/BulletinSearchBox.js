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
      dyn: new Map(),
      qName: '',
    };
  },

  mounted() {
    this.$root.fetchDynamicFields({ entityType: 'bulletin' });
    this.$root.fetchSearchableDynamicFields({ entityType: 'bulletin' });
    this.q.locTypes = this.q.locTypes || this.translations.bulletinLocTypes_.map((x) => x.code);
    
    (this.q?.dyn || []).forEach(field => {
      this.dyn.set(field.name, field)
    });
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
    showGeomap() {
      return this.q.locTypes?.length > 0;
    },
  },

  methods: {
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
                  class="mb-4"
                  v-model="q.extsv"
                  :label="translations.notContains_"
                  clearable
                  hint="Separate words with space, use quotes for exact match"
                  persistent-hint
              ></v-text-field>

              <v-text-field
                  class="mb-4"
                  v-model="q.originid"
                  :label="translations.originId_"
                  clearable
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
              ></v-combobox>
                    
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opTerms" color="primary" class="me-4"></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" v-model="q.termsExact" color="primary" class="me-4"></v-checkbox>
              </div>
              
              <v-combobox
                  v-model="q.exTerms"
                  @update:model-value="val => q.exTerms = $root.sanitizeCombobox(val)"
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
              
              <template v-if="$root.isFieldActiveByName('tags', { entityType: 'bulletin' })">
              <v-combobox
                  v-model="q.tags"
                  @update:model-value="val => q.tags = $root.sanitizeCombobox(val)"
                  :label="translations.inTags_"
                  multiple
                  chips
                  closable-chips
                  small-chips
                  clearable
              ></v-combobox>
                    
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" dense v-model="q.opTags" color="primary" small
                            class="me-4"></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" dense v-model="q.inExact" color="primary" small
                            class="me-4"></v-checkbox>

              </div>

              
              <v-combobox
                    v-model="q.exTags"
                    @update:model-value="val => q.exTags = $root.sanitizeCombobox(val)"
                    :label="translations.exTags_"
                    multiple
                    chips
                    closable-chips
                    clearable
                    ></v-combobox>
                    
              <div class="d-flex align-center">
                <v-checkbox :label="translations.all_" dense v-model="q.opExTags" color="primary" small
                            class="me-4"></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" dense v-model="q.exExact" color="primary" small
                            class="me-4"></v-checkbox>
              </div>
              </template>


            </v-col>
          </v-row>

          <v-row>
            <v-col v-if="$root.isFieldActiveByName('publish_date', { entityType: 'bulletin' })" cols="12">
                <pop-date-range-field
                    :label="translations.publishDate_"
                    v-model="q.pubdate"
                />
            </v-col>

            <v-col v-if="$root.isFieldActiveByName('documentation_date', { entityType: 'bulletin' })" cols="12">
                <pop-date-range-field
                    :label="translations.documentationDate_"
                    v-model="q.docdate"
                />
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
                <pop-date-range-field
                    :label="translations.createdDate_"
                    v-model="q.created"
                />
            </v-col>

            <v-col cols="12">
                <pop-date-range-field
                    :label="translations.updatedDate_"
                    v-model="q.updated"
                />
            </v-col>
          </v-row>

          <v-row>
            <v-col v-if="$root.isFieldActiveByName('events_section', { entityType: 'bulletin' })" md="12">
              <v-card class="mb-4">
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

            <v-col v-if="$root.isFieldActiveByName('sources', { entityType: 'bulletin' })">
              <search-field
                    v-model="q.sources"
                    api="/admin/api/sources/"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeSources_"
              ></search-field>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" dense v-model="q.opsources" color="primary" small
                            class="me-4"></v-checkbox>

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
            <v-col v-if="$root.isFieldActiveByName('labels', { entityType: 'bulletin' })">
                <search-field
                    v-model="q.labels"
                    api="/admin/api/labels/"
                    :query-params="{ typ: 'for_bulletin' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLabels_"
                ></search-field>
                <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" dense v-model="q.oplabels" color="primary" small
                            class="me-4"></v-checkbox>
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
            <v-col v-if="$root.isFieldActiveByName('ver_labels', { entityType: 'bulletin' })">
                <search-field
                    v-model="q.vlabels"
                    api="/admin/api/labels/"
                    :query-params="{ fltr: 'verified', typ: 'for_bulletin' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeVerLabels_"
                ></search-field>
                <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" dense v-model="q.opvlabels" color="primary" small
                            class="me-4"></v-checkbox>
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
            <v-col v-if="$root.isFieldActiveByName('locations', { entityType: 'bulletin' })">
                <location-search-field
                    v-model="q.locations"
                    api="/admin/api/locations/"
                    item-title="full_string"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLocations_"

                ></location-search-field>
                <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" dense v-model="q.oplocations" color="primary" small
                            class="me-4"></v-checkbox>
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

          <v-sheet v-if="$root.isFieldActiveByName('geo_locations', { entityType: 'bulletin' })" class="ma-4">
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

          <div>
            <div v-for="(field, index) in this.$root.formBuilder.searchableDynamicFields.bulletin" :key="index">
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
