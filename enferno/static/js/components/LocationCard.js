const LocationCard = Vue.defineComponent({
  props: ['location', 'close', 'thumb-click', 'active', 'log', 'diff', 'showEdit'],

  data: function () {
    return {
      translations: window.translations,
      diffResult: '',
      diffDialog: false,
      revisions: null,
      show: false,
      hloading: false,
      mapLocations: [],
      localDiff: this.diff, // Create a local data property to hold the diff value
    };
  },

  watch: {
    location: function (val, old) {
      if (!this.$root.currentUser.view_simple_history) {
        this.log = false;
      }
      if (this.$root.currentUser.view_full_history) {
        this.localDiff = true; // Update the local data property instead of the prop
      }
      if (this.location.latlng) {
        let loc = {
          parentId: null,
          color: '#00a1f1',
          full_string: this.location.full_string,
          id: this.location.id,
          lat: this.location.latlng.lat,
          lng: this.location.latlng.lng,
          title: this.location.title,
        };
        this.mapLocations = this.mapLocations.concat(loc);
      }
    },
  },

  mounted() {},

  methods: {
    formatDate: formatDate,
    editAllowed() {
      return this.$root.editAllowed(this.location) && this.showEdit;
    },

    loadRevisions() {
      this.hloading = true;
      axios
        .get(`/admin/api/locationhistory/${this.location.id}`)
        .then((response) => {
          this.revisions = response.data.items;
        })
        .catch((error) => {
          if (error.response) {
            console.log(error.response.data);
          }
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

  template: `
    <v-card>
      <v-toolbar>
        <v-toolbar-title class="d-flex">
          <v-chip size="small">
            {{ translations.id_ }} {{ location.id }}
          </v-chip>

          <v-btn prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2" @click="$emit('edit', location)" small
                 >
            {{ translations.edit_ }}
          </v-btn>


          
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)"></v-btn>
            
        </template>

      </v-toolbar>
      <!-- Title -->
      <uni-field :caption="translations.title_" :english="location.full_string"></uni-field>
      <!-- Parent -->
      <v-card v-if="location.parent"  class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1"
              color="grey lighten-5">
        <div>{{ translations.parent_ }}</div>
        <v-chip  >{{ translations.id_ }}{{ location.parent.id }}
        </v-chip>
        <div></div>
        <div>{{ location.parent.full_string }}</div>
      </v-card>
      <!-- Postal Code -->
      <uni-field v-if="location.postal_code" :caption="translations.postalCode_" :english="location.postal_code"></uni-field>
      <!-- Meta -->
      <v-card variant="flat"  class="ma-2 pa-2">
        <v-chip    v-if="location.location_type">
          {{ translations.location_type_ }} {{ location.location_type.title }}
        </v-chip>
        <v-chip    v-if="location.admin_level">
          {{ translations.admin_level_ }} {{ location.admin_level.title }}
        </v-chip>
        <v-chip  v-if="location.country">
          {{ translations.country_ }} {{ location.country.title }}
        </v-chip>
      </v-card>
      <!-- Refs -->
      <v-card :subtitle="translations.tags_" v-if="location?.tags?.length" variant="flat" class="mx-2 my-1 pa-2 d-flex align-center">
        <div class="flex-chips">
          <v-chip size="x-small" class="flex-chip" v-for="e in location.tags" >{{ e }}</v-chip>
        </div>
      </v-card>
      <!-- Map -->
      <v-card variant="flat" class="my-2" >
        <global-map :edit-mode="false"  :model-value="mapLocations" :legend="false"></global-map>
      </v-card>
      <!-- Description -->
      <v-card variant="flat"  v-if="location.description" class="my-2 px-4">
        <div>{{ translations.location_ }}</div>
        <div class="rich-description" v-html="location.description"></div>
      </v-card>
      <!-- Log -->
      <v-card v-if="log" outline elevation="0" class="ma-2">
        <v-card-text>
          <h3 class="title black--text align-content-center">{{ translations.logHistory_ }}
            <v-btn icon="mdi-history" class="ml-1" variant="flat" size="small" :loading="hloading" @click="loadRevisions">
              
            </v-btn>
          </h3>
          <template v-for="(revision,index) in revisions">
            <v-card  dense flat class="my-1 pa-3 d-flex align-center">
              <span class="caption"> {{ formatDate(revision.created_at, { forceZ: true }) }} - {{ translations.by_ }} {{ revision.user.username }}</span>
              <v-spacer></v-spacer>
              <v-btn v-if="localDiff" v-show="index!=revisions.length-1" @click="showDiff($event,index)"
                     class="mx-1"
                     variant="flat"
                     size="small"
                     icon="mdi-vector-difference-ab"
                     >
                
              </v-btn>
            </v-card>
          </template>
        </v-card-text>
      </v-card>
      <v-dialog v-model="diffDialog" class="log-dialog">
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
