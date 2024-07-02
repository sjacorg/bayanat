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
    },
    showOp: {
      type: Boolean,
      default: true,
    },
    i18n: {
      type: Object,
    },

    roles: {
      type: Array,
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
      repr: '',
      q: {},
      qName: '',
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
  },

  mounted() {
    this.q.locTypes = this.translations.actorLocTypes_.map((x) => x.code);
  },

  computed: {
    showGeoMap() {
      return this.q.locTypes?.length > 0;
    },
  },

  template: `
      <v-card outlined class="pa-6">

        <v-container class="container--fluid">
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
            </v-col>
          </v-row>
          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="i18n"
                    :label="i18n.publishDate_"
                    v-model="q.pubdate"
                ></pop-date-range-field>
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="i18n" 
                    :label="i18n.documentationDate_"
                    v-model="q.docdate"
                ></pop-date-range-field>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="i18n" 
                    :label="i18n.createdDate_"
                    v-model="q.created"
                ></pop-date-range-field>
              </div>
            </v-col>

            <v-col md="6">
              <div class="d-flex flex-wrap">
                <pop-date-range-field
                    :i18n="i18n"
                    :label="i18n.updatedDate_"
                    v-model="q.updated"
                ></pop-date-range-field>
              </div>
            </v-col>
          </v-row>

          <v-row>
            <v-col md="12">
              <v-alert text color="grey lighten-1" class="pa-5 my-3">
                <div class="d-flex align-baseline justify-lg-space-between">


                  <span class="black--text font-weight-bold text-h6">{{ i18n.events_ }}</span>
                  <v-checkbox :label="i18n.singleEvent_" dense v-model="q.singleEvent" color="primary" small
                              class="ma-3"></v-checkbox>
                </div>


                <div class="d-flex align-baseline">
                  <pop-date-range-field
                      :i18n="i18n"
                      :label="i18n.eventDate_"
                      v-model="q.edate" 
                      
                  ></pop-date-range-field>


                  <search-field
                      class="ml-6 mb-3"
                      persistent-hint
                      :hint="i18n.selEventType_"
                      v-model="q.etype"
                      api="/admin/api/eventtypes/"
                      :query-params="{ typ: 'for_actor' }"
                      item-title="title"
                      item-value="id"
                      :multiple="false"
                      :label="i18n.eventType_"
                  ></search-field>


                </div>


                <location-search-field
                  v-model="q.elocation"
                  api="/admin/api/locations/"
                  item-title="full_string"
                  item-value="id"
                  :multiple="false"
                  :label="i18n.includeEventLocations_"
              ></location-search-field>


            </v-alert>

          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.first_name"
                :label="i18n.firstName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.middle_name"
                :label="i18n.middleName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.last_name"
                :label="i18n.lastName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.nickname"
                :label="i18n.nickName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.father_name"
                :label="i18n.fatherName_"
                clearable
            ></v-text-field>
          </v-col>
        </v-row>

        <v-row>
          <v-col md="12">
            <v-text-field
                v-model="q.mother_name"
                :label="i18n.motherName_"
                clearable
            ></v-text-field>
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
            <span class="caption">{{i18n.unrestricted_}}</span>
            <v-switch v-model="q.norole"></v-switch>
          </v-col>
        </v-row>


        <v-row v-if="extraFilters">
          <v-col>
            <span class="caption">{{ i18n.assignedUser_ }}</span>


            <v-chip-group
                column
                multiple
                v-model="q.assigned"
            >
              <v-chip :value="user.id" small label v-for="user in users" filter
                      outlined>{{ user.name }}
              </v-chip>
            </v-chip-group>
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
              <v-chip :value="user.id" label small v-for="user in users" filter
                      outlined>{{ user.name }}
              </v-chip>
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
              <v-chip :value="status.en" label small v-for="status in translations.statuses" :key="status.en"
                      filter
                      outlined>{{ status.tr }}
              </v-chip>
            </v-chip-group>

          </v-col>
        </v-row>
        <v-row>
          <v-col cols="12">
            <span class="caption pt-2">{{ i18n.reviewAction_ }}</span>
            <v-chip-group column v-model="q.reviewAction">
              <v-chip :value="i18n.noReviewNeeded_" label small filter outlined>{{i18n.noReviewNeeded_}}</v-chip>
              <v-chip :value="i18n.needsReview_" label small filter outlined>{{i18n.needsReview_}}</v-chip>

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
                    :label="i18n.includeLabels_"
                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.oplabels" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

              <search-field
                  v-model="q.exlabels"
                  api="/admin/api/labels/"
                  :query-params="{ typ: 'for_actor' }"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeLabels_"
              ></search-field>


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
                    :label="i18n.includeVerLabels_"
                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.opvlabels" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

              <search-field
                  v-model="q.exvlabels"
                  api="/admin/api/labels/"
                  :query-params="{ fltr: 'verified', typ: 'for_actor' }"
                  item-title="title"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeVerLabels_"
              ></search-field>
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
                  :label="i18n.includeOriginLocations_"
              ></location-search-field>

              <location-search-field
                  v-model="q.exOriginLocations"
                  api="/admin/api/locations/"
                  item-title="full_string"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeOriginLocations_"
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
                  v-for="type in translations.actorLocTypes_"
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

            <geo-map v-if="showGeoMap"
                     class="flex-grow-1"
                     v-model="q.latlng"
                     :map-height="200"
                     :radius-controls="true"/>
          </v-sheet>

          <v-row>
            <v-col cols="12" md="3">
              <v-select
                  :items="i18n.actorSex"
                  item-title="tr"
                  item-value="en"
                  clearable
                  v-model="q.sex"
                  :label="i18n.sex_"
              ></v-select>
            </v-col>

            <v-col cols="12" md="3">
              <v-select
                  :items="i18n.actorAge"
                  item-title="tr"
                  item-value="en"
                  clearable
                  v-model="q.age"
                  :label="i18n.minorAdult_"
              ></v-select>
            </v-col>

            <v-col cols="12" md="3">
              <v-select
                  :items="i18n.actorCivilian"
                  item-title="tr"
                  item-value="en"
                  clearable
                  v-model="q.civilian"
                  :label="i18n.civilian_"
              ></v-select>
            </v-col>

            <v-col md="3">
              <v-select
                  item-title="tr"
                  item-value="en"
                  clearable
                  :items="i18n.actorTypes"
                  v-model="q.type"
                  :label="i18n.actorType_"
              ></v-select>
            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12" md="3">
              <v-text-field
                  :label="i18n.occupation_"
                  v-model="q.occupation"
              >
              </v-text-field>
            </v-col>
            <v-col cols="12" md="3">
              <v-text-field
                  :label="i18n.position_"
                  v-model="q.position"
              >
              </v-text-field>
            </v-col>

            
            <v-col cols="12" md="3">
              <v-select
                    item-title="tr"
                    item-value="en"
                    clearable
                    :items="i18n.actorFamilyStatuses"
                    v-model="q.family_status"
                    :label="i18n.familyStatus_"
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
                    :label="i18n.spokenDialects_"
                ></search-field>
            
                <v-checkbox :label="i18n.any_" dense v-model="q.opDialects" color="primary" small
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
                    :label="i18n.ethnography_"
                ></search-field>
             
                <v-checkbox :label="i18n.any_" dense v-model="q.opEthno" color="primary" small
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
                                        :label="i18n.nationality_"
                                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.opNat" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>

            </v-col>
          </v-row>

          <v-row>
            <v-col md="6">
              <v-text-field dense :label="i18n.idNumber_" v-model="q.id_number"></v-text-field>
            </v-col>
          </v-row>

        </v-container>
      </v-card>

    `,

  methods: {},
});
