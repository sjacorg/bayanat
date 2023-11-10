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
            // Marker cluster
            markerGroup: null,
            // Event routes
            eventLinks: null,
            mapsApiEndpoint: mapsApiEndpoint,
            subdomains: null,
            lat: geoMapDefaultCenter.lat,
            lng: geoMapDefaultCenter.lng,
            attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
            osmAttribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
            satellite: null,
            defaultTile: true,
            measureControls: null,


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

            const map = this.$refs.map.mapObject;

            if (this.markerGroup) {
                map.removeLayer(this.markerGroup);
            }

            this.markerGroup = L.markerClusterGroup({
                maxClusterRadius: 20,
            });

            if (this.locations.length) {
                let eventLocations = [];

                for (loc of this.locations) {
                    mainStr = false
                    if (loc.main) {
                        mainStr = this.i18n.mainIncident_;
                        loc.color = '#000000';
                    }

                    let marker = L.circleMarker([loc.lat, loc.lng], {
                        color: 'white',
                        fillColor: loc.color,
                        fillOpacity: 0.65,
                        radius: 8,
                        weight: 2,
                        stroke: 'white'
                    });

                    if (loc.type === 'Event') {

                        // Add the events latlng to the latlngs array
                        eventLocations.push(loc);
                    }

                    marker.bindPopup(`

                    <span title="No." class=" ma-1 map-bid">${loc.number || ''}</span>
                    <span title="Bulletin ID" class="ma-1 map-bid">${loc.parentId || ''}</span>
                    <strong class="body-2">${loc.title || ''}</strong> </span><br>
                    
                    <div class="mx-1 my-4 subtitle-2 font-weight-bold">
                    ${loc.lat.toFixed(6)}, ${loc.lng.toFixed(6)}
                    </div>

                    <span class="mt-1 subtitle">${loc.full_string || ''}</span>
                    <span title="Geo Marker Type" class="ma-1 map-bid">${loc.type || ''}</span>
                    <span title="Geo Marker Event Type" class=" ma-1 map-bid">${loc.eventtype || ''}</span>
                    <span title="Main Incident" class=" ma-1 map-bid">${mainStr || ''}</span>
                    `);
                    this.markerGroup.addLayer(marker);
                }

                // Add event linestring links if any available
                if (eventLocations.length > 1) {
                    this.addEventRouteLinks(eventLocations);
                }

                if (!this.measureControls) {

                    this.measureControls = L.control.polylineMeasure({
                        position: 'topleft',
                        unit: 'kilometres',
                        fixedLine: {                    // Styling for the solid line
                            color: 'rgba(67,157,146,0.77)',              // Solid line color
                            weight: 2                   // Solid line weight
                        },

                        arrow: {                        // Styling of the midway arrow
                            color: 'rgba(67,157,146,0.77)',              // Color of the arrow
                        },
                        showBearings: false,
                        clearMeasurementsOnStop: false,
                        showClearControl: true,
                        showUnitControl: true
                    });


                    this.measureControls.addTo(map);
                }


                // Fit map of bounds of clusterLayer
                let bounds = this.markerGroup.getBounds();
                this.markerGroup.addTo(map);
                map.fitBounds(bounds, {padding: [20, 20]});

                if (map.getZoom() > 14) {
                    // flyout of center when map is zoomed in too much (single marker or many dense markers)

                    map.flyTo(map.getCenter(), 10, {duration: 1});
                }
            }


            map.invalidateSize();

        },

        addEventRouteLinks(eventLocations) {
            const map = this.$refs.map.mapObject;

            // Remove existing eventRoute linestrings
            if (this.eventLinks) {
                map.removeLayer(this.eventLinks);
            }
            this.eventLinks = L.layerGroup({}).addTo(map);

            for (let i = 0; i < eventLocations.length - 1; i++) {
                const startCoord = [eventLocations[i].lat, eventLocations[i].lng];
                const endCoord = [eventLocations[i + 1].lat, eventLocations[i + 1].lng];

                // If the next eventLocation has the zombie attribute, do not draw the curve
                if (eventLocations[i + 1].zombie) {
                    // Add a circle marker for the zombie event location
                    L.circleMarker(endCoord, {
                        radius: 5,
                        fillColor: "#ff7800",
                        color: "#000",
                        weight: 1,
                        opacity: 1,
                        fillOpacity: 0.8
                    }).addTo(this.eventLinks);
                    continue; // Skip to the next iteration
                }

                const midpointCoord = this.getCurveMidpointFromCoords(startCoord, endCoord);

                // Create bezier curve path between events
                const curve = L.curve(
                    [
                        'M', startCoord,
                        'Q', midpointCoord,
                        endCoord
                    ], {
                        color: '#00f166',
                        weight: 4,
                        opacity: 0.4,
                        dashArray: '5', animate: {duration: 15000, iterations: Infinity}
                    }
                ).addTo(this.eventLinks);

                const curveMidPoints = curve.trace([0.8]);
                const arrowIcon = L.icon({
                    iconUrl: '/static/img/direction-arrow.svg',
                    iconSize: [12, 12],
                    iconAnchor: [6, 6],
                });

                curveMidPoints.forEach(point => {
                    const rotationAngle = this.getVectorDegrees(startCoord, endCoord);
                    L.marker(point, {icon: arrowIcon, rotationAngle: rotationAngle}).addTo(this.eventLinks);
                });
            }
        },


        getCurveMidpointFromCoords(startCoord, endCoord) {
            const offsetX = endCoord[1] - startCoord[1],
                offsetY = endCoord[0] - startCoord[0];

            const r = Math.sqrt(Math.pow(offsetX, 2) + Math.pow(offsetY, 2)),
                theta = Math.atan2(offsetY, offsetX);

            const thetaOffset = (3.14 / 10);

            const r2 = (r / 2) / (Math.cos(thetaOffset)),
                theta2 = theta + thetaOffset;

            const midpointLng = (r2 * Math.cos(theta2)) + startCoord[1],
                midpointLat = (r2 * Math.sin(theta2)) + startCoord[0];

            return [midpointLat, midpointLng];
        },

        getVectorDegrees(start, end) {
            const dx = end[0] - start[0];
            const dy = end[1] - start[1];
            return Math.atan2(dy, dx) * (180 / Math.PI);
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
              <v-icon small color="#00f166"> mdi-checkbox-blank-circle</v-icon>
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