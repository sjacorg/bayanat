Vue.component('global-map', {

    props: {
        value: {
            default: []
        },


    }


    ,

    data: function () {
        return {

            locations: this.value.length ? this.value : [],
            mapHeight: 300,
            zoom: 10,
            mapsApiEndpoint: mapsApiEndpoint,
            lat: geoMapDefaultCenter.lat,
            lng: geoMapDefaultCenter.lng


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


    },

    watch: {
        value(val, old) {

            if (val && val.length || val !=old) {

                this.locations = val;
                this.fitMarkers();
            }
            if (val.length==0){
                this.$refs.map.mapObject.setView([this.lat,this.lng]);

            }

        },

        locations() {
            this.$emit('input', this.locations)
        }

    },

    methods: {

        fsHandler(){

        //allow some time for the map to enter/exit fullscreen
          setTimeout(()=> this.fitMarkers(), 500);
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

                    map.flyTo(map.getCenter(), 10,{duration: 1});
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
              Locations
            </div>
            <div class="caption">
              <v-icon small color="#ffbb00"> mdi-checkbox-blank-circle</v-icon>
              Geo Markers
            </div>
            <div class="caption">
              <v-icon small color="#f65314"> mdi-checkbox-blank-circle</v-icon>
              Events
            </div>

          </div>

          <l-map @fullscreenchange="fsHandler" @dragend="redraw" ref="map"  @ready="fitMarkers" :zoom="zoom"
                 :style=" 'resize:vertical;height:'+ mapHeight + 'px'"
                 :center="[lat,lng]">
            <l-tile-layer :url="mapsApiEndpoint">

            </l-tile-layer>
            <l-feature-group ref="featGroup">
              <l-circle-marker class-name="circle-marker" radius="0" weight="16" fill-opacity="0.6"
                               v-for="(marker, i) in locations" :color="marker.color"
                               :lat-lng="[marker.lat,marker.lng]" :key="i">

                <l-popup >
                  <div style="position: relative;">
                    <v-avatar v-if="marker.number" color="grey lighten-4 float-right " size="22">{{ marker.number }}</v-avatar>
                    <h4 v-if="marker.title" class="my-1 subtitle-1" small color="grey lighten-3">{{marker.title}}</h4>

                    <v-chip small color="grey lighten-4" label class="caption black--text">{{ marker.lat.toFixed(6) }} | {{ marker.lng.toFixed(6) }}</v-chip>
                    
                    <v-chip v-if="marker.full_string" small color="grey lighten-4" label class="chipwrap my-2 caption black--text"><v-icon x-small left>mdi-map-marker</v-icon> {{ marker.full_string}}</v-chip>
                    <div class="my-1">
                    <v-chip label v-if="marker.type" class="my-1" small color="lime lighten-3">{{marker.type}}</v-chip>  
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