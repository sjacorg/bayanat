const LocationCard = Vue.defineComponent({
  props: ['location', 'close', 'thumb-click', 'active', 'log', 'diff', 'showEdit', 'i18n'],

  data: function () {
    return {
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
            {{ i18n.id_ }} {{ location.id }}
          </v-chip>

          <v-btn prepend-icon="mdi-pencil" v-if="editAllowed()" class="ml-2" @click="$emit('edit', location)" small
                 >
            {{ i18n.edit_ }}
          </v-btn>


          
        </v-toolbar-title>

        <template #append>
          <v-btn icon="mdi-close" v-if="close" @click="$emit('close',$event.target.value)"></v-btn>
            
        </template>

      </v-toolbar>
      <!-- Title -->
      <uni-field :caption="i18n.title_" :english="location.full_string"></uni-field>
      <!-- Parent -->
      <v-card v-if="location.parent"  class="mx-2 my-1 pa-2 d-flex align-center flex-grow-1"
              color="grey lighten-5">
        <div>{{ i18n.parent_ }}</div>
        <v-chip  >{{ i18n.id_ }}{{ location.parent.id }}
        </v-chip>
        <div></div>
        <div>{{ location.parent.full_string }}</div>
      </v-card>
      <!-- Postal Code -->
      <uni-field v-if="location.postal_code" :caption="i18n.postalCode_" :english="location.postal_code"></uni-field>
      <!-- Meta -->
      <v-card variant="flat"  class="ma-2 pa-2">
        <v-chip    v-if="location.location_type">
          {{ i18n.location_type_ }} {{ location.location_type.title }}
        </v-chip>
        <v-chip    v-if="location.admin_level">
          {{ i18n.admin_level_ }} {{ location.admin_level.title }}
        </v-chip>
        <v-chip  v-if="location.country">
          {{ i18n.country_ }} {{ location.country.title }}
        </v-chip>
      </v-card>
      <!-- Refs -->
      <v-card v-if="location.tags && location.tags.length"  class="ma-2 pa-2 d-flex align-center flex-grow-1"
              color="grey lighten-5">
        <div class="caption grey--text mr-2">{{ i18n.ref_ }}</div>
        <v-chip-group column>
          <v-chip x-small  v-for="e in location.tags" >{{ e }}</v-chip>
        </v-chip-group>
      </v-card>
      <!-- Map -->
      <v-card variant="flat" class="my-2" >
        <geo-map :edit-mode="false" :i18n="i18n" :value="location.latlng" :legend="false"></geo-map>
      </v-card>
      <!-- Description -->
      <v-card variant="flat"  v-if="location.description" class="my-2 px-4">
        <div>{{ i18n.location_ }}</div>
        <div class="rich-description" v-html="location.description"></div>
      </v-card>
      <!-- Log -->
      <v-card v-if="log" outline elevation="0" class="ma-2">
        <v-card-text>
          <h3 class="title black--text align-content-center">{{ i18n.logHistory_ }}
            <v-btn icon="mdi-history" class="ml-1" variant="flat" size="small" :loading="hloading" @click="loadRevisions">
              
            </v-btn>
          </h3>
          <template v-for="(revision,index) in revisions">
            <v-card  dense flat class="my-1 pa-3 d-flex align-center">
              <span class="caption"> {{ revision.created_at }} - {{ i18n.by_ }} {{ revision.user.username }}</span>
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
