const BulletinCard = Vue.defineComponent({
  props: ['bulletin', 'close', 'thumb-click', 'active', 'log', 'diff', 'showEdit'],
  emits: ['edit', 'close'],
  watch: {
    bulletin: function (val, old) {

        this.mapLocations = aggregateBulletinLocations(this.bulletin);
    },
  },

  mounted() {
    this.removeVideo();
    if (this.bulletin?.id) {
        this.mapLocations = aggregateBulletinLocations(this.bulletin);
    }
  },

  methods: {
    extractValuesById(dataList, idList, valueKey) {
      // handle null related_as case
      if (idList === null) {
        return [];
      }

      return dataList.filter((item) => idList.includes(item.id)).map((item) => item[valueKey]);
    },

    updateMediaState() {},

    prepareImagesForPhotoswipe() {},

    initLightbox() {},

    translate_status(status) {
      return translate_status(status);
    },

    showReview(bulletin) {
      return bulletin.status === 'Peer Reviewed' && bulletin.review;
    },

    logAllowed() {
      return this.$root.currentUser.view_simple_history && this.log;
    },

    diffAllowed() {
      return this.$root.currentUser.view_full_history && this.diff;
    },

    editAllowed() {
      if (typeof this.$root.editAllowed === 'function') {
        return this.$root.editAllowed(this.bulletin) && this.showEdit;
      }
      return false;

    },

    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/bulletinhistory/${this.bulletin.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          if (error.response) {
            console.log(error?.response?.data);
          }
        })
        .finally(() => {
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
      this.iplayer = true;
      //solve bug when the player div is not ready yet
      // wait for vue's next tick

      this.$nextTick(() => {
        const video = this.$el.querySelector('#iplayer video');

        videojs(
          video,
          {
            playbackRates: VIDEO_RATES,
            //resizeManager: false
            fluid: true,
          },
          function () {
            this.reset();
            this.src(s3url);
            this.load();
            this.play();
          },
        );
        video.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      });
    },

    showDiff(e, index) {
      this.diffDialog = true;
      //calculate diff
      const dp = jsondiffpatch.create({
        arrays: {
          detectMove: true,
        },
        objectHash: function (obj, index) {
          return obj.name || obj.id || obj._id || '$$index:' + index;
        },
      });

      const delta = dp.diff(this.revisions[index + 1].data, this.revisions[index].data);
      if (!delta) {
        this.diffResult = 'Both items are Identical :)';
      } else {
        this.diffResult = jsondiffpatch.formatters.html.format(delta);
      }
    },
  },

  data: function () {
    return {
      translations: window.translations,
      diffResult: '',
      diffDialog: false,
      revisions: null,
      show: false,
      hloading: false,
      mapLocations: [],
      iplayer: false,

      // image viewer
      lightbox: null,
      mediasReady: 0,
    };
  },

  template: `

    <v-card class="rounded-0">
      <v-card variant="flat" class=" mb-4 rounded-0">
        <v-toolbar class="d-flex px-2 ga-2">
          <v-chip size="small">
            {{ translations.id_ }} {{ bulletin.id }}
          </v-chip>

          <v-tooltip v-if="bulletin.originid" location="bottom">
              <template v-slot:activator="{ props }">
                  <v-chip 
                      v-bind="props"
                      prepend-icon="mdi-identifier" 
                      :href="bulletin.source_link" 
                      target="_blank" 
                      label
                      append-icon="mdi-open-in-new"
                      class="ml-1">
                      {{ bulletin.originid }}

                  </v-chip>
              </template>
              {{ translations.originid_ }}
          </v-tooltip>

          <v-btn variant="tonal" size="small" prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2"
                 @click="$emit('edit',bulletin)">
            {{ translations.edit_ }}
          </v-btn>

          <v-btn size="small" class="ml-2" variant="tonal" prepend-icon="mdi-graph-outline"
                 @click.stop="$root.$refs.viz.visualize(bulletin)">
            {{ translations.visualize_ }}
          </v-btn>

          <template #append>
            <v-btn variant="text" icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)">
          </v-btn>
          </template>
          
        </v-toolbar>

        <v-sheet v-if="bulletin.assigned_to || bulletin.status" variant="flat" class="d-flex pa-0   ga-2">
          <div class="pa-2" v-if="bulletin.assigned_to">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    
                    variant="text"
                  v-bind="props"
                  prepend-icon="mdi-account-circle-outline">
                  {{ bulletin.assigned_to['name'] }}
                </v-chip>
              </template>
              {{ translations.assignedUser_ }}
            </v-tooltip>
          </div>

          <v-divider v-if="bulletin.assigned_to" vertical ></v-divider>
          
          <div class="pa-2" v-if="bulletin.status">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    variant="text"
                  v-bind="props"
                  prepend-icon="mdi-delta" class="mx-1">
                  {{ bulletin.status }}
                </v-chip>
              </template>
              {{ translations.workflowStatus_ }}
            </v-tooltip>
          </div>
        </v-sheet> 

        <v-divider></v-divider>
        <v-card v-if="bulletin.roles?.length" variant="flat" class="ma-2 d-flex align-center pa-2 flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="blue-darken-3" class="mx-2" size="small" v-bind="props">mdi-lock</v-icon>
            </template>
            {{ translations.accessRoles_ }}
          </v-tooltip>
          <v-chip label small v-for="role in bulletin.roles" :color="role.color" class="mx-1">{{ role.name }}</v-chip>
        </v-card>  
        <v-divider v-if="bulletin.roles?.length" ></v-divider>
        
        <v-card v-if="bulletin.ref?.length" variant="flat" class="ma-2 pa-2 flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-icon color="primary" class="mx-2" size="small" v-bind="props">mdi-tag</v-icon>
            </template>
            {{ translations.ref_ }}
          </v-tooltip>
          <v-chip size="small" v-for="e in bulletin.ref" class="caption black--text mx-1 mb-1">{{ e }}</v-chip>
        </v-card>
        <v-divider v-if="bulletin.ref?.length" ></v-divider>
    
        <v-card v-if="bulletin.source_link && bulletin.source_link !='NA'" variant="flat" class=" pa-2 ma-1 d-flex align-center flex-grow-1">
          <v-tooltip location="bottom">
            <template v-slot:activator="{ props }">
              <v-chip 
                  
                v-bind="props"
                prepend-icon="mdi-link-variant"
                :href="bulletin.source_link" 
                target="_blank" 
                variant="text"
                append-icon="mdi-open-in-new"
                label
                class="white--text ml-1">
                {{ bulletin.source_link }}
                
              </v-chip>
            </template>
            {{ translations.sourceLink_ }}: {{ bulletin.source_link }}
          </v-tooltip>
        </v-card> 
        <v-divider v-if="bulletin.source_link" ></v-divider>
      </v-card>

      <!-- Titles -->
      <uni-field :caption="translations.originalTitle_" :english="bulletin.title" :arabic="bulletin.title_ar"></uni-field>
      <uni-field :caption="translations.title_" :english="bulletin.sjac_title" :arabic="bulletin.sjac_title_ar"></uni-field>

      <!-- Description -->
      <v-card v-if="bulletin.description" class="ma-2 mb-4">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.description_ }}</v-toolbar-title>
        </v-toolbar>

        <v-card-text class="text-body-2 " v-html="bulletin.description"></v-card-text>
      </v-card>


      <!-- Map -->
      <v-divider></v-divider>
      <v-card variant="flat" >
       
        <global-map v-model="mapLocations"></global-map>
      </v-card>


      <!-- Sources -->
      <v-card class="ma-2"  v-if="bulletin.sources && bulletin.sources.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.sources_ }}</v-toolbar-title>

        </v-toolbar>
        <v-card-text>

          <v-chip-group column>
            <v-chip small label color="blue-grey " v-for="source in bulletin.sources"
                    :key="source.id">{{ source.title }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Events -->
      <v-card class="ma-2" v-if="bulletin.events && bulletin.events.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.events_ }}</v-toolbar-title>
        </v-toolbar>

        <v-card-text class="pa-2">
          <event-card v-for="(event, index) in bulletin.events" :number="index+1" :key="event.id"
                      :event="event"></event-card>
        </v-card-text>
      </v-card>

      <!-- Labels -->

      <v-card class="ma-2" v-if="bulletin.labels && bulletin.labels.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.labels_ }}</v-toolbar-title>
        </v-toolbar>

        <v-card-text>

          <v-chip-group column>
            <v-chip label small color="blue-grey " v-for="label in bulletin.labels"
                    :key="label.id">{{ label.title }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Verified Labels -->

      <v-card class="ma-2" v-if="bulletin.verLabels && bulletin.verLabels.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.verifiedLabels_ }}</v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <v-chip-group column>
            <v-chip label small color="blue-grey " v-for="vlabel in bulletin.verLabels"
                    :key="vlabel.id">{{ vlabel.title }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>


      <!-- Media -->

      <v-card class="ma-2" v-if="bulletin.medias && bulletin.medias.length">
        <v-toolbar density="compact">
            <v-toolbar-title class="text-subtitle-1">{{ translations.media_ }}</v-toolbar-title>
        </v-toolbar>
        <v-card variant="flat"  v-if="iplayer" id="iplayer" class="px-2 my-3">
          <video :id="'player'+ $.uid" controls class="video-js vjs-default-skin vjs-big-play-centered "
                 crossorigin="anonymous"
                 height="360" preload="auto"></video>

        </v-card>
        
        <v-card-text>
          
          <image-gallery :medias="bulletin.medias" @thumb-click="viewThumb" @video-click="viewVideo"></image-gallery>
        </v-card-text>
      </v-card>

      <!-- Locations -->
      <v-card class="ma-2"  v-if="bulletin.locations && bulletin.locations.length">
        <v-toolbar density="compact">
          <v-toolbar-title class="text-subtitle-1">{{ translations.locations_ }}</v-toolbar-title>
        </v-toolbar>
        <v-card-text>
          <v-chip-group column>
            <v-chip label small color="blue-grey " v-for="location in bulletin.locations"
                    :key="location.id">
              {{ location.full_string }}
            </v-chip>
          </v-chip-group>
        </v-card-text>
      </v-card>

      <!-- Related Bulletins -->
      <related-bulletins-card v-if="bulletin" :entity="bulletin"
                            :relationInfo="$root.btobInfo"> </related-bulletins-card>
      
      <!-- Related Actors  -->
      <related-actors-card v-if="bulletin" :entity="bulletin" 
                           :relationInfo="$root.atobInfo" ></related-actors-card>

      <!-- Related Incidents -->
      <related-incidents-card v-if="bulletin" :entity="bulletin"
                                :relationInfo="$root.itobInfo"></related-incidents-card>

      <!-- Pub/Doc Dates -->
      <v-sheet class="d-flex">
        <uni-field :caption="translations.publishDate_" :english="bulletin.publish_date"></uni-field>
        <uni-field :caption="translations.documentationDate_" :english="bulletin.documentation_date"></uni-field>
      </v-sheet>

      <!-- Review -->
      <v-card v-if="showReview(bulletin)" variant="outlined" elevation="0" class="ma-3" color="teal-lighten-2">
        <v-card-text>
          <div class="px-1">{{ translations.review_ }}</div>
          <div v-html="bulletin.review" class="pa-1 my-2 grey--text text--darken-2">

          </div>
          <v-chip  color="primary">{{ bulletin.review_action }}</v-chip>
        </v-card-text>
      </v-card>

      <!-- Log -->
      <v-card v-if="logAllowed()" variant="flat">
        <v-toolbar density="compact">
          <v-toolbar-title>
          <v-btn variant="plain" class="text-subtitle-2" append-icon="mdi-history" :loading="hloading"
                 @click="loadRevisions">
            {{ translations.logHistory_ }}
            
          </v-btn>
            </v-toolbar-title>
        </v-toolbar>
        
        <v-card-text> 


          <template v-for="(revision,index) in revisions">
            <v-sheet class="my-1 pa-3  align-center d-flex">
              <span class="caption">{{ revision.data['comments'] }} - 
                <v-chip label size="small"
                >{{ translate_status(revision.data.status) }}</v-chip> -
                {{ revision.created_at }}
                - {{ translations.by_ }} {{ revision.user.username }}</span>
              <v-spacer></v-spacer>

              <v-btn icon="mdi-vector-difference" v-if="diffAllowed()" v-show="index!=revisions.length-1"
                     @click="showDiff($event,index)"
                     class="mx-1" variant="flat" size="small"
              >

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
