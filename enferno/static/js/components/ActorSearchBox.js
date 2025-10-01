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

        this.id_number = {
          type: this.q?.id_number?.type || null,
          number: this.q?.id_number?.number || null,
        };
      }
    },
  },
  created() {
    this.q = this.modelValue;
  },

  mounted() {
    this.$root.fetchSearchableDynamicFields({ entityType: 'actor' });
    this.fetchIdNumberTypes();
    this.q.locTypes = this.q.locTypes || this.translations.actorLocTypes_.map((x) => x.code);
    if ('id_number' in this.q) {
      this.id_number = {
        type: this.q?.id_number?.type || null,
        number: this.q?.id_number?.number || null,
      };
    }
  },

  computed: {
    showGeoMap() {
      return this.q.locTypes?.length > 0;
    },
  },

  
  methods: {
    fetchIdNumberTypes() {
      // If already loaded the exit
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
      if (value === undefined || value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
        this.dyn.delete(field.name)
      } else {
        this.dyn.set(field.name, {
          name: field.name,
          op: operator ?? this.getDefaultOperator(field),
          value: value
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

    getDefaultOperator(field) {
      switch (field.field_type) {
        case 'text':
        case 'long_text': return 'contains'
        case 'number': return 'eq'
        case 'select': return 'all'
        case 'datetime': return 'between'
        default: return 'eq'
      }
    }
  },

  template: `
      <div>

        <v-container class="container--fluid">
          <v-row v-if="showOp">
            <v-col>
              <v-btn-toggle mandatory v-model="q.op">
                <v-btn value="and">{{ translations.and_ }}</v-btn>
                <v-btn value="or">{{ translations.or_ }}</v-btn>
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

              <v-text-field
                  v-model="q.originid"
                  :label="translations.originId_"
                  clearable
              ></v-text-field>
              
                <v-combobox
                    v-model="q.tags"
                    :label="translations.inTagsAll_"
                    multiple
                    chips
                    closable-chips
                    clearable
                ></v-combobox>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opTags" color="primary"
                            class="me-4"></v-checkbox>
                <v-checkbox label="Exact Match" v-model="q.inExact" color="primary"
                            class="me-4"></v-checkbox>
              </div>

                <v-combobox
                    v-model="q.exTags"
                    :label="translations.exTagsAny_"
                    multiple
                    chips
                    closable-chips
                    clearable
                ></v-combobox>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.all_" v-model="q.opExTags" color="primary"
                            class="me-4"></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" v-model="q.exExact" color="primary"
                            class="me-4"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
                <pop-date-range-field
                    :label="translations.publishDate_"
                    v-model="q.pubdate"
                ></pop-date-range-field>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
                <pop-date-range-field 
                    :label="translations.documentationDate_"
                    v-model="q.docdate"
                ></pop-date-range-field>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
                <pop-date-range-field 
                    :label="translations.createdDate_"
                    v-model="q.created"
                ></pop-date-range-field>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
                <pop-date-range-field
                    :label="translations.updatedDate_"
                    v-model="q.updated"
                ></pop-date-range-field>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">
              <v-card class="mb-4">
                <v-toolbar :title=" translations.events_ ">
                  
                </v-toolbar>
                <v-card-text class="d-flex align-enter ga-2">

                <pop-date-range-field
                      :label="translations.eventDate_"
                      v-model="q.edate" 
                      
                  ></pop-date-range-field>
                  
                  <v-checkbox :label="translations.singleEvent_" v-model="q.singleEvent" color="primary"
                              class="ma-3"></v-checkbox>
                  
                </v-card-text>
                <v-card-text class="d-flex align-center ga-2">

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
          <v-col md="12">
            <v-text-field
                v-model="q.first_name"
                :label="translations.firstName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.middle_name"
                :label="translations.middleName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.last_name"
                :label="translations.lastName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.nickname"
                :label="translations.nickName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.father_name"
                :label="translations.fathersName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.mother_name"
                :label="translations.mothersName_"
                clearable
            ></v-text-field>
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
              <v-chip v-if="roles" :value="role.id" v-for="role in roles" filter
                      outlined>{{ role.name }}
              </v-chip>
            </v-chip-group>
          </v-col>
          <v-col md="3">
            <span class="caption">{{translations.unrestricted_}}</span>
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
              <v-chip :value="user.id" label v-for="user in users" filter
                      outlined>{{ user.name }}
              </v-chip>
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
              <v-chip :value="user.id" label v-for="user in users" filter
                      outlined>{{ user.name }}
              </v-chip>
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
              <v-chip :value="status.en" label v-for="status in translations.statuses" :key="status.en"
                      filter
                      outlined>{{ status.tr }}
              </v-chip>
            </v-chip-group>

          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12">
            <span class="caption pt-2">{{ translations.reviewAction_ }}</span>
            <v-chip-group column v-model="q.reviewAction">
              <v-chip :value="translations.noReviewNeeded_" label filter outlined>{{translations.noReviewNeeded_}}</v-chip>
              <v-chip :value="translations.needsReview_" label filter outlined>{{translations.needsReview_}}</v-chip>

            </v-chip-group>

          </v-col>
        </v-row>
        <v-row>

          <v-col>
                <search-field
                    v-model="q.sources"
                    api="/admin/api/sources/"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeSources_"
                ></search-field>
            <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opsources" color="primary"
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
            <v-col>
                <search-field
                    v-model="q.labels"
                    api="/admin/api/labels/"
                    :query-params="{ typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLabels_"
                ></search-field>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.oplabels" color="primary"
                            class="me-4"></v-checkbox>
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

              <v-switch color="primary" v-model="q.childlabels" :label="translations.includeChildLabels_"></v-switch>


            </v-col>
          </v-row>
          <v-row>
            <v-col>
                <search-field
                    v-model="q.vlabels"
                    api="/admin/api/labels/"
                    :query-params="{ fltr: 'verified', typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeVerLabels_"
                ></search-field>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opvlabels" color="primary"
                            class="me-4"></v-checkbox>
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
              <v-switch color="primary" v-model="q.childverlabels" :label="translations.includeChildVerLabels_"></v-switch>
            </v-col>
          </v-row>

          <v-row>
            <v-col>

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
                  v-for="type in translations.actorLocTypes_"
                  :value="type.code"
                  label
                  filter
                  outlined
                  :key="type.code"
              >
                {{ type.tr }}
              </v-chip>
            </v-chip-group>

            <geo-map v-if="showGeoMap"
                     class="flex-grow-1"
                     v-model="q.latlng"
                     :map-height="200"
                     :radius-controls="true"/>
          </v-sheet>

          <v-row>
            <v-col cols="12" md="3">
              <v-select
                  :items="translations.actorSex"
                  item-title="tr"
                  item-value="en"
                  clearable
                  v-model="q.sex"
                  :label="translations.sex_"
              ></v-select>
            </v-col>

            <v-col cols="12" md="3">
              <v-select
                  :items="translations.actorAge"
                  item-title="tr"
                  item-value="en"
                  clearable
                  v-model="q.age"
                  :label="translations.minorAdult_"
              ></v-select>
            </v-col>

            <v-col cols="12" md="3">
              <v-select
                  :items="translations.actorCivilian"
                  item-title="tr"
                  item-value="en"
                  clearable
                  v-model="q.civilian"
                  :label="translations.civilian_"
              ></v-select>
            </v-col>

            <v-col md="3">
              <v-select
                  item-title="tr"
                  item-value="en"
                  clearable
                  :items="translations.actorTypes"
                  v-model="q.type"
                  :label="translations.actorType_"
              ></v-select>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="3">
              <v-text-field
                  :label="translations.occupation_"
                  v-model="q.occupation"
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" md="3">
              <v-text-field
                  :label="translations.position_"
                  v-model="q.position"
              >
              </v-text-field>
            </v-col>

            
            <v-col cols="12" md="3">
              <v-select
                    item-title="tr"
                    item-value="en"
                    clearable
                    :items="translations.actorFamilyStatuses"
                    v-model="q.family_status"
                    :label="translations.familyStatus_"
                ></v-select>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">

                <search-field
                    api="/admin/api/dialects/"
                    :multiple="true"
                    clearable
                    item-title="title"
                    item-value="title"
                    v-model="q.dialects"
                    :label="translations.spokenDialects_"
                ></search-field>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opDialects" color="primary"
                            class="me-4"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">

                <search-field
                    api="/admin/api/ethnographies/"
                    :multiple="true"
                    clearable
                    item-title="title"
                    item-value="title"
                    v-model="q.ethnography"
                    :label="translations.ethnography_"
                ></search-field>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opEthno" color="primary"
                            class="me-4"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">

                <search-field
                    v-model="q.nationality"
                    api="/admin/api/countries/"
                    item-title="title"
                    item-value="title"
                    :multiple="true"
                    clearable
                    :label="translations.nationality_"
                ></search-field>
              <div class="d-flex align-center flex-wrap">
                <v-checkbox :label="translations.any_" v-model="q.opNat" color="primary"
                            class="me-4"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
              <v-card>
                <v-card-item>
                    <v-card-title>{{ translations.idNumber_ }}</v-card-title>
                </v-card-item>
              
                <v-card-text class="pb-0">
                  <v-row class="mb-2">
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
                      ></v-select>
                    </v-col>
                    <v-col cols="12" sm="6">
                      <v-text-field
                          :model-value="id_number.number || null"
                          :label="translations.number_"
                          @update:model-value="updateIdNumber('number', $event)"
                          @keydown.enter="$event.target.blur()"
                          clearable
                      ></v-text-field>
                    </v-col>
                  </v-row>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <div class="mt-12">
            <div v-for="(field, index) in this.$root.formBuilder.searchableDynamicFields" :key="index">
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
