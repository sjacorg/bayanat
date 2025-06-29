const GeoLocations = Vue.defineComponent({
  props: {
    modelValue: {
      default: [],
    },
    others: {
      type: Array,
      default: () => [],
    },
    dialogProps: {
      type: Object,
      default: () => ({}),
    },
  },
  emits: ['update:modelValue', 'locations-updated'],

  data: function () {
    return {
      translations: window.translations,
      // temp item to hold new locations
      e: {},
      addDlg: false,
      eindex: null,
      locations: this.modelValue.length ? this.modelValue : [],
    };
  },

  mounted() {
    
  },
  computed: {
    eformValid() {
      if (this.e.latlng) {
        if (this.e.latlng.lat && this.e.latlng.lng) {
          return true;
        }
      }
      return false;
    },
  },

  watch: {
    modelValue(val) {
      if (val && val.length) {
        this.locations = val;
      }
    },
  },

  methods: {
    newLocation() {
      this.e = { latlng: { lat: geoMapDefaultCenter.lat, lng: geoMapDefaultCenter.lng } };

      this.addDlg = true;
    },
    saveLocation() {
      if (this.e.mode === 'edit') {
        this.modifyLocation();
      } else {
        this.addLocation();
      }
      this.$emit('update:modelValue', this.locations);
    },

    modifyLocation() {
      //preprocess
      this.e.lat = this.e.latlng.lat;
      this.e.lng = this.e.latlng.lng;

      this.locations[this.eindex] = this.e;
      this.resetLocationEditor();
      // broadcast an event to  refresh parent global map
      this.$emit('locations-updated');
    },

    addLocation() {
      this.e.lat = this.e.latlng.lat;
      this.e.lng = this.e.latlng.lng;

      this.locations.push(this.e);
      this.resetLocationEditor();
    },
    editLocation(item, index) {
      item.latlng = { lat: item.lat, lng: item.lng };
      this.e = { ...item, mode: 'edit' };

      this.eindex = index;
      this.addDlg = true;
      this.e.mode = 'edit';
    },
    resetLocationEditor() {
      this.addDlg = false;
      this.e = {};
    },

    removeLocation(i) {
      if (confirm(this.translations.confirm_)) {
        this.locations.splice(i, 1);
        this.$emit('update:modelValue', this.locations);
      }
    },
  },

  template: `
      <div>
        <v-card>
          <v-toolbar elevation="0">
            <v-toolbar-title>
              {{ translations.geoMarkers_ }}
            </v-toolbar-title>
            <v-spacer></v-spacer>
            <v-btn icon="mdi-plus-circle" color="primary" @click="newLocation" variant="text"></v-btn>
          </v-toolbar>


          <v-card-text>
            <v-container fluid>
              <v-row>
                <v-col v-for="(loc,i) in locations" :key="i" cols="12" md="4">
                  <v-card>
                    <v-card-text>

                      <v-chip size="small" class="primary">{{ i + 1 }}</v-chip>
                      <v-chip size="small" v-if="loc.geotype" class="grey lighten-3">{{ loc.geotype.title }}</v-chip>
                      <v-chip size="small" v-if="loc.main" class="grey lighten-3">{{ translations.mainIncident_ }}</v-chip>
                      <h4 class="pa-3 mb-2 text-caption">{{ loc.title }}</h4>
                      <div class="text-subtitle-1 ">
                        <v-icon size="small" left>mdi-map-marker</v-icon>
                        {{ loc.lat.toFixed(4) }} , {{ loc.lng.toFixed(4) }}
                      </div>

                      <div v-if="loc.comment" class="comments pa-3 mt-2" v-html="loc.comment">

                      </div>


                    </v-card-text>

                    <v-card-actions class="justify-end">
                      <v-btn
                          @click="editLocation(loc,i)"
                          size="small"
                          icon="mdi-pencil"
                      >

                      </v-btn
                      >
                      <v-btn
                          @click="removeLocation(i)"
                          icon="mdi-delete-sweep"
                          size="small"
                          color="red"
                      >

                      </v-btn
                      >
                    </v-card-actions>

                  </v-card>

                </v-col>
              </v-row>
            </v-container>


            <v-card>

            </v-card>


          </v-card-text>
        </v-card>
        <v-dialog v-if="addDlg" max-width="770" v-model="addDlg" v-bind="dialogProps">
          <v-card>
            <v-toolbar :title="translations.addGeoMarker_">
              <template #append>
                <v-btn @click="addDlg=false" icon="mdi-close"></v-btn>
              </template>

            </v-toolbar>


            <v-card-text>
              <div class="d-flex px-5 ga-3">
                <v-text-field v-model="e.title" :label="translations.title_"></v-text-field>

                <search-field
                    :label="translations.type_"
                    api="/admin/api/geolocationtypes/"
                    v-model="e.geotype"
                    item-title="title"
                    item-value="id"
                    :multiple="false"
                >
                </search-field>
              </div>
              <div class="d-flex px-5 ga-2">
                <v-text-field v-model="e.comment" :label="translations.comments_"></v-text-field>
                <v-checkbox :label="translations.mainIncident_" v-model="e.main"></v-checkbox>
              </div>

            </v-card-text>
            <v-card-text>
              <geo-map :radius-controls="false" :others="others" v-model="e.latlng" :map-height="300"></geo-map>
            </v-card-text>
            <v-card-actions class="pa-4">
              <v-spacer></v-spacer>
              <v-btn :disabled="!eformValid" @click="saveLocation" variant="elevated" width="220" color="primary">
                {{ translations.save_ }}
              </v-btn>
              <v-spacer></v-spacer>
            </v-card-actions>
          </v-card>

        </v-dialog>
      </div>
    `,
});
