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
    };
  },
  watch: {
    id_number: {
      handler(newVal) {
        // Create a filtered copy of newVal omitting null values
        const filteredIdNumber = Object.fromEntries(
          Object.entries(newVal)
            .filter(([_, v]) => v !== null)
            .map(([key, value]) => [key, value.toString().trim()]),
        );

        this.q = {
          ...this.q,
          id_number: filteredIdNumber,
        };
      },
      deep: true,
    },
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
  },

  mounted() {
    this.$root.fetchIdNumberTypes();
    this.q.locTypes = this.q.locTypes || this.translations.actorLocTypes_.map((x) => x.code);
  },

  computed: {
    showGeoMap() {
      return this.q.locTypes?.length > 0;
    },
  },

  template: /*html*/ `
      <v-card outlined class="pa-6">

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
              
              <div class="d-flex align-center">
                <v-combobox
                    v-model="q.tags"
                    :label="translations.inTagsAll_"
                    multiple
                    chips
                    closable-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="translations.any_" v-model="q.opTags" color="primary"
                            class="mx-3"></v-checkbox>
                <v-checkbox label="Exact Match" v-model="q.inExact" color="primary"
                            class="mx-3"></v-checkbox>

              </div>

              <div class="d-flex align-center">

                <v-combobox
                    v-model="q.exTags"
                    :label="translations.exTagsAny_"
                    multiple
                    chips
                    closable-chips
                    clearable
                ></v-combobox>

                <v-checkbox :label="translations.all_" v-model="q.opExTags" color="primary"
                            class="mx-3"></v-checkbox>
                <v-checkbox :label="translations.exactMatch_" v-model="q.exExact" color="primary"
                            class="mx-3"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :label="translations.publishDate_"
                    v-model="q.pubdate"
                ></pop-date-range-field>
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field 
                    :label="translations.documentationDate_"
                    v-model="q.docdate"
                ></pop-date-range-field>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field 
                    :label="translations.createdDate_"
                    v-model="q.created"
                ></pop-date-range-field>
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :label="translations.updatedDate_"
                    v-model="q.updated"
                ></pop-date-range-field>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">
              <v-alert text color="grey lighten-1" class="pa-5 my-3">
                <div class="d-flex align-baseline justify-lg-space-between">


                  <span class="black--text font-weight-bold text-h6">{{ translations.events_ }}</span>
                  <v-checkbox :label="translations.singleEvent_" v-model="q.singleEvent" color="primary"
                              class="ma-3"></v-checkbox>
                </div>


                <div class="d-flex align-baseline">
                  <pop-date-range-field
                      :label="translations.eventDate_"
                      v-model="q.edate" 
                      
                  ></pop-date-range-field>


                  <search-field
                      class="ml-6 mb-3"
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


                </div>


                <location-search-field
                  v-model="q.elocation"
                  api="/admin/api/locations/"
                  item-title="full_string"
                  item-value="id"
                  :multiple="false"
                  :label="translations.includeEventLocations_"
              ></location-search-field>


            </v-alert>

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
            <div class="d-flex">

                <search-field

                    v-model="q.sources"
                    api="/admin/api/sources/"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeSources_"
                ></search-field>
                <v-checkbox :label="translations.any_" v-model="q.opsources" color="primary"
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
                    :query-params="{ typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeLabels_"
                ></search-field>
                <v-checkbox :label="translations.any_" v-model="q.oplabels" color="primary"
                            class="mx-3"></v-checkbox>
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
              <div class="d-flex">
                <search-field
                    v-model="q.vlabels"
                    api="/admin/api/labels/"
                    :query-params="{ fltr: 'verified', typ: 'for_actor' }"
                    item-title="title"
                    item-value="id"
                    :multiple="true"
                    :label="translations.includeVerLabels_"
                ></search-field>
                <v-checkbox :label="translations.any_" v-model="q.opvlabels" color="primary"
                            class="mx-3"></v-checkbox>
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

              <div class="d-flex align-center">
                <search-field
                    api="/admin/api/dialects/"
                    :multiple="true"
                    clearable
                    item-title="title"
                    item-value="title"
                    v-model="q.dialects"
                    :label="translations.spokenDialects_"
                ></search-field>
            
                <v-checkbox :label="translations.any_" v-model="q.opDialects" color="primary"
                            class="mx-3"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">

              <div class="d-flex align-center">
                <search-field
                    api="/admin/api/ethnographies/"
                    :multiple="true"
                    clearable
                    item-title="title"
                    item-value="title"
                    v-model="q.ethnography"
                    :label="translations.ethnography_"
                ></search-field>
             
                <v-checkbox :label="translations.any_" v-model="q.opEthno" color="primary"
                            class="mx-3"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">

              <div class="d-flex align-center">
                <search-field
                                        v-model="q.nationality"
                                        api="/admin/api/countries/"
                                        item-title="title"
                                        item-value="title"
                                        :multiple="true"
                                        clearable
                                        :label="translations.nationality_"
                                ></search-field>
                <v-checkbox :label="translations.any_" v-model="q.opNat" color="primary"
                            class="mx-3"></v-checkbox>
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
                  <div class="d-flex align-center ga-4 mb-2">
                    <v-select
                        :model-value="Number(id_number.type) || Number(q?.id_number?.type) || null"
                        :items="$root.idNumberTypes"
                        item-title="title"
                        item-value="id"
                        :label="translations.idType_"
                        class="w-100"
                        @update:model-value="id_number.type = $event"
                    ></v-select>
                    
                    <v-text-field
                        :model-value="id_number.number || q?.id_number?.number || null"
                        :label="translations.number_"
                        class="w-100"
                        @update:model-value="id_number.number = $event"
                        @keydown.enter="$event.target.blur()"
                    ></v-text-field>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

        </v-container>
      </v-card>

    `,

  methods: {},
});
