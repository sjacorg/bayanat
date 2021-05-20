Vue.component("bulletin-card", {
    props: ["bulletin", "close", "thumb-click", "active", "log", "diff", "showEdit"],

    watch: {
        bulletin: function (val, old) {


            if (!this.$root.currentUser.view_simple_history) {
                this.log = false;
            }
            if (this.$root.currentUser.view_full_history) {
                this.diff = true;
            }

        },
    },

    mounted() {


        this.removeVideo();
    },


    methods: {
        probability(item) {
            return probs[item.probability]
        },
        actor_related_as(id) {
            return actorConfig.btoaRelateAs[id];
        },
        bulletin_related_as(item) {
            return btobRelateAs[item.related_as];
        },
        incident_related_as(item) {
            return itobRelateAs[item.related_as];
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
                }).catch(error=>{
              console.log(error.body.data)
            }).finally(()=>{
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
            console.log(s3url);
            this.$emit('thumb-click', s3url);
        },


        viewVideo(s3url) {

            this.removeVideo();

            let video = document.createElement('video');
            video.src = s3url;
            video.controls = true;
            video.autoplay = true;
            this.$el.querySelector('#iplayer').append(video);


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
        };
    },

    template: `

      <v-card color="grey lighten-3" class="mx-auto pa-3">
      <v-btn v-if="close" @click="$emit('close',$event.target.value)" fab absolute top right x-small text
             class="mt-6">
        <v-icon>mdi-close</v-icon>
      </v-btn>
      <v-card-text>
        <v-chip pill small label color="gv darken-2" class="white--text">
          ID {{ bulletin.id }}</v-chip>
        <v-chip :href="bulletin.source_link" target="_blank" small pill label color="lime darken-3 "
                class="white--text ml-1">
          # {{ bulletin.originid }}</v-chip>
        <v-btn v-if="editAllowed()" class="ml-2" @click="$emit('edit',bulletin)" x-small outlined>Edit</v-btn>

      </v-card-text>

      <v-sheet v-if="bulletin.ref && bulletin.ref.length" outlined class="ma-2 pa-2 d-flex align-center flex-grow-1"
               color="yellow lighten-5 ">
        <div class="caption grey--text mr-2">Ref</div>
        <v-chip x-small v-for="e in bulletin.ref" class="caption black--text mx-1">{{ e }}</v-chip>

      </v-sheet>

      <uni-field caption="Original Title" :english="bulletin.title" :arabic="bulletin.title_ar"></uni-field>
      <uni-field caption="Title" :english="bulletin.sjac_title" :arabic="bulletin.sjac_title_ar"></uni-field>

      <v-card outlined v-if="bulletin.description" class="ma-2 pa-2" color="grey lighten-5">
        <div class="caption grey--text mb-2">Description</div>
        <div class="rich-description" v-html="bulletin.description"></div>
      </v-card>


      <!-- Sources -->
      <v-card outlined class="ma-3" color="grey lighten-5" v-if="bulletin.sources && bulletin.sources.length">
        <v-card-text>
          <div class="px-1 title black--text">Sources</div>
          <v-chip-group column>
            <v-chip small label color="blue-grey lighten-5" v-for="source in bulletin.sources"
                    :key="source.id">{{ source.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Events -->
      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.events && bulletin.events.length">
        <v-card-text class="pa-2">
          <div class="px-1 title black--text">Events</div>
          <event-card v-for="event in bulletin.events" :key="event.id" :event="event"></event-card>
        </v-card-text>
      </v-card>

      <!-- Labels -->

      <v-card outlined class="ma-3" color="grey lighten-5" v-if="bulletin.labels && bulletin.labels.length">
        <v-card-text>
          <div class="px-1 title black--text">Labels</div>
          <v-chip-group column>
            <v-chip label small color="blue-grey lighten-5" v-for="label in bulletin.labels"
                    :key="label.id">{{ label.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Verified Labels -->

      <v-card outlined class="ma-3" color="grey lighten-5" v-if="bulletin.verLabels && bulletin.verLabels.length">
        <v-card-text>
          <div class="px-1 title black--text">Verified Labels</div>
          <v-chip-group column>
            <v-chip label small color="blue-grey lighten-5" v-for="vlabel in bulletin.verLabels"
                    :key="vlabel.id">{{ vlabel.title }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>


      <!-- Media -->

      <v-card outlined class="ma-3" v-if="bulletin.medias && bulletin.medias.length">
        <v-card outlined id="iplayer">

        </v-card>
        <v-card-text>
          <div class="px-1 mb-3 title black--text">Media</div>
          <v-layout wrap>
            <v-flex class="ma-2" md6 v-for="media in bulletin.medias" :key="media.id">

              <media-card v-if="media" @thumb-click="viewThumb" @video-click="viewVideo"
                          :media="media"></media-card>
            </v-flex>
          </v-layout>
        </v-card-text>
      </v-card>

      <!-- Locations -->
      <v-card outlined class="ma-2" color="grey lighten-5" v-if="bulletin.locations && bulletin.locations.length">
        <v-card-text>
          <div class="px-1 title black--text">Locations</div>
          <v-chip-group column>
            <v-chip label small color="blue-grey lighten-5" v-for="location in bulletin.locations"
                    :key="location.id">
              {{ location.full_string }}</v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Related Bulletins -->

      <v-card outlined class="ma-3" v-if="bulletin.bulletin_relations && bulletin.bulletin_relations.length">
        <v-card-text>
          <div class="px-1 title black--text">Related Bulletins</div>
          <bulletin-result class="mt-1" v-for="(item,index) in bulletin.bulletin_relations" :key="index"
                           :bulletin="item.bulletin">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">Relationship Info</div>
                <v-chip color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip color="grey lighten-4" small label>{{ bulletin_related_as(item) }}</v-chip>
                <v-chip color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </bulletin-result>
        </v-card-text>
      </v-card>

      <!-- Related Actors  -->
      <v-card outlined class="ma-3" v-if="bulletin.actor_relations && bulletin.actor_relations.length">
        <v-card-text>
          <div class="px-1 title black--text">Related Actors</div>
          <actor-result class="mt-1" v-for="(item,index) in bulletin.actor_relations" :key="index"
                        :actor="item.actor">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">Relationship Info</div>
                <v-chip class="ma-1" color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip class="ma-1" v-for="r in item.related_as" color="blue-grey lighten-4" small label>{{ actor_related_as(r) }}</v-chip>
                <v-chip class="ma-1" color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </actor-result>
        </v-card-text>
      </v-card>

      <!-- Related Incidents -->
      <v-card outlined class="ma-3" v-if="bulletin.incident_relations && bulletin.incident_relations.length">
        <v-card-text>
          <div class="px-1 title black--text">Related Incidents</div>
          <incident-result class="mt-1" v-for="(item,index) in bulletin.incident_relations" :key="index"
                           :incident="item.incident">
            <template v-slot:header>

              <v-sheet color="yellow lighten-5" class="pa-2">

                <div class="caption ma-2">Relationship Info</div>
                <v-chip color="grey lighten-4" small label>{{ probability(item) }}</v-chip>
                <v-chip color="grey lighten-4" small label>{{ incident_related_as(item) }}</v-chip>

                <v-chip color="grey lighten-4" small label>{{ item.comment }}</v-chip>

              </v-sheet>

            </template>
          </incident-result>
        </v-card-text>
      </v-card>

      <!-- Pub/Doc Dates -->
      <div class="d-flex">
        <uni-field caption="Publish Date" :english="bulletin.publish_date"></uni-field>
        <uni-field caption="Documentation Date" :english="bulletin.documentation_date"></uni-field>
      </div>

      <uni-field caption="Source Link" :english="bulletin.source_link"></uni-field>


      <v-card v-if="bulletin.status=='Peer Reviewed'" outline elevation="0" class="ma-3" color="light-green lighten-5">
        <v-card-text>
          <div class="px-1 title black--text">Review</div>
          <div v-html="bulletin.review" class="pa-1 my-2 grey--text text--darken-2">

          </div>
          <v-chip small label color="lime">{{ bulletin.review_action }}</v-chip>
        </v-card-text>
      </v-card>

      <v-card v-if="log" outline elevation="0" color="ma-3">
        <v-card-text>
          <h3 class="title black--text align-content-center" >Log History
          <v-btn fab small :loading="hloading" @click="loadRevisions" small class="elevation-0 align-content-center" >
              <v-icon  >mdi-history</v-icon>
          </v-btn>
          </h3>

          

            


            <template v-for="(revision,index) in revisions">
              <v-sheet color="grey lighten-4" dense flat class="my-1 pa-3 d-flex align-center">
              <span class="caption">{{ revision.data['comments'] }} - <v-chip x-small label
                                                                              color="gv lighten-3">{{ revision.data.status }}</v-chip> - {{ revision.created_at }}
                - By {{ revision.user.email }}</span>
                <v-spacer></v-spacer>

                <v-btn v-if="diff" v-show="index!=revisions.length-1" @click="showDiff($event,index)"
                       class="mx-1"
                       color="grey" icon small>
                  <v-icon>mdi-compare</v-icon>
                </v-btn>

              </v-sheet>

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
