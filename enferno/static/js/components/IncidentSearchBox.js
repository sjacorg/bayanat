Vue.component('incident-search-box', {
    props: {
        value: {
            type: Object, required: true
        }, users: {
            type: Array
        }, extraFilters: {
            type: Boolean
        }, i18n: {
            type: Object
        }, roles: {
            type: Array
        }, isAdmin: {
            type: Boolean, default: false
        }
    },

    data: () => {
        return {
            q: {},
            potentialViolationsCategories: [],
            claimedViolationsCategories: [],
        }
    }, watch: {


        q: {
            handler(newVal) {

                this.$emit('input', newVal)
            }, deep: true
        }, value: function (newVal, oldVal) {

            if (newVal !== oldVal) {
                this.q = newVal;
            }
        }

    }, created() {
        this.q = this.value;
        this.fetchViolationCategories('potentialviolation', 'potentialViolationsCategories');
        this.fetchViolationCategories('claimedviolation', 'claimedViolationsCategories');

    }, methods: {
        fetchViolationCategories(endpointSuffix, categoryVarName) {
            axios.get(`/admin/api/${endpointSuffix}/`)
                .then(response => {
                    this[categoryVarName] = response.data.items;
                })
                .catch(error => {
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
                          :label="i18n.createdDate_"
                          v-model="q.created"
                      />
                  </div>
              </v-col>
      
              <v-col md="6">
                  <div class="d-flex flex-wrap">
                      <pop-date-range-field
                          :label="i18n.updatedDate_"
                          v-model="q.updated"
                      />
                  </div>
              </v-col>
          </v-row>
        
          <v-row>
          <v-col md="12">
            <v-alert text color="grey lighten-1" class="pa-5 my-3">
              <div class="d-flex align-baseline justify-lg-space-between" >
                
                
                <span class="black--text font-weight-bold text-h6">Events</span>
                <v-checkbox :label="i18n.singleEvent_" dense v-model="q.singleEvent" color="primary" small
                          class="ma-3"></v-checkbox>
              </div>
              
              
              
              <div class="d-flex align-baseline"  > 
                    <pop-date-range-field
                        :label="i18n.eventDate_"
                        v-model="q.edate"
                        
                        class="mt-2"
                        
                    />

              


                  <search-field
                      class="ml-6 mb-3"
                      persistent-hint 
                      hint="select event type"
                      v-model="q.etype"
                      api="/admin/api/eventtypes/"
                      query-params="&typ=for_bulletin"
                      item-text="title"
                      item-value="id"
                      :multiple="false"
                      :label="i18n.eventType_"
                  ></search-field>

              
                </div>

              
              
                
                  <search-field
                      v-model="q.elocation"
                      api="/admin/api/locations/"
                      item-text="full_string"
                      item-value="id"
                      :multiple="false"
                      :label="i18n.includeEventLocations_"
                  ></search-field>

                


            </v-alert>

          </v-col>
        </v-row>


          <v-row v-if="isAdmin">
            <v-col md="9">
              <span class="caption">Access Roles</span>
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
              <span class="caption">Unrestricted</span>
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
                <v-chip :value="user.id" small label v-for="user in users" filter outlined>{{ user.name }}</v-chip>
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
                <v-chip label :value="user.id" small v-for="user in users" filter outlined>{{ user.name }}</v-chip>
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
                <v-chip :value="status.en" label small v-for="status in translations.statuses_" :key="status.en"
                        filter outlined>{{ status.tr }}
                </v-chip>
              </v-chip-group>

            </v-col>
          </v-row>

          <v-row>
            <v-col cols="12">
              <span class="caption pt-2">{{ i18n.reviewAction_ }}</span>
              <v-chip-group column v-model="q.reviewAction">
                <v-chip value="No Review Needed" label small filter outlined>No Review Needed</v-chip>
                <v-chip value="Needs Review" label small filter outlined>Needs Review</v-chip>

              </v-chip-group>

            </v-col>
          </v-row>

          <v-row v-if="extraFilters">
            <v-col cols="12">
              <span class="caption pt-2">{{ i18n.potentialViolationsCategories_ }}</span>
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

          <v-row v-if="extraFilters">
            <v-col cols="12">
              <span class="caption pt-2">{{ i18n.claimedViolationsCategories_ }}</span>
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
                    query-params="&typ=for_indident&mode=2"
                    item-text="title"
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
                  query-params="&typ=for_indident"
                  item-text="title"
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
                    v-model="q.locations"
                    api="/admin/api/locations/"
                    item-text="full_string"
                    item-value="id"
                    :multiple="true"
                    :label="i18n.includeLocations_"
                ></search-field>
                <v-checkbox :label="i18n.any_" dense v-model="q.oplocations" color="primary" small
                            class="mx-3"></v-checkbox>
              </div>
              <search-field
                  v-model="q.exlocations"
                  api="/admin/api/locations/"
                  item-text="full_string"
                  item-value="id"
                  :multiple="true"
                  :label="i18n.excludeLocations_"
              ></search-field>


            </v-col>
          </v-row>


        </v-container>


      </v-card>
      

      </v-sheet>
    `

})