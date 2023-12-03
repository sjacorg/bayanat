Vue.component("geo-map", {
    props: {
        title: String,
        value: {},

        mapHeight: {
            default: 300
        },
        mapZoom: {
            default: 10
        },
        editMode: {
            type: Boolean,
            default: true
        },
        radiusControls: {
            type: Boolean,
            default: false,
        },
        others: []
    },

    computed: {
        map() {
            return this.$refs.map.mapObject;
        },

        mapCenter() {
            if (this.lat && this.lng) {
                return [this.lat, this.lng];
            }
            return geoMapDefaultCenter;
        },

        extra() {
            // computed property to display other markers, it should exclude the main marker
            if (this.others && this.value) {


                // console.log(this.others.filter(x=> x.lat!=this.value.lat && x.lng != this.value.lng));
                return this.others.filter(x => x.lat != this.value.lat && x.lng != this.value.lng);

            }
            return []
        },
    },


    data: function () {

        return {
            mapKey: 0,
            lat: (this.value && this.value.lat),
            lng: (this.value && this.value.lng),
            radius: this.value && this.value.radius ? this.value.radius : 1000, // Default to 1000


            subdomains: null,
            mapsApiEndpoint: mapsApiEndpoint,

            location: null,
            attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
            osmAttribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',

            defaultTile: true,
            satellite: null,

            radiusCircle: null,
        }
    },


    watch: {

        value(val) {
            if (!val) {
                this.lat = undefined;
                this.lng = undefined;
                this.radius = 100; // reset
                return;
            }
            // Prevent string or negative radius on backend
        if (typeof val.radius !== 'string' && val.radius >= 0) {

                this.radius = val.radius;
                this.clearAddRadiusCircle();

            }

            // Only send coordinate pairs to backend
            if (val.lat && val.lng) {
                this.lat = val.lat;
                this.lng = val.lng;

            }

        },

        lat: {
            handler: 'broadcast',
        },

        lng: {
            handler: 'broadcast'
        },

        radius: {
            handler: 'broadcast',
        },
    },

    mounted() {

        window.addEventListener('resize', this.fixMap);


        this.fixMap();
        this.broadcast();
        this.map.addControl(new L.Control.Fullscreen({
            title: {
                'false': 'View Fullscreen',
                'true': 'Exit Fullscreen'
            }
        }));
        this.satellite = L.gridLayer
            .googleMutant({
                type: "satellite", // valid values are 'roadmap', 'satellite', 'terrain' and 'hybrid'
            })
    },

    // clean up resize event listener
    beforeDestroy() {
        window.removeEventListener('resize', this.fixMap);
    },


    methods: {

        fixMap() {

            this.$nextTick(() => {
                if (this.map) {
                    this.map.invalidateSize();
                }


                // Add error handling for the tile layer
                L.tileLayer(this.mapsApiEndpoint).on('error', function (error) {
                    console.error('Tile layer error:', error);
                }).addTo(this.map);
            });
        },

        toggleSatellite() {
            if (this.defaultTile) {
                this.satellite.addTo(this.map);
                this.defaultTile = false;

            } else {
                this.defaultTile = true;
                this.map.removeLayer(this.satellite);
            }


            // Working hack : redraw the tile layer component via Vue key
            this.mapKey += 1;

        },

        clearMarker(evt) {

            this.lat = this.lng = null;
            this.map.removeLayer(this.radiusCircle);

        },

        setMarker(evt) {
            if (this.editMode) {
                this.lat = evt.latlng.lat;
                this.lng = evt.latlng.lng;
            }
        },


        updateLocation(point) {
            this.lat = point.lat;
            this.lng = point.lng;
        },

        clearAddRadiusCircle() {


            if (!this.radiusControls) {
                return;
            }


            // Remove existing radius circle if it exists
            if (this.radiusCircle) {
                this.map.removeLayer(this.radiusCircle);
            }

            // If radius is not provided, return
            if (!this.radius) {
                return;
            }


            if (!this.lat || !this.lng) {
                return;
            }
            this.radiusCircle = L.circle([this.lat, this.lng], {
                radius: this.radius
            });
            this.radiusCircle.addTo(this.map);

            debounce(() => {
                const bounds = this.radiusCircle.getBounds();
                this.map.fitBounds(bounds);
            }, 250)();
        },

        broadcast() {
            // Only return obj if both lat,lng values present
            if (this.lat && this.lng) {
                const obj = {lat: this.lat, lng: this.lng};
                if (this.radiusControls && this.radius) {
                    obj.radius = this.radius;
                }
                this.$emit('input', obj);
                return;
            }

            this.$emit('input', undefined);
        },
    },
    template:
        `
          <v-card class="pa-1" elevation="0">

          <v-card-text>
            <h3 v-if="title" class=" mb-5">{{ title }}</h3>
            <div v-if="editMode" class="d-flex" style="column-gap: 20px;">
              <v-text-field dense type="number" min="-90" max="90" :label="translations.latitude_"
                            v-model.number="lat"></v-text-field>
              <v-text-field dense type="number" min="-180" max="180" :label="translations.longitude_"
                            v-model.number="lng"></v-text-field>
              <v-btn v-if="lat&&lng" small @click="clearMarker" text fab>
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </div>

            <div v-if="editMode && radiusControls">
                 
            
                <v-slider
                    v-if="editMode && radiusControls"
                    class="mt-1 align-center"
                    :min="100"
                    :max="100000"
                    :step="100"
                    thumb-label
                    track-color="gray lighten-2"
                    v-model.number="radius"
                    :label="translations.radius_"
                >
                    <template v-slot:append>  
                        <v-text-field 
                            readonly
                            style="max-width:200px" 
                            v-model.number="radius"
                            :suffix="translations.meters_" 
                            outlined 
                            dense 
                        >
                        </v-text-field>
                    </template>
                  
                </v-slider>
              </div>

            <l-map @click="setMarker" class="mt-2" ref="map" :zoom="mapZoom"
                   :style="'border-radius: 8px;resize: vertical;height:'+ mapHeight + 'px'"
                   :center="mapCenter"
                   :options="{scrollWheelZoom:false}">
              <l-tile-layer :key="mapKey" v-if="defaultTile" :attribution="attribution" :url="mapsApiEndpoint"
                            :subdomains="subdomains"></l-tile-layer>
              <l-control class="example-custom-control">
                <v-btn v-if="__GOOGLE_MAPS_API_KEY__" @click="toggleSatellite" small fab>
                  <img src="/static/img/satellite-icon.png" width="18">
                </v-btn>
              </l-control>
              <l-marker
                  v-if="lat && lng"
                  @update:latLng="updateLocation"
                  :lat-lng="[lat,lng]"
                  :draggable="editMode"/>
              <l-marker
                  :draggable="false"
                  opacity="0.4"
                  v-for="marker in extra"
                  :lat-lng="[marker.lat,marker.lng]"/>
            </l-map>

          </v-card-text>

          </v-card>

        `,
});
