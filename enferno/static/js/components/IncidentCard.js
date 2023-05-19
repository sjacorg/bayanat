Vue.component("incident-card", {
    props: ['incident', 'close', 'log', 'diff', "showEdit", "i18n"],
    watch: {


        incident: function (b, n) {

            if (!this.$root.currentUser.view_simple_history) {
                this.log = false;
            }
            if (this.$root.currentUser.view_full_history) {
                this.diff = true;
            }

            this.loadBulletinRelations();
            this.loadActorRelations();
            this.loadIncidentRelations();


        }
    },

    methods: {

            loadGeoMap(){

                this.geoMapLoading = true
                //load again all bulletin relations without paging (soft limit is 1000 bulletin)

                 axios.get(`/admin/api/incident/relations/${this.incident.id}?class=bulletin&page=1&per_page=1000`).then(res => {
                    // Check if there are related bulletins / then fetch their full data to visualize location
                     let relatedBulletins = res.data.items;
                if (relatedBulletins && relatedBulletins.length) {
                    getBulletinLocations(relatedBulletins.map(x => x.bulletin.id)).then(res => {
                        this.mapLocations = aggregateIncidentLocations(this.incident).concat(res.flat());
                        this.geoMapLoading = false;
                        this.geoMapOn = true;
                    })
                } else {
                    this.mapLocations = aggregateIncidentLocations(this.incident);
                    this.geoMapOn = true;
                }

            }).catch(err => {

                console.log(err.toJSON());
            });





        },

         translate_status(status){
          return translate_status(status);
        },

          loadBulletinRelations(page=1) {


            axios.get(`/admin/api/incident/relations/${this.incident.id}?class=bulletin&page=${page}`).then(res => {

                this.incident.bulletin_relations.push.apply(this.incident.bulletin_relations, res.data.items);
                this.bulletinPage += 1;
                this.bulletinLM = res.data.more;
            }).catch(err => {
                console.log(err.toJSON());
            });

        },

        loadActorRelations(page = 1){


            axios.get(`/admin/api/incident/relations/${this.incident.id}?class=actor&page=${page}`).then(res=>{
            //console.log(this.bulletin.actor_relations, res.data.items);
            this.incident.actor_relations.push.apply(this.incident.actor_relations,res.data.items);
            this.actorPage +=1;
            this.actorLM = res.data.more;

            }).catch(err=>{
                console.log(err.toJSON());
            });



        },
        loadIncidentRelations(page =1){

             // b2i
            axios.get(`/admin/api/incident/relations/${this.incident.id}?class=incident&page=${page}`).then(res=>{
            this.incident.incident_relations.push.apply(this.incident.incident_relations, res.data.items);
            this.incidentPage +=1;
            this.incidentLM = res.data.more;
            }).catch(err=>{
                console.log(err.toJSON());
            });

        },

        probability(item) {
            return translations.probs[item.probability].tr;
        },
        actor_related_as(item) {

            return translations.itoaRelateAs[item.related_as].tr;
        },

        bulletin_related_as(item) {

            return translations.itobRelateAs[item.related_as].tr;
        },

        incident_related_as(item) {

            return translations.itoiRelateAs[item.related_as].tr;
        },


        editAllowed() {
            return this.$root.editAllowed(this.incident) && this.showEdit;
        },


        loadRevisions() {
            this.hloading = true;
            axios.get(`/admin/api/incidenthistory/${this.incident.id}`).then(response => {
                this.revisions = response.data.items;
            }).catch(error => {
                console.log(error.body.data)
            }).finally(() => {
                this.hloading = false;
            });
        },

        showDiff(e, index) {

            this.diffDialog = true;
            //calculate diff
            const dp = jsondiffpatch.create({
                arrays: {
                    detectMove: true
                },
                objectHash: function (obj, index) {
                    return obj.name || obj.id || obj._id || '$$index:' + index;
                }
            });

            const delta = dp.diff(this.revisions[index + 1].data, this.revisions[index].data);
            if (!delta) {
                this.diffResult = 'Both items are Identical :)';
            } else {
                this.diffResult = jsondiffpatch.formatters.html.format(delta)
            }

        }

    },

    data: function () {
        return {
            geoMapLoading: false,
            geoMapOn: false,
            diffResult: '',
            diffDialog: false,
            revisions: null,
            show: false,
            hloading: false,
            //global map
            mapLocations: [],

            // pagers for related entities
            bulletinPage: 1,
            actorPage: 1,
            incidentPage: 1,

            // load more buttons
            bulletinLM: false,
            actorLM: false,
            incidentLM:false
        }
    },


    template: `
      <v-card color="grey lighten-3" class="mx-auto pa-3">
      <v-sheet color="grey lighten-5" class="header-fixed mx-2">
      <v-btn v-if="close" @click="$emit('close',$event.target.value)" fab absolute top right x-small text
             class="mt-6">
        <v-icon>mdi-close</v-icon>
      </v-btn>
      <v-card-text class="d-flex align-center">
        <v-chip small pill label color="gv darken-2" class="white--text">
          {{ i18n.id_ }} {{ incident.id }}</v-chip>
        <v-btn v-if="editAllowed()" class="ml-2" @click="$emit('edit',incident)" small outlined><v-icon color="primary" left>mdi-pencil</v-icon> {{ i18n.edit_ }}</v-btn>
        <v-btn @click.stop="$root.$refs.viz.visualize(incident)" class="ml-2" outlined small elevation="0"><v-icon color="primary" left>mdi-graph-outline</v-icon> {{ i18n.visualize_ }}</v-btn>

      </v-card-text>
      
      <v-chip color="white lighten-3" small label class="pa-2 mx-2 my-2" v-if="incident.assigned_to" ><v-icon left>mdi-account-circle-outline</v-icon>
          {{ i18n.assignedUser_ }} {{incident.assigned_to['name']}}</v-chip>
        <v-chip color="white lighten-3" small label class="mx-2 my-2" v-if="incident.status" > <v-icon left>mdi-delta</v-icon> {{translate_status(incident.status) }}</v-chip>
        
      </v-sheet>
      
      <v-card v-if="incident.roles?.length" color="blue" class="ma-2 pa-2 d-flex align-center flex-grow-1" elevation="0">
          <v-icon content="Access Roles" v-tippy color="blue lighten-5">mdi-lock</v-icon>
        <v-chip label color="gray darken-3" small v-for="role in incident.roles" :color="role.color" class="caption mx-1">{{ role.name }}</v-chip>
          
        </v-card>
      
      
      <uni-field :caption="i18n.title_" :english="incident.title" :arabic="incident.title_ar"></uni-field>

      <v-card outlined v-if="incident.description" class="ma-2 pa-2" color="grey lighten-5">
        <div class="caption grey--text mb-2">{{ i18n.description_ }}</div>
        <div class="rich-description" v-html="incident.description"></div>
      </v-card>

      <!-- Map -->
      <v-card :loading="geoMapLoading" outlined class="ma-2 pa-2" color="grey lighten-5">
        <v-btn :loading="geoMapLoading" :disabled="geoMapOn" @click="loadGeoMap" block elevation="0" color="primary lighten-2"> <v-icon left>mdi-map</v-icon> Load Geo Map</v-btn>
        <v-card-text v-if="geoMapOn">
        <global-map :i18n="i18n" :value="mapLocations"></global-map>
          </v-card-text>
      </v-card>

      <v-card outlined class="ma-2" color="grey lighten-5"
              v-if="incident.potential_violations && incident.potential_violations.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.potentialViolationsCategories_ }}</div>
          <v-chip-group column>
            <v-chip small color="blue-grey lighten-5" v-for="item in incident.potential_violations"
                    :key="item.id">{{ item.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <v-card outlined class="ma-2" color="grey lighten-5"
              v-if="incident.claimed_violations && incident.claimed_violations.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.claimedViolationsCategories_ }}</div>
          <v-chip-group column>
            <v-chip small color="blue-grey lighten-5" v-for="item in incident.claimed_violations"
                    :key="item.id">{{ item.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>


      <v-card outlined class="ma-2" color="grey lighten-5" v-if="incident.labels && incident.labels.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.labels_ }}</div>
          <v-chip-group column>
            <v-chip small color="blue-grey lighten-5" v-for="label in incident.labels"
                    :key="label.id">{{ label.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <v-card outlined class="ma-2" color="grey lighten-5" v-if="incident.locations && incident.locations.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.locations_ }}</div>
          <v-chip-group column>
            <v-chip small color="blue-grey lighten-5" v-for="item in incident.locations"
                    :key="item.id">{{ item.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>


      <!-- Events -->
      <v-card outlined class="ma-2" color="grey lighten-5" v-if="incident.events && incident.events.length">
        <v-card-text class="pa-2">
          <div class="px-1 title black--text">{{ i18n.events_ }}</div>
          <event-card v-for="event in incident.events" :key="event.id" :event="event"></event-card>
        </v-card-text>
      </v-card>


      <v-card outlined color="grey lighten-5" class="ma-2" v-if="incident.incident_relations && incident.incident_relations.length">
        <v-card-text>
          <div  class="pa-2 title header-sticky black--text">{{ i18n.relatedIncidents_ }}
          <v-tooltip top>
              <template v-slot:activator="{on,attrs}">
                <a :href="'/admin/incidents/?reltoi='+incident.id" target="_self">
                  <v-icon v-on="on" small color="grey" class="mb-1">
                    mdi-image-filter-center-focus-strong
                  </v-icon>
                </a>
              </template>
              <span>Filter and display related items in main table</span>
            </v-tooltip>
          </div>
          <incident-result :i18n="i18n" class="mt-1" v-for="(item,index) in incident.incident_relations" :key="index"
                           :incident="item.incident">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">{{ i18n.relationshipInfo_ }}</div>
                <v-chip v-if="item.probability!=null" color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip v-if="item.related_as!=null" color="grey lighten-4" small label>{{ incident_related_as(item) }}</v-chip>
                <v-chip v-if="item.comment" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </incident-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto caption" small color="grey lighten-4" elevation="0" @click="loadIncidentRelations(incidentPage)" v-if="incidentLM">Load More <v-icon right>mdi-chevron-down</v-icon> </v-btn>
        </v-card-actions>
      </v-card>

      <v-card outlined color="grey lighten-5" class="ma-2" v-if="incident.bulletin_relations && incident.bulletin_relations.length">

        <v-card-text>
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedBulletins_ }}
          <v-tooltip top>
              <template v-slot:activator="{on,attrs}">
                <a :href="'/admin/bulletins/?reltoi='+incident.id" target="_self">
                  <v-icon v-on="on" small color="grey" class="mb-1">
                    mdi-image-filter-center-focus-strong
                  </v-icon>
                </a>
              </template>
              <span>Filter and display related items in main table</span>
            </v-tooltip>
          </div>
          <bulletin-result :i18n="i18n" class="mt-1" v-for="(item,index) in incident.bulletin_relations" :key="index"
                           :bulletin="item.bulletin">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">{{ i18n.relationshipInfo_ }}</div>
                <v-chip v-if="item.probability!=null" color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip v-if="item.related_as!=null" color="grey lighten-4" small label>{{ bulletin_related_as(item) }}</v-chip>

                <v-chip v-if="item.comment" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </bulletin-result>
        </v-card-text>
        
        <v-card-actions>
          <v-btn class="ma-auto caption" small color="grey lighten-4" elevation="0" @click="loadBulletinRelations(bulletinPage)" v-if="bulletinLM">Load More <v-icon right>mdi-chevron-down</v-icon> </v-btn>
        </v-card-actions>
      </v-card>

      
      <v-card outlined color="grey lighten-5" class="ma-2" v-if="incident.actor_relations && incident.actor_relations.length">
        <v-card-text>
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedActors_ }}
          <v-tooltip top>
              <template v-slot:activator="{on,attrs}">
                <a :href="'/admin/actors/?reltoi='+incident.id" target="_self">
                  <v-icon v-on="on" small color="grey" class="mb-1">
                    mdi-image-filter-center-focus-strong
                  </v-icon>
                </a>
              </template>
              <span>Filter and display related items in main table</span>
            </v-tooltip>
          </div>
          <actor-result :i18n="i18n" class="mt-1" v-for="(item,index) in incident.actor_relations" :key="index"
                        :actor="item.actor">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">{{ i18n.relationshipInfo_ }}</div>
                <v-chip v-if="item.probability!=null" color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip v-if="item.related_as!=null" color="grey lighten-4" small label>{{ actor_related_as(item) }}</v-chip>
                <v-chip v-if="item.comment" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </actor-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto caption" small color="grey lighten-4" elevation="0" @click="loadActorRelations(actorPage)" v-if="actorLM">Load More <v-icon right>mdi-chevron-down</v-icon> </v-btn>
        </v-card-actions>
      </v-card>

      <v-card v-if="incident.status==='Peer Reviewed'" outline elevation="0" class="ma-3" color="light-green lighten-5">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.review_ }}</div>
          <div v-html="incident.review" class="pa-1 my-2 grey--text text--darken-2">

          </div>
          <v-chip small label color="lime">{{ incident.review_action }}</v-chip>
        </v-card-text>
      </v-card>


      <v-card v-if="log" outline elevation="0" color="grey lighten-5" class="ma-2">
        <v-card-text>
          <h3 class="title black--text align-content-center">{{ i18n.logHistory_ }}
            <v-btn fab  :loading="hloading" @click="loadRevisions" small class="elevation-0 align-content-center">
              <v-icon>mdi-history</v-icon>
            </v-btn>
          </h3>

          <template v-for="(revision,index) in revisions">
            <v-card color="grey lighten-4" dense flat class="my-1 pa-2 d-flex align-center">
                            <span class="caption">{{ revision.data['comments'] }} - <v-chip x-small label
                                                                                            color="gv lighten-3">{{ translate_status(revision.data.status) }}</v-chip> - {{ revision.created_at }}
                              - By {{ revision.user.username }}</span>
              <v-spacer></v-spacer>

              <v-btn v-if="diff" v-show="index!==revisions.length-1" @click="showDiff($event,index)"
                     class="mx-1" color="grey" icon small>
                <v-icon>mdi-compare</v-icon>
              </v-btn>
          </v-card>
            

          </template>
        </v-card-text>

      </v-card>
      <v-dialog
          v-model="diffDialog"
          max-width="770px"
      >
        <v-card class="pa-5">
          <v-card-text>
            <div v-html="diffResult">

            </div>
          </v-card-text>
        </v-card>

      </v-dialog>


      <!-- Root Card   -->
      </v-card>
    `
});
  