Vue.component('global-map', {

    props: {
        value: {
            default: []
        },

        i18n: {}


    }


    ,

    data: function () {
        return {

            locations: this.value.length ? this.value : [],
            mapHeight: 300,
            zoom: 10,
            mapKey: 0,
            mapsApiEndpoint: mapsApiEndpoint,
            subdomains: null,
            lat: geoMapDefaultCenter.lat,
            lng: geoMapDefaultCenter.lng,
            attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
            osmAttribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
            satellite: null,
            defaultTile: true,


        }

    },


    mounted() {

        let map = this.$refs.map.mapObject;

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

    watch: {
        value(val, old) {

            if (val && val.length || val != old) {

                this.locations = val;
                this.fitMarkers();
            }
            if (val.length == 0) {
                this.$refs.map.mapObject.setView([this.lat, this.lng]);

            }

        },

        locations() {
            this.$emit('input', this.locations)
        }

    },

    methods: {

        toggleSatellite() {
            // use subdomains to identify state
            if (this.defaultTile){
            this.defaultTile = false;
            this.satellite.addTo(this.$refs.map.mapObject);
            }
            else {
                this.defaultTile = true;
                this.$refs.map.mapObject.removeLayer(this.satellite);

            }




            // Working hack : redraw the tile layer component via Vue key
            this.mapKey += 1;

        },

        fsHandler() {

            //allow some time for the map to enter/exit fullscreen
            setTimeout(() => this.fitMarkers(), 500);
        },


        redraw() {
            this.$refs.map.mapObject.invalidateSize();
        },


        fitMarkers() {

            // construct a list of markers to build a feature group
            let map = this.$refs.map.mapObject;


            let markers = [];

            if (this.locations.length) {

                for (loc of this.locations) {
                    markers.push(L.marker(loc));
                }
                ;


                // build a feature group
                let fg = L.featureGroup(markers);
                let bounds = fg.getBounds();


                map.fitBounds(bounds, {padding: [20, 20]});

                if (map.getZoom() > 14) {
                    // flyout of center when map is zoomed in too much (single marker or many dense markers)

                    map.flyTo(map.getCenter(), 10, {duration: 1});
                }


            }

            map.invalidateSize();

        },


    },

    template: `
      <div>
      <v-card outlined color="grey lighten-3">

        <v-card-text>
          <div class="d-flex mb-3 align-center" style="column-gap: 10px">
            <div class="caption">
              <v-icon small color="#00a1f1"> mdi-checkbox-blank-circle</v-icon>
              {{ i18n.locations_ }}
            </div>
            <div class="caption">
              <v-icon small color="#ffbb00"> mdi-checkbox-blank-circle</v-icon>
              {{ i18n.geoMarkers_ }}
            </div>
            <div class="caption">
              <v-icon small color="#f65314"> mdi-checkbox-blank-circle</v-icon>
              {{ i18n.events_ }}
            </div>

          </div>

          <l-map @fullscreenchange="fsHandler" @dragend="redraw" ref="map" @ready="fitMarkers" :zoom="zoom"
                 :style=" 'resize:vertical;height:'+ mapHeight + 'px'"
                 :center="[lat,lng]">
            <l-tile-layer v-if="defaultTile" :attribution="attribution" :key="mapKey" :url="mapsApiEndpoint" :subdomains="subdomains">
            </l-tile-layer>
            <l-control class="example-custom-control">
              <v-btn v-if="__GOOGLE_MAPS_API_KEY__" @click="toggleSatellite" small fab>
                <img src="/static/img/satellite-icon.png" width="18"></img>
              </v-btn>
            </l-control>


            <l-feature-group ref="featGroup">
              <l-circle-marker class-name="circle-marker" radius="0" weight="16" fill-opacity="0.6"
                               v-for="(marker, i) in locations" :color="marker.color"
                               :lat-lng="[marker.lat,marker.lng]" :key="i">

                <l-popup>
                  <div style="position: relative;">
                    <v-avatar v-if="marker.number" color="grey lighten-4 float-right " size="22">{{ marker.number }}
                    </v-avatar>
                    <h4 v-if="marker.title" class="my-1 subtitle-1" small color="grey lighten-3">{{ marker.title }}</h4>

                    <v-chip small color="grey lighten-4" label class="caption black--text">{{ marker.lat.toFixed(6) }} |
                      {{ marker.lng.toFixed(6) }}
                    </v-chip>

                    <v-chip v-if="marker.full_string" small color="grey lighten-4" label
                            class="chipwrap my-2 caption black--text">
                      <v-icon x-small left>mdi-map-marker</v-icon>
                      {{ marker.full_string }}
                    </v-chip>
                    <div class="my-1">
                      <v-chip label v-if="marker.type" class="my-1" small color="lime lighten-3">{{ marker.type }}
                      </v-chip>
                    </div>


                  </div>


                </l-popup>


              </l-circle-marker>
            </l-feature-group>


          </l-map>


        </v-card-text>
      </v-card>
      </div>
    `
})