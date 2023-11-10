Vue.component("location-card", {
    props: ["location", "close", "thumb-click", "active", "log", "diff", "showEdit", "i18n"],

    watch: {
        location: function (val, old) {

          if (!this.$root.currentUser.view_simple_history) {
              this.log = false;
          }
          if (this.$root.currentUser.view_full_history) {
              this.diff = true;
          }
          if (this.location.latlng){
            let loc = {
              parentId: null,
              color: "#00a1f1",
              full_string: this.location.full_string,
              id: this.location.id,
              lat: this.location.latlng.lat,
              lng: this.location.latlng.lng,
              title: this.location.title
            };
          this.mapLocations = this.mapLocations.concat(loc);
          }
        },
    },

    mounted() {
      
    },

    methods: {

        editAllowed() {
            return this.$root.editAllowed(this.location) && this.showEdit;
        },

        loadRevisions() {
            this.hloading = true;
            axios
                .get(`/admin/api/locationhistory/${this.location.id}`)
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
            mapLocations: []
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
          {{ i18n.id_ }} {{ location.id }}
        </v-chip>
        <v-btn v-if="editAllowed()" class="ml-2" @click="$emit('edit', location)" small outlined><v-icon color="primary" left>mdi-pencil</v-icon> {{ i18n.edit_ }}
        </v-btn>
      </v-card-text>

        </v-card>

      <!-- Title -->
      <uni-field :caption="i18n.title_" :english="location.full_string" ></uni-field>
      
      <!-- Parent -->
      <v-card v-if="location.parent" outlined class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1" color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ i18n.parent_ }}</div>
        <v-chip pill x-small label color="gv darken-2" class="white--text">{{ i18n.id_ }} {{location.parent.id }}</v-chip>
        <div></div>
        <div class="pl-2 caption black--text">{{location.parent.full_string}}</div>
      </v-card>

      <!-- Postal Code -->
      <uni-field v-if="location.postal_code" :caption="i18n.postalCode_" :english="location.postal_code" ></uni-field>

      <!-- Meta -->
      <v-card outlined class="ma-2 pa-2" color="grey lighten-5">
        <v-chip pill small label color="gv darken-1" class="white--text" v-if="location.location_type">
          {{ i18n.location_type_ }} {{ location.location_type.title }}
        </v-chip>
        <v-chip pill small label color="gv darken-1" class="white--text" v-if="location.admin_level">
          {{ i18n.admin_level_ }} {{ location.admin_level.title }}
        </v-chip>
        <v-chip pill small label color="gv darken-3" class="white--text" v-if="location.country">
          {{ i18n.country_ }} {{ location.country.title }}
        </v-chip>
      </v-card>

      <!-- Refs -->
      <v-card v-if="location.tags && location.tags.length" outlined class="ma-2 pa-2 d-flex align-center flex-grow-1" color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ i18n.ref_ }}</div>
        <v-chip-group column>
          <v-chip x-small color="gv darken-1" v-for="e in location.tags" class="white--text">{{ e }}</v-chip>
        </v-chip-group>
      </v-card>

      <!-- Map -->
      <v-card outlined class="ma-2 pa-2" color="grey lighten-5">
        <geo-map :edit-mode="false" :i18n="i18n" :value="location.latlng"  :legend="false"></geo-map>
      </v-card>

      <!-- Description -->
      <v-card outlined v-if="location.description" class="ma-2 pa-2" color="grey lighten-5">
        <div class="caption grey--text mb-2">{{ i18n.location_ }}</div>
        <div class="rich-description" v-html="location.description"></div>
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
              <span class="caption"> {{ revision.created_at }} - By {{ revision.user.username }}</span>
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
          class="log-dialog"
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
