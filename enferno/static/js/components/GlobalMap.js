Vue.component('global-map', {

    props: {
        value: {
            default: []
        },

        i18n: {},
        legend: {
            default: true
        }
    }


    ,

    data: function () {
        return {

            locations: this.value.length ? this.value : [],
            mapHeight: 300,
            zoom: 10,
            mapKey: 0,
            //marker cluster
            mcg : null,
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

        // let markers = L.markerClusterGroup();
        // if(this.locations.length){
        //    for (const loc of this.locations) {
        //        markers.addLayer(L.marker([loc.lat,loc.lng]));
        //
        //    };
        //    map.addLayer(markers);
        //
        // }
        //


        // map.addLayer(markers);


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


            if (val && val.length || val !== old) {
                this.locations = val;
                this.fitMarkers();
            }
            if (val.length === 0) {
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
            if (this.defaultTile) {
                this.defaultTile = false;
                this.satellite.addTo(this.$refs.map.mapObject);
            } else {
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

            if(this.mcg){
                map.removeLayer(this.mcg);
            }
            this.mcg = L.markerClusterGroup();
            if (this.locations.length) {

                for (loc of this.locations) {
                    //preprocess bulletinId
                    loc.bulletinId = loc.bulletinId || '';
                    let marker = L.circleMarker([loc.lat, loc.lng], {
                        color: 'white',
                        fillColor: loc.color,
                        fillOpacity: 0.65,
                        radius: 8,
                        weight: 2,
                        stroke: 'white'
                    });
                    const heading = loc.number ? loc.number + '. ' + loc.title : loc.title;

                    marker.bindPopup(`
                     <span ><span title="*Bulletin ID" class="map-bid">${loc.bulletinId}</span><strong>
${heading}</strong> </span><br>
                    
                    <div class="mt-2">
                    
                    
                    ${loc.lat.toFixed(6)}, ${loc.lng.toFixed(6)}
                    </div>
                    <div class="mt-2 subtitle">${loc.full_string || ''}</div>
                    <div>${loc.type|| ''}</div>
                    `);
                    this.mcg.addLayer(marker);
                }
                ;


                // build a feature group

                let bounds = this.mcg.getBounds();
                this.mcg.addTo(map);


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
          <div v-if="legend" class="map-legend d-flex mb-3 align-center" style="column-gap: 10px">
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
                 :max-zoom="18"
                 :style=" 'resize:vertical;height:'+ mapHeight + 'px'"
                 :center="[lat,lng]" :options="{scrollWheelZoom:false}">
            <l-tile-layer v-if="defaultTile" :attribution="attribution" :key="mapKey" :url="mapsApiEndpoint"
                          :subdomains="subdomains">
            </l-tile-layer>
            <l-control class="example-custom-control">
              <v-btn v-if="__GOOGLE_MAPS_API_KEY__" @click="toggleSatellite" small fab>
                <img src="/static/img/satellite-icon.png" width="18"></img>
              </v-btn>
            </l-control>


          </l-map>


        </v-card-text>
      </v-card>
      </div>
    `
})