Vue.component('incident-search-box', {
    props: {
        value: {
            type: Object, required: true
        }, users: {
            type: Array
        }, closeBtn: {
            type: String
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
            repr: '', q: {},


        }
    }, watch: {


        q: {
            handler(newVal) {

                this.$emit('input', newVal)
            }, deep: true
        }, value: function (newVal, oldVal) {


            if (newVal != oldVal) {
                this.q = newVal;
            }
        }

    }, created() {
        this.q = this.value;

    }, methods: {},

    template: `
<v-sheet>
    <v-card class="pa-4">
        <v-card-title>
            <v-spacer></v-spacer>
            <v-btn fab text @click="$emit('close')">
                <v-icon>mdi-close</v-icon>
            </v-btn>
        </v-card-title>

            


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
                
                
                <v-row v-if="isAdmin" > 
                    <v-col md="9">
                        <span class="caption">Access Roles</span>
                        <v-chip-group
                                column
                                multiple
                                v-model="q.roles">
                            <v-chip v-if="roles" :value="role.id" small v-for="role in roles" filter
                                    outlined>{{role.name}}</v-chip>
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
                            <v-chip :value="user.id" small label v-for="user in users" filter outlined>{{user.name}}</v-chip>
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
                            <v-chip label :value="user.id" small v-for="user in users" filter outlined>{{user.name}}</v-chip>
                        </v-chip-group>
                    </v-col>
                </v-row>


                <v-row v-if="extraFilters">
                    <v-col cols="12">
                        <span class="caption pt-2">{{ i18n.workflowStatus_ }}</span>


                        <v-chip-group
                                column
                                v-model="q.status"
                        >
                            <v-chip :value="status.en" label small v-for="status in translations.statuses_" :key="status.en"
                                    filter outlined>{{status.tr}}</v-chip>
                        </v-chip-group>

                    </v-col>
                </v-row>
              
              <v-row>
                  <v-col cols="12">
                    <span class="caption pt-2">{{ i18n.reviewAction_ }}</span>
                    <v-chip-group column v-model="q.reviewAction">
                      <v-chip value="No Review Needed" label small filter outlined >No Review Needed</v-chip>
                      <v-chip value="Needs Review" label small filter outlined>Needs Review</v-chip>
                      
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


                <v-row>
                    <v-col>
                        <search-field
                                v-model="q.elocation"
                                api="/admin/api/locations/"
                                item-text="full_string"
                                item-value="id"
                                :multiple="false"
                                :label="i18n.includeEventLocations_"
                        ></search-field>

                    </v-col>

                </v-row>


                <v-row>
                    <v-col cols="12" md="12">
                        <search-field
                                v-model="q.etype"
                                api="/admin/api/eventtypes/"
                                query-params="&typ=for_indident"
                                item-text="title"
                                item-value="id"
                                :multiple="false"
                                :label="i18n.eventType_"
                        ></search-field>

                    </v-col>

                </v-row>
                


            </v-container>
            
            

            
        </v-card>
        <v-card tile class="text-center  search-toolbar" elevation="10" color="grey lighten-5">
        <v-card-text> <v-spacer></v-spacer>
        <v-btn @click="q={}" text>{{ i18n.clearSearch_ }}</v-btn>

                <v-btn @click="$emit('search',q)" color="primary">{{ i18n.search_ }}</v-btn>
                 <v-spacer></v-spacer>
</v-card-text>
        
</v-card>
  
</v-sheet>
    `

})