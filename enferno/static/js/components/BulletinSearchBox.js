Vue.component('bulletin-search-box', {
    props: {
        value: {
            type: Object,
            required: true
        },
        users: {
            type: Array
        },

        extraFilters: {
            type: Boolean
        },
        showOp: {
            type: Boolean,
            default: true
        },
        i18n: {
            type: Object,
        }
    },

    data: () => {
        return {
            searches: [],
            saveDialog: false,
            repr: '',
            q: {},
            qName: '',


        }
    },
    created() {
        this.q = this.value;


    },
    watch: {


        q: {
            handler(newVal) {

                this.$emit('input', newVal)
            }
            ,
            deep: true
        },
        value: function (newVal, oldVal) {


            if (newVal != oldVal) {
                this.q = newVal;
            }
        }

    },
    methods: {


    },

    template: `
        <v-card flat>
            <v-card-text>
            <v-container class="fluid">
                <v-row v-if="showOp">
                    <v-col>
                        <v-btn-toggle mandatory v-model="q.op">
                            <v-btn small value="and">And</v-btn>
                            <v-btn small value="or">Or</v-btn>
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
                        <div class="d-flex">
                          <v-combobox
                                v-model="q.ref"
                                :label="i18n.inRef_"
                                multiple
                                deletable-chips
                                small-chips
                                clearable
                        ></v-combobox>
                        
                        <v-checkbox :label="i18n.any_" dense v-model="q.opref" color="primary" small
                                        class="mx-3"></v-checkbox>
                        
                        </div>
                        
                        <div class="d-flex">
                        
                        <v-combobox
                                v-model="q.exref"
                                :label="i18n.exRef_"
                                multiple
                                deletable-chips
                                small-chips
                                clearable
                        ></v-combobox>
                        
                        <v-checkbox :label="i18n.all_" dense v-model="q.opexref" color="primary" small
                                        class="mx-3"></v-checkbox>
                                        </div>
                        
                        
                    </v-col>
                </v-row>
                <v-row>
                    <v-col md="6">
                        <div class="d-flex flex-wrap">
                            <pop-date-field :label="i18n.publishDate_" v-model="q.pubdate"></pop-date-field>
                            <v-select
                                    dense
                                    v-model="q.pubdatewithin"
                                    :label="i18n.within_"
                                    :items="dateWithin"
                                    class="mx-2"
                            ></v-select>
                        </div>
                    </v-col>
            
                    <v-col md="6">
                        <div class="d-flex flex-wrap">
                            <pop-date-field :label="i18n.documentationDate_" v-model="q.docdate"></pop-date-field>
                            <v-select
                                    class="mx-2"
                                    dense

                                    v-model="q.docdatewithin"
                                    :label="i18n.within_"
                                    :items="dateWithin"

                            ></v-select>
                        </div>
                    </v-col>
                </v-row>
              
              <v-row>
                    <v-col md="6">
                        <div class="d-flex flex-wrap">
                            <pop-date-field :label="i18n.createdDate_" v-model="q.created"></pop-date-field>
                            <v-select
                                    dense
                                    v-model="q.createdwithin"
                                    :label="i18n.within_"
                                    :items="dateWithin"
                                    class="mx-2"
                            ></v-select>
                        </div>
                    </v-col>
            
                    <v-col md="6">
                        <div class="d-flex flex-wrap">
                            <pop-date-field :label="i18n.updatedDate_" v-model="q.updated"></pop-date-field>
                            <v-select
                                    class="mx-2"
                                    dense

                                    v-model="q.updatedwithin"
                                    :label="i18n.within_"
                                    :items="dateWithin"

                            ></v-select>
                        </div>
                    </v-col>
                </v-row>
              
              
              
              
                <v-row>
                    <v-col>
                        <div class="d-flex">
                            <pop-date-field :label="i18n.eventDate_" v-model="q.edate"></pop-date-field>
                            <v-select
                                    dense
                                    v-model="q.edatewithin"
                                    :label="i18n.within_"
                                    :items="dateWithin"
                                    class="mx-2"
                            ></v-select>
                        </div>
                    </v-col>
                </v-row>


                <v-row v-if="extraFilters">
                    
                    <v-col md="9">
                        <span class="caption">{{i18n.assignedUser_}}</span>


                        <v-chip-group
                                column
                                multiple
                                v-model="q.assigned"
                                
                        >
                            <v-chip :value="user.id" small label v-for="user in users" filter
                                    outlined>{{user.name}}</v-chip>
                        </v-chip-group>
                    </v-col>
                    <v-col md="3">
                        <span class="caption">{{ i18n.unassigned_ }}</span>
                        <v-switch v-model="q.unassigned"></v-switch>
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
                                    outlined>{{user.name}}</v-chip>
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
                            <v-chip :value="status" label small v-for="status in statuses" filter
                                    outlined>{{status}}</v-chip>
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

                                    v-model="q.sources"
                                    api="/admin/api/sources/"
                                    item-text="title"
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
                                item-text="title"
                                item-value="id"
                                :multiple="true"
                                :label="i18n.excludeSources_"

                        ></search-field>
                        
                        <v-switch  v-model="q.childsources" :label="i18n.includeChildSources_"></v-switch>


                    </v-col>
                </v-row>

                <v-row>
                    <v-col>
                        <div class="d-flex">
                            <search-field
                                    v-model="q.labels"
                                    api="/admin/api/labels/"
                                    query-params="&typ=for_bulletin&mode=2"
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
                                query-params="&typ=for_bulletin"
                                item-text="title"
                                item-value="id"
                                :multiple="true"
                                :label="i18n.excludeLabels_"
                        ></search-field>
                        
                        <v-switch v-model="q.childlabels" :label="i18n.includeChildLabels_"></v-switch>


                    </v-col>
                </v-row>
                <v-row>
                    <v-col>
                        <div class="d-flex">
                            <search-field
                                    v-model="q.vlabels"
                                    api="/admin/api/labels/"
                                    query-params="&fltr=verified&typ=for_bulletin"
                                    item-text="title"
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
                                query-params="&fltr=verified&typ=for_bulletin"
                                item-text="title"
                                item-value="id"
                                :multiple="true"
                                :label="i18n.excludeVerLabels_"
                        ></search-field>
                      
                      <v-switch v-model="q.childverlabels" :label="i18n.includeChildVerLabels_"></v-switch>
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
                                query-params="&typ=for_bulletin"
                                item-text="title"
                                item-value="id"
                                :multiple="false"
                                :label="i18n.eventType_"
                        ></search-field>

                    </v-col>

                </v-row>


            </v-container>
</v-card-text>
          
        </v-card>
        
        

    `

})