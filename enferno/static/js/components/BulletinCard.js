Vue.component("bulletin-card", {
    props: ["bulletin", "close", "thumb-click", "active", "log", "diff", "showEdit", "i18n"],

    watch: {
        bulletin: function (val, old) {



            if (!this.$root.currentUser.view_simple_history) {
                this.log = false;
            }
            if (this.$root.currentUser.view_full_history) {
                this.diff = true;
            }

            this.loadBulletinRelations();
            this.loadActorRelations();
            this.loadIncidentRelations();

            this.mapLocations = aggregateLocations(this.bulletin);

        },
    },

    mounted() {


        this.removeVideo();
        //this.mapLocations = this.$root.aggregateLocations(this.bulletin)

    },




    methods: {


        translate_status(status){
          return translate_status(status);
        },

           loadBulletinRelations(page=1) {

             // b2a
            axios.get(`/admin/api/bulletin/relations/${this.bulletin.id}?class=bulletin&page=${page}`).then(res=>{
            this.bulletin.bulletin_relations.push.apply(this.bulletin. bulletin_relations,res.data.items);
            this.bulletinPage +=1;
            this.bulletinLM = res.data.more;

            }).catch(err=>{
                console.log(err.toJSON());
            });

        },

        loadActorRelations(page = 1){

             // b2a
            axios.get(`/admin/api/bulletin/relations/${this.bulletin.id}?class=actor&page=${page}`).then(res=>{
            //console.log(this.bulletin.actor_relations, res.data.items);
            this.bulletin.actor_relations.push.apply(this.bulletin.actor_relations,res.data.items);
            this.actorPage +=1;
            this.actorLM = res.data.more;

            }).catch(err=>{
                console.log(err.toJSON());
            });



        },
        loadIncidentRelations(page =1){

             // b2i
            axios.get(`/admin/api/bulletin/relations/${this.bulletin.id}?class=incident&page=${page}`).then(res=>{
            this.bulletin.incident_relations.push.apply(this.bulletin.incident_relations, res.data.items);
            this.incidentPage +=1;
            this.incidentLM = res.data.more;
            }).catch(err=>{
                console.log(err.toJSON());
            });

        },


        loadRelations(){





        },
        probability(item) {

            return translations.probs[item.probability].tr
        },
        actor_related_as(id) {
            return translations.btoaRelateAs[id].tr;
        },
        bulletin_related_as(item) {

            return translations.btobRelateAs[item.related_as].tr;
        },
        incident_related_as(item) {


            return translations.itobRelateAs[item.related_as].tr;
        },


        showReview(bulletin) {

            return (bulletin.status == 'Peer Reviewed' && bulletin.review);

        },


        editAllowed() {
            return this.$root.editAllowed(this.bulletin) && this.showEdit;
        },


        loadRevisions() {
            this.hloading = true;
            axios
                .get(`/admin/api/bulletinhistory/${this.bulletin.id}`)
                .then((response) => {
                    this.revisions = response.data.items;
                }).catch(error => {
                  if(error.response){
                    console.log(error.response.data)
                  }
            }).finally(() => {
                this.hloading = false;
            });
        },

        removeVideo() {
            let video = this.$el.querySelector('#iplayer video');
            if (video) {
                video.remove();
            }

        },
        viewThumb(s3url) {
            
            this.$emit('thumb-click', s3url);
        },


        viewVideo(s3url) {
            this.iplayer = true
            //solve bug when the player div is not ready yet
            // wait for vue's next tick

            this.$nextTick(() => {

                const video = this.$el.querySelector('#iplayer video');

                videojs(video, {
                    playbackRates: VIDEO_RATES,
                    //resizeManager: false
                    fluid: true
                }, function () {

                    this.reset();
                    this.src(s3url);
                    this.load();
                    this.play();
                });

            })


        },

        showDiff(e, index) {
            this.diffDialog = true;
            //calculate diff
            const dp = jsondiffpatch.create({
                arrays: {
                    detectMove: true,
                },
                objectHash: function (obj, index) {
                    return obj.name || obj.id || obj._id || "$$index:" + index;
                },
            });

            const delta = dp.diff(
                this.revisions[index + 1].data,
                this.revisions[index].data
            );
            if (!delta) {
                this.diffResult = "Both items are Identical :)";
            } else {
                this.diffResult = jsondiffpatch.formatters.html.format(delta);
            }
        },
    },

    data: function () {
        return {
            diffResult: "",
            diffDialog: false,
            revisions: null,
            show: false,
            hloading: false,
            mapLocations: [],
            iplayer: false,

            // pagers for related entities
            bulletinPage: 1,
            actorPage: 1,
            incidentPage: 1,

            // load more buttons
            bulletinLM: false,
            actorLM: false,
            incidentLM:false
        };
    },

    template: `

      <v-card color="grey lighten-3" class="mx-auto pa-3">
        <v-card color="grey lighten-5" outlined class="header-fixed mx-2">
        <v-btn v-if="close" @click="$emit('close',$event.target.value)" fab absolute top right x-small text
             class="mt-6">
        <v-icon>mdi-close</v-icon>
      </v-btn>
      <v-card-text>
        <v-chip pill small label color="gv darken-2" class="white--text">
          {{ i18n.id_ }} {{ bulletin.id }}
        </v-chip>
        <v-chip :href="bulletin.source_link" target="_blank" small pill label color="lime darken-3 "
                class="white--text ml-1">
          # {{ bulletin.originid }}
        </v-chip>
        <v-btn v-if="editAllowed()" class="ml-2" @click="$emit('edit',bulletin)" small outlined><v-icon color="primary" left>mdi-pencil</v-icon> {{ i18n.edit_ }}
        </v-btn>
        
        <v-btn @click.stop="$root.$refs.viz.visualize(bulletin)" class="ml-2" outlined small elevation="0"><v-icon color="primary" left>mdi-graph-outline</v-icon> {{ i18n.visualize_ }}</v-btn>
      </v-card-text>


      <v-chip color="white lighten-3" small label class="pa-2 mx-2 my-2" v-if="bulletin.assigned_to">
        <v-icon left>mdi-account-circle-outline</v-icon>
        {{ i18n.assignedUser_ }} {{ bulletin.assigned_to['name'] }}
      </v-chip>
      <v-chip color="white lighten-3" small label class="mx-2 my-2" v-if="bulletin.status">
        <v-icon left>mdi-delta</v-icon>
        {{ translate_status(bulletin.status) }}
      </v-chip>
        </v-card>

      <!-- Refs -->
      <v-card v-if="bulletin.ref && bulletin.ref.length" outlined class="ma-2 pa-2 d-flex align-center flex-grow-1"
      color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ i18n.ref_ }}</div>
        <v-chip x-small v-for="e in bulletin.ref" class="caption black--text mx-1">{{ e }}</v-chip>

      </v-card>

      <!-- Roles -->
      <v-card v-if="bulletin.roles?.length" color="blue darken-1" class="ma-2 pa-2 d-flex align-center flex-grow-1" elevation="0">
        <v-icon content="Access Roles" v-tippy color="white">mdi-lock</v-icon>
      <v-chip label small v-for="role in bulletin.roles" :color="role.color" class="mx-1">{{ role.name}}</v-chip>
        
      </v-card>
      

      <!-- Titles -->
      <uni-field :caption="i18n.originalTitle_" :english="bulletin.title" :arabic="bulletin.title_ar"></uni-field>
      <uni-field :caption="i18n.title_" :english="bulletin.sjac_title" :arabic="bulletin.sjac_title_ar"></uni-field>

      <!-- Description -->
      <v-card outlined v-if="bulletin.description" class="ma-2 pa-2" color="grey lighten-5">
        <div class="caption grey--text mb-2">{{ i18n.description_ }}</div>
        <div class="rich-description" v-html="bulletin.description"></div>
      </v-card>
      
      
      

      <!-- Map -->
      <v-card outlined class="ma-2 pa-2" color="grey lighten-5">
        <global-map :i18n="i18n" :value="mapLocations"></global-map>
      </v-card>

      <!-- Sources -->
      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.sources && bulletin.sources.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.sources_ }}</div>
          <v-chip-group column>
            <v-chip small label color="blue-grey lighten-5" v-for="source in bulletin.sources"
                    :key="source.id">{{ source.title }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Events -->
      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.events && bulletin.events.length">
        <v-card-text class="pa-2">
          <div class="px-1 title black--text">{{ i18n.events_ }}</div>
          <event-card v-for="(event, index) in bulletin.events" :number="index+1" :key="event.id"
                      :event="event"></event-card>
        </v-card-text>
      </v-card>

      <!-- Labels -->

      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.labels && bulletin.labels.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.labels_ }}</div>
          <v-chip-group column>
            <v-chip label small color="blue-grey lighten-5" v-for="label in bulletin.labels"
                    :key="label.id">{{ label.title }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Verified Labels -->

      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.verLabels && bulletin.verLabels.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.verifiedLabels_ }}</div>
          <v-chip-group column>
            <v-chip label small color="blue-grey lighten-5" v-for="vlabel in bulletin.verLabels"
                    :key="vlabel.id">{{ vlabel.title }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>


      <!-- Media -->

      <v-card outlined color="grey lighten-5" class="ma-2" v-if="bulletin.medias && bulletin.medias.length">
        <v-card v-if="iplayer" elevation="0" id="iplayer" class="px-2 my-3">
          <video :id="'player'+_uid" controls class="video-js vjs-default-skin vjs-big-play-centered"
                 crossorigin="anonymous"
                 height="360" preload="auto"></video>

        </v-card>
        <v-card-text>
          <div class="pa-2 header-sticky mb-3 title black--text">{{ i18n.media_ }}</div>

          <div class="d-flex flex-wrap">
            <div class="pa-1" style="width: 50%" v-for="media in bulletin.medias" :key="media.id">

              <media-card v-if="media" @thumb-click="viewThumb" @video-click="viewVideo"
                          :media="media"></media-card>
            </div>
          </div>

        </v-card-text>
      </v-card>

      <!-- Locations -->
      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.locations && bulletin.locations.length">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.locations_ }}</div>
          <v-chip-group column>
            <v-chip label small color="blue-grey lighten-5" v-for="location in bulletin.locations"
                    :key="location.id">
              {{ location.full_string }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Related Bulletins -->

      <v-card outlined color="grey lighten-5" class="ma-2" v-if="bulletin.bulletin_relations && bulletin.bulletin_relations.length">
        <v-card-text>
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedBulletins_ }}
          <v-tooltip top>
              <template v-slot:activator="{on,attrs}">

                <a :href="'/admin/bulletins/?reltob='+bulletin.id" target="_self">
                  <v-icon v-on="on" small color="grey" class="mb-1">
                    mdi-image-filter-center-focus-strong
                  </v-icon>
                </a>
              </template>
              <span>Filter and display related items in main table</span>
            </v-tooltip>

          </div>
          <bulletin-result :i18n="i18n" class="mt-1" v-for="(item,index) in bulletin.bulletin_relations" :key="index"
                           :bulletin="item.bulletin">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">{{ i18n.relationshipInfo_ }}</div>
                <v-chip v-if="item.probability!== null" color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip v-if="item.related_as!== null" color="grey lighten-4" small label>{{ bulletin_related_as(item) }}
                </v-chip>
                <v-chip v-if="item.comment" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </bulletin-result>
        </v-card-text>
         <v-card-actions>
          <v-btn class="ma-auto caption" small color="grey lighten-4" elevation="0" @click="loadBulletinRelations(bulletinPage)" v-if="bulletinLM">Load More <v-icon right>mdi-chevron-down</v-icon> </v-btn>
        </v-card-actions>
      </v-card>

      <!-- Related Actors  -->
      <v-card outlined color="grey lighten-5" class="ma-2" v-if="bulletin.actor_relations && bulletin.actor_relations.length">
        <v-card-text>
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedActors_ }}
          <v-tooltip top>
              <template v-slot:activator="{on,attrs}">

                <a :href="'/admin/actors/?reltob='+bulletin.id" target="_self">
                  <v-icon v-on="on" small color="grey" class="mb-1">
                    mdi-image-filter-center-focus-strong
                  </v-icon>
                </a>
              </template>
              <span>Filter and display related items in main table</span>
            </v-tooltip>
          
          </div>
          <actor-result :i18n="i18n" class="mt-1" v-for="(item,index) in bulletin.actor_relations" :key="index"
                        :actor="item.actor">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">{{ i18n.relationshipInfo_ }}</div>
                <v-chip v-if="item.probability!== null" class="ma-1" color="grey lighten-4" small label>
                  {{ probability(item) }}
                </v-chip>
                <v-chip class="ma-1" v-for="r in item.related_as" color="grey lighten-4" small
                        label>{{ actor_related_as(r) }}
                </v-chip>
                <v-chip v-if="item.comment" class="ma-1" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </actor-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto caption" small color="grey lighten-4" elevation="0" @click="loadActorRelations(actorPage)" v-if="actorLM">Load More <v-icon right>mdi-chevron-down</v-icon> </v-btn>
        </v-card-actions>
      </v-card>

      <!-- Related Incidents -->
      <v-card outlined color="grey lighten-5" class="ma-2" v-if="bulletin.incident_relations && bulletin.incident_relations.length">
        <v-card-text>
          <div class="pa-2 header-sticky title black--text">{{ i18n.relatedIncidents_ }}
          <v-tooltip top>
              <template v-slot:activator="{on,attrs}">
                <a :href="'/admin/incidents/?reltob='+bulletin.id" target="_self">
                  <v-icon v-on="on" small color="grey" class="mb-1">
                    mdi-image-filter-center-focus-strong
                  </v-icon>
                </a>
              </template>
              <span>Filter and display related items in main table</span>
            </v-tooltip>
          
          </div>
          <incident-result :i18n="i18n"  class="mt-1" v-for="(item,index) in bulletin.incident_relations" :key="index"
                           :incident="item.incident">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">{{ i18n.relationshipInfo_ }}</div>
                <v-chip v-if="item.probability!== null" color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                
                <v-chip v-if="item.related_as!==null" color="grey lighten-4" small label>{{ incident_related_as(item) }}
                </v-chip>

                <v-chip v-if="item.comment" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </incident-result>
        </v-card-text>
        <v-card-actions>
          <v-btn class="ma-auto caption" small color="grey lighten-4" elevation="0" @click="loadIncidentRelations(incidentPage)" v-if="incidentLM">Load More <v-icon right>mdi-chevron-down</v-icon> </v-btn>
        </v-card-actions>
      </v-card>

      <!-- Pub/Doc Dates -->
      <div class="d-flex">
        <uni-field :caption="i18n.publishDate_" :english="bulletin.publish_date"></uni-field>
        <uni-field :caption="i18n.documentationDate_" :english="bulletin.documentation_date"></uni-field>
      </div>

      <uni-field :caption="i18n.sourceLink_" :english="bulletin.source_link"></uni-field>

      <!-- Review -->
      <v-card v-if="showReview(bulletin)" outline elevation="0" class="ma-3" color="light-green lighten-5">
        <v-card-text>
          <div class="px-1 title black--text">{{ i18n.review_ }}</div>
          <div v-html="bulletin.review" class="pa-1 my-2 grey--text text--darken-2">

          </div>
          <v-chip small label color="lime">{{ bulletin.review_action }}</v-chip>
        </v-card-text>
      </v-card>

      <!-- Log -->
      <v-card v-if="log" outline elevation="0" class="ma-2">
        <v-card-text>
          <h3 class="title black--text align-content-center">{{ i18n.logHistory_ }}
            <v-btn fab :loading="hloading" @click="loadRevisions" small class="elevation-0 align-content-center">
              <v-icon>mdi-history</v-icon>
            </v-btn>
          </h3>


          <template v-for="(revision,index) in revisions">
            <v-card color="grey lighten-4" dense flat class="my-1 pa-3 d-flex align-center">
              <span class="caption">{{ revision.data['comments'] }} - <v-chip x-small label
                                                                              color="gv lighten-3">{{ translate_status(revision.data.status) }}</v-chip> -
                {{ revision.created_at }}
                - By {{ revision.user.username }}</span>
              <v-spacer></v-spacer>

              <v-btn v-if="diff" v-show="index!=revisions.length-1" @click="showDiff($event,index)"
                     class="mx-1"
                     color="grey" icon small>
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
      <!-- Root card -->
      </v-card>


    `,
});
