const ActorCard = Vue.defineComponent({
  props: ['actor', 'close', 'thumb-click', 'active', 'log', 'diff', 'showEdit'],
  emits: ['edit', 'close'],

  mounted() {
    this.fetchData();
  },

  methods: {
    fetchData() {
      this.mapLocations = aggregateActorLocations(this.actor);
    },

    updateMediaState() {
      this.mediasReady += 1;
      if (this.mediasReady == this.actor.medias.length && this.mediasReady > 0) {
        this.prepareImagesForPhotoswipe().then((res) => {
          this.initLightbox();
        });
      }
    },

    prepareImagesForPhotoswipe() {
      // Get the <a> tags from the image gallery
      const imagesList = document.querySelectorAll('#lightbox a');
      const promisesList = [];

      imagesList.forEach((element) => {
        const promise = new Promise(function (resolve) {
          let image = new Image();
          image.src = element.getAttribute('href');
          image.onload = () => {
            element.dataset.pswpWidth = image.width;
            element.dataset.pswpHeight = image.height;
            resolve(); // Resolve the promise only if the image has been loaded
          };
          image.onerror = () => {
            resolve();
          };
        });
        promisesList.push(promise);
      });

      // Use .then() to handle the promise resolution
      return Promise.all(promisesList);
    },

    initLightbox() {
      this.lightbox = new PhotoSwipeLightbox({
        gallery: '#lightbox',
        children: 'a',
        pswpModule: PhotoSwipe,
        wheelToZoom: true,
        arrowKeys: true,
      });

      this.lightbox.init();
    },

    getRelatedValues(item, actor) {
      const titleType = actor.id < item.actor.id ? 'title' : 'reverse_title';
      return extractValuesById(this.$root.atoaInfo, [item.related_as], titleType);
    },

    translate_status(status) {
      return translate_status(status);
    },

    logAllowed() {
      return this.$root.currentUser.view_simple_history && this.log;
    },

    diffAllowed() {
      return this.$root.currentUser.view_full_history && this.diff;
    },

    editAllowed() {
      if (typeof this.$root.editAllowed === 'function') {
        return this.$root.editAllowed(this.actor) && this.showEdit;
      }
      return false;
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

    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/actorhistory/${this.actor.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          console.error(error.body.data);
        })
        .finally(() => {
          this.hloading = false;
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
      lightbox: null,
      mediasReady: 0,
    };
  },

  template: `

      <v-card class="rounded-0">
        <v-card variant="flat" class=" mb-4 rounded-0">
          <v-toolbar class="d-flex px-2 ga-2">
            <v-chip size="small">
              {{ translations.id_ }} {{ actor.id }}
            </v-chip>

            <v-tooltip v-if="actor.originid" location="bottom">
                <template v-slot:activator="{ props }">
                    <v-chip 
                        v-bind="props"
                        prepend-icon="mdi-identifier" 
                        :href="actor.source_link" 
                        target="_blank" 
                        label
                        append-icon="mdi-open-in-new"
                        class="ml-1">
                        {{ actor.originid }}

                    </v-chip>
                </template>
                {{ translations.originid_ }}
            </v-tooltip>

            <v-btn variant="tonal" size="small" prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2"
                  @click="$emit('edit',actor)">
              {{ translations.edit_ }}
            </v-btn>

            <v-btn size="small" class="ml-2" variant="tonal" prepend-icon="mdi-graph-outline"
                  @click.stop="$root.$refs.viz.visualize(actor)">
              {{ translations.visualize_ }}
            </v-btn>

            <template #append>
              <v-btn variant="text" icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)">
            </v-btn>
            </template>
            
          </v-toolbar>

          <v-sheet v-if="actor.assigned_to || actor.status" variant="flat" class="d-flex pa-0   ga-2">
            <div class="pa-2" v-if="actor.assigned_to">
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-chip 
                      
                      variant="text"
                    v-bind="props"
                    prepend-icon="mdi-account-circle-outline">
                    {{ actor.assigned_to['name'] }}
                  </v-chip>
                </template>
                {{ translations.assignedUser_ }}
              </v-tooltip>
            </div>

            <v-divider v-if="actor.assigned_to" vertical ></v-divider>
            
            <div class="pa-2" v-if="actor.status">
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-chip 
                      variant="text"
                    v-bind="props"
                    prepend-icon="mdi-delta" class="mx-1">
                    {{ actor.status }}
                  </v-chip>
                </template>
                {{ translations.workflowStatus_ }}
              </v-tooltip>
            </div>
          </v-sheet> 

          <v-divider></v-divider>
          <v-card v-if="actor.roles?.length" variant="flat" class="ma-2 d-flex align-center pa-2 flex-grow-1">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-icon color="blue-darken-3" class="mx-2" size="small" v-bind="props">mdi-lock</v-icon>
              </template>
              {{ translations.accessRoles_ }}
            </v-tooltip>
            <v-chip label small v-for="role in actor.roles" :color="role.color" class="mx-1">{{ role.name }}</v-chip>
          </v-card>  
          <v-divider v-if="actor.roles?.length" ></v-divider>
      
          <v-card v-if="actor.source_link && actor.source_link !='NA'" variant="flat" class=" pa-2 ma-1 d-flex align-center flex-grow-1">
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-chip 
                    
                  v-bind="props"
                  prepend-icon="mdi-link-variant"
                  :href="actor.source_link" 
                  target="_blank" 
                  variant="text"
                  append-icon="mdi-open-in-new"
                  label
                  class="white--text ml-1">
                  {{ actor.source_link }}
                  
                </v-chip>
              </template>
              {{ translations.sourceLink_ }}: {{ actor.source_link }}
            </v-tooltip>
          </v-card> 
          <v-divider v-if="actor.source_link" ></v-divider>
        </v-card>

        <v-sheet class="pa-3 text-center">
          <h2 class="text-subtitle-2">{{ actor.name }} {{ actor.name_ar }}</h2>
        </v-sheet>

        <v-divider class="my-3"></v-divider>


        <uni-field :caption="translations.nickName_" :english="actor.nickname" :arabic="actor.nickname_ar"></uni-field>

        <div class="d-flex">
          <uni-field :caption="translations.firstName_" :english="actor.first_name" :arabic="actor.first_name_ar"></uni-field>
          <uni-field :caption="translations.middleName_" :english="actor.middle_name"
                     :arabic="actor.middle_name_ar"></uni-field>
        </div>

        <uni-field :caption="translations.lastName_" :english="actor.last_name" :arabic="actor.last_name_ar"></uni-field>
        <div class="d-flex">
          <uni-field :caption="translations.fathersName_" :english="actor.father_name"
                     :arabic="actor.father_name_ar"></uni-field>
          <uni-field :caption="translations.mothersName_" :english="actor.mother_name"
                     :arabic="actor.mother_name_ar"></uni-field>
        </div>

        <div class="d-flex">
          <uni-field :caption="translations.sex_" :english="actor._sex"></uni-field>
          <uni-field :caption="translations.age_" :english="actor._age"></uni-field>
          <uni-field :caption="translations.civilian_" :english="actor._civilian"></uni-field>
        </div>

        <uni-field :caption="translations.originPlace_" v-if="actor.origin_place"
                   :english="actor.origin_place.full_string"></uni-field>

        <div class="d-flex">
          <uni-field :caption="translations.familyStatus_" :english="actor.family_status"></uni-field>
        </div>

        <div class="d-flex">
          <uni-field :caption="translations.occupation_" :english="actor.occupation" :arabic="actor.occupation_ar"></uni-field>
          <uni-field :caption="translations.position_" :english="actor.position" :arabic="actor.position_ar"></uni-field>
        </div>

        <v-card v-if="actor.dialects?.length" outlined
                class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey ">
          <div class="caption grey--text mr-2">{{ translations.spokenDialects_ }}</div>
          <v-chip size="small" v-for="e in actor.dialects" color="blue-grey" class="caption black--text mx-1">{{ e.title }}
          </v-chip>

        </v-card>

        <v-card :subtitle=" translations.ethnographicInfo_" variant="flat" v-if="actor.ethnographies?.length" 
                class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey ">
          <div class="caption grey--text mr-2"></div>
          <v-chip size="small" v-for="e in actor.ethnographies" color="blue-grey" class="caption black--text mx-1">
            {{ e.title }}
          </v-chip>

        </v-card>
        <v-card variant="flat"  :subtitle="translations.nationalities_" v-if="actor.nationalities?.length" 
                class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey ">
          
          <v-chip size="small" v-for="n in actor.nationalities" color="blue-grey" class="caption black--text mx-1">
            {{ n.title }}
          </v-chip>

        </v-card>

        <uni-field :caption="translations.idNumber_" :english="actor.id_number"></uni-field>

        <!-- profiles -->
        <actor-profiles v-if="actor.id" :actor-id="actor.id"></actor-profiles>

        <!-- Map -->
        <v-card outlined class="ma-2 pa-2" color="grey">
          <global-map :model-value="mapLocations"></global-map>
        </v-card>


        <v-card  outlined class="rounded-0 mt-4" variant="text" v-if="actor.events?.length">
          <v-toolbar density="compact" >
            <v-toolbar-title  class="text-subtitle-1">{{ translations.events_ }}</v-toolbar-title>
          </v-toolbar>
          <v-card-text>
            <div class="px-1">{{ translations.events_ }}</div>
            <event-card v-for="event in actor.events" :key="event.id" :event="event"></event-card>
          </v-card-text>
        </v-card>


        <!-- Media -->

        <v-card class="ma-2" v-if="actor.medias && actor.medias.length">
          <v-toolbar density="compact">
              <v-toolbar-title class="text-subtitle-1">{{ translations.media_ }}</v-toolbar-title>
          </v-toolbar>

          <v-card variant="flat" v-if="iplayer" id="iplayer" class="px-2 my-3">
            <video :id="'player'+ $.uid" controls class="video-js vjs-default-skin vjs-big-play-centered "
                  crossorigin="anonymous"
                  height="360" preload="auto"></video>
          </v-card>
          
          <v-card-text>
            <image-gallery :medias="actor.medias" @thumb-click="viewThumb" @video-click="viewVideo"></image-gallery>
          </v-card-text>
        </v-card>

        <!-- Related Bulletins -->
        <related-bulletins-card v-if="actor" :entity="actor"
                                :relationInfo="$root.atobInfo"></related-bulletins-card>

        <!-- Related Actors  -->
        <related-actors-card v-if="actor" :entity="actor"
                             :relationInfo="$root.atoaInfo"></related-actors-card>

        <!-- Related Incidents -->
        <related-incidents-card v-if="actor" :entity="actor"
                                :relationInfo="$root.itoaInfo"></related-incidents-card>

        <div class="d-flex">
          <uni-field :caption="translations.publishDate_" :english="actor.publish_date"></uni-field>
          <uni-field :caption="translations.documentationDate_" :english="actor.documentation_date"></uni-field>
        </div>
        <uni-field :caption="translations.sourceLink_" :english="actor.source_link"></uni-field>


        <v-card v-if="actor.status==='Peer Reviewed'" variant="outlined" elevation="0" class="ma-2" color="teal-lighten-2">
          <v-card-text>
            <div class="px-1 title black--text">{{ translations.review_ }}</div>
            <div v-html="actor.review" class="pa-1 my-2  ">

            </div>
            <v-chip small label color="lime">{{ actor.review_action }}</v-chip>
          </v-card-text>
        </v-card>

        <!-- Log -->
        <v-card v-if="logAllowed()" outline elevation="0" class="ma-2">
          <v-card-text>
            <h3 class="title black--text align-content-center">{{ translations.logHistory_ }}
              <v-btn fab :loading="hloading" @click="loadRevisions" small class="elevation-0 align-content-center">
                <v-icon>mdi-history</v-icon>
              </v-btn>
            </h3>

            <template v-for="(revision,index) in revisions">
              <v-card color="grey" dense flat class="my-1 pa-2 d-flex align-center">
              <span class="caption">{{ revision.data['comments'] }} - <v-chip size="small" label
                                                                              color="gv">{{ translate_status(revision.data.status) }}</v-chip> -
                {{ revision.created_at }}
                - {{ translations.by_ }} {{ revision.user.username }}</span>
                <v-spacer></v-spacer>

                <v-btn v-if="diffAllowed()" v-show="index!==revisions.length-1" @click="showDiff($event,index)"
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


        <!-- Root Card   -->
      </v-card>
    `,
});
