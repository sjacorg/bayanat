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
        editMode : {
            type: Boolean,
            default: true
        },
        others: []


    },

    computed: {

        mapCenter() {
          if (this.lat && this.lng){
              return [this.lat,this.lng];
          }
          return geoMapDefaultCenter;

        },
        extra() {
            // computed property to display other markers, it should exclude the main marker
            if (this.others && this.value) {


                // console.log(this.others.filter(x=> x.lat!=this.value.lat && x.lng != this.value.lng));
                return this.others.filter(x=> x.lat!=this.value.lat && x.lng != this.value.lng);

            }
            return []
        }


    },

    data: function () {

        return {
            mapKey: 0,
            lat: (this.value && this.value.lat),
            lng: (this.value && this.value.lng),
            subdomains: null,
            mapsApiEndpoint: mapsApiEndpoint,

            location: null,
            attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
            osmAttribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',

            defaultTile: true,
            satellite: null,


        }
    },


    watch: {

        value(val) {


            if (val && val.lat && val.lng) {

                this.lat = val.lat;
                this.lng = val.lng;

            }

        },


        lat: {
            handler: 'broadcast',

        },
        lng: {
            handler: 'broadcast'
        }


    },

    mounted() {
        let map = this.$refs.map.mapObject;
        setTimeout(() => {

            map.invalidateSize();
        }, 500)
        this.broadcast();
         map.addControl(new L.Control.Fullscreen({
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


    methods: {

        toggleSatellite() {
            if (this.defaultTile) {
                this.satellite.addTo(this.$refs.map.mapObject);
                this.defaultTile = false;

            } else {
                this.defaultTile = true;
                this.$refs.map.mapObject.removeLayer(this.satellite);
            }


            // Working hack : redraw the tile layer component via Vue key
            this.mapKey += 1;

        },


        setMarker(evt) {
            if (this.editMode){
            this.lat = evt.latlng.lat;
            this.lng = evt.latlng.lng;
            }
        },


        updateLocation(point) {
            this.lat = point.lat;
            this.lng = point.lng;


        },
        broadcast() {

            this.$emit('input', {lat: this.lat, lng: this.lng});

        }
    },
    template:
        `
          <v-card class="pa-1" elevation="0">

          <v-card-text>
            <h3 v-if="title" class=" mb-5">{{ title }}</h3>
            <div v-if="editMode" class="d-flex" style="column-gap: 20px;">
              <v-text-field dense type="number" min="-90" max="90" :label="translations.latitude_" v-model.number="lat"></v-text-field>
              <v-text-field dense type="number" min="-180" max="180" :label="translations.longitude_" v-model.number="lng"></v-text-field>
            </div>


            <l-map @click="setMarker" class="mt-4" ref="map" :zoom="mapZoom"
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
              <l-marker v-if="lat && lng" @update:latLng="updateLocation" :lat-lng="[lat,lng]" :draggable="editMode"></l-marker>
              <l-marker :draggable="false" opacity="0.4" v-for="marker in extra"
                        :lat-lng="[marker.lat,marker.lng]"></l-marker>

            </l-map>

          </v-card-text>

          </v-card>

        `,
});
