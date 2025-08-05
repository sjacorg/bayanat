const GlobalMap = Vue.defineComponent({
  props: {
    modelValue: {
      default: [],
    },
    legend: {
      default: true,
    },
  },
  computed: {
    uniqueEventTypes() {
      return [...new Set(this.locations.map(loc => loc.eventtype).filter(Boolean))];
    },
    filteredLocations() {
      return this.locations.filter(loc => this.selectedLocations.includes(loc.eventtype));
    }
  },

  data: function () {
    return {
      translations: window.translations,
      mapId: 'map-' + this.$.uid,
      locations: this.modelValue?.length ? this.modelValue : [],
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
      googleAttribution: '&copy; <a href="https://www.google.com/maps">Google Maps</a>, Imagery ©2025 Google, Maxar Technologies',
      measureControls: null,
      selectedLocations: [],
    };
  },

  mounted() {
    this.map = null;
    this.initMap();
  },

  watch: {
    modelValue(val, old) {

      if (val?.length || val !== old) {
        this.locations = val;
        this.fitMarkers();
        this.selectedLocations = [...this.uniqueEventTypes];
      }
      if (val.length === 0) {
        this.map.setView([this.lat, this.lng]);
      }
    },

    selectedLocations(val) {
      this.fitMarkers();
    },

    locations() {

      this.$emit('update:modelValue', this.locations);
    },
  },

  methods: {
    generatePopupContent(loc) {
      function renderIfExists(label, value) {
        return value ? `${label ? `<b>${label}:</b>` : ''} ${value}` : ''
      }
      // Simple HTML structure for popup content. Adjust as needed.
      return `<div class="popup-content">
      <h4>${renderIfExists('', loc.title)}</h4>
      <div>${renderIfExists(this.translations.number_, loc.number)} ${renderIfExists(this.translations.parentId_, loc.parentId)}</div>
      <div>${renderIfExists(this.translations.coordinates_, `${loc.lat?.toFixed(6)}, ${loc.lng?.toFixed(6)}`)}</div>
      <div>${renderIfExists('', loc.full_string)}</div>
      ${loc.main ? `<div>${this.translations.mainIncident_}</div>` : ''}
      <div>${renderIfExists(this.translations.type_, loc.geotype?.title)}</div>
      <div>${renderIfExists(this.translations.eventType_, loc.eventtype)}</div>
    </div>`;
    },

    initMap() {

      this.map = L.map(this.mapId, {
        center: [this.lat, this.lng],
        zoom: this.zoom,
        scrollWheelZoom: false,
      });

      // Add the default tile layer
      const osmLayer = L.tileLayer(this.mapsApiEndpoint, {
        attribution: this.attribution,
      }).addTo(this.map);

      const googleLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        attribution: this.googleAttribution,
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      });

      const baseMaps = {
        'OpenStreetMap': osmLayer,
        'Google Satellite': googleLayer,
      };

      if (window.__GOOGLE_MAPS_API_KEY__) {
        L.control.layers(baseMaps).addTo(this.map);
      }

      // Add fullscreen control
      this.map.addControl(
        new L.Control.Fullscreen({
          title: {
            false: this.translations.enterFullscreen_,
            true: this.translations.exitFullscreen_,
          },
        }),
      );

      this.fitMarkers();
    },

    fsHandler() {
      //allow some time for the map to enter/exit fullscreen
      setTimeout(() => this.fitMarkers(), 500);
    },

    redraw() {
      this.map.invalidateSize();
    },

    fitMarkers() {
      if (!this.map) return;

      // ensure markerGroup exists
      if (!this.markerGroup) {
        this.markerGroup = L.markerClusterGroup({ maxClusterRadius: 20 });
        // don't add to map here — we'll add after filling it
      } else {
        // remove existing event route links (we'll rebuild below)
        if (this.eventLinks) {
          this.map.removeLayer(this.eventLinks);
          this.eventLinks = null;
        }
        // clear markers in existing group (preserves cluster internals)
        this.markerGroup.clearLayers();
      }

      const visible = this.filteredLocations || [];
      if (visible.length) {
        const locationsWithCoordinates = visible.filter(loc => loc.lat && loc.lng);
        let eventLocations = [];

        for (const loc of locationsWithCoordinates) {
          if (loc.main) {
            loc.color = '#000000';
          }
          const marker = L.circleMarker([loc.lat, loc.lng], {
            color: 'white',
            fillColor: loc.color,
            fillOpacity: 0.65,
            radius: 8,
            weight: 2,
            stroke: 'white',
          });

          if (loc.type === 'Event') {
            eventLocations.push(loc);
          }

          marker.bindPopup(this.generatePopupContent(loc));
          this.markerGroup.addLayer(marker);
        }

        // Add event route links if needed
        if (eventLocations.length > 1) {
          this.addEventRouteLinks(eventLocations);
        }

        // Ensure markerGroup is added to the map
        if (!this.map.hasLayer(this.markerGroup)) {
          this.markerGroup.addTo(this.map);
        }

        // Fit bounds only if it changed (avoid refit flicker)
        const bounds = this.markerGroup.getBounds();
        if (bounds && bounds.isValid()) {
          const boundsStr = bounds.toBBoxString();
          if (this.lastBounds !== boundsStr) {
            this.lastBounds = boundsStr;
            // limit maxZoom so a single marker doesn't zoom crazy
            this.map.fitBounds(bounds, { padding: [20, 20], maxZoom: 14 });
          }
        }

        // If the map is zoomed in too far after fitBounds, nudge it out
        if (this.map.getZoom && this.map.getZoom() > 14) {
          this.map.flyTo(this.map.getCenter(), 10, { duration: 0.8 });
        }

        // add measureControls if not present
        if (!this.measureControls) {
          this.measureControls = L.control.polylineMeasure({
            position: 'topleft',
            unit: 'kilometres',
            fixedLine: { color: 'rgba(67,157,146,0.77)', weight: 2 },
            arrow: { color: 'rgba(67,157,146,0.77)' },
            showBearings: false,
            clearMeasurementsOnStop: false,
            showClearControl: true,
            showUnitControl: true,
          }).addTo(this.map);
        }
      } else {
        // no visible markers — clear group from map
        if (this.map.hasLayer && this.map.hasLayer(this.markerGroup)) {
          this.map.removeLayer(this.markerGroup);
        }
        this.lastBounds = null;
      }

      // Only invalidate once (needed if container changed); can be removed if not needed
      // small timeout helps Leaflet recalc right after DOM changes
      setTimeout(() => this.map.invalidateSize(), 50);
    },

    addEventRouteLinks(eventLocations) {
      // Remove existing eventRoute linestrings
      if (this.eventLinks) {
        this.map.removeLayer(this.eventLinks);
      }
      this.eventLinks = L.layerGroup({}).addTo(this.map);

      for (let i = 0; i < eventLocations.length - 1; i++) {
        const startCoord = [eventLocations[i].lat, eventLocations[i].lng];
        const endCoord = [eventLocations[i + 1].lat, eventLocations[i + 1].lng];

        // If the next eventLocation has the zombie attribute, do not draw the curve
        if (eventLocations[i + 1].zombie) {
          // Add a circle marker for the zombie event location
          L.circleMarker(endCoord, {
            radius: 5,
            fillColor: '#ff7800',
            color: '#000',
            weight: 1,
            opacity: 1,
            fillOpacity: 0.8,
          }).addTo(this.eventLinks);
          continue; // Skip to the next iteration
        }

        const midpointCoord = this.getCurveMidpointFromCoords(startCoord, endCoord);

        // Create bezier curve path between events
        const curve = L.curve(['M', startCoord, 'Q', midpointCoord, endCoord], {
          color: '#00f166',
          weight: 4,
          opacity: 0.4,
          dashArray: '5',
          animate: { duration: 15000, iterations: Infinity },
        }).addTo(this.eventLinks);

        const curveMidPoints = curve.trace([0.8]);
        const arrowIcon = L.icon({
          iconUrl: '/static/img/direction-arrow.svg',
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });

        curveMidPoints.forEach((point) => {
          const rotationAngle = this.getVectorDegrees(startCoord, endCoord);
          L.marker(point, { icon: arrowIcon, rotationAngle: rotationAngle }).addTo(this.eventLinks);
        });
      }
    },

    getCurveMidpointFromCoords(startCoord, endCoord) {
      const offsetX = endCoord[1] - startCoord[1],
        offsetY = endCoord[0] - startCoord[0];

      const r = Math.sqrt(Math.pow(offsetX, 2) + Math.pow(offsetY, 2)),
        theta = Math.atan2(offsetY, offsetX);

      const thetaOffset = 3.14 / 10;

      const r2 = r / 2 / Math.cos(thetaOffset),
        theta2 = theta + thetaOffset;

      const midpointLng = r2 * Math.cos(theta2) + startCoord[1],
        midpointLat = r2 * Math.sin(theta2) + startCoord[0];

      return [midpointLat, midpointLng];
    },

    getVectorDegrees(start, end) {
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      return Math.atan2(dy, dx) * (180 / Math.PI);
    },
  },

  beforeUnmount() {
    if (this.map) {
      this.map.remove();
    }
  },

  template: `
      <div>
        <v-card  variant="flat">
          <v-card-text>
            <div class="d-flex">
              <div v-if="legend" class="map-legend d-flex mb-3 align-center" style="column-gap: 10px">
                <div class="caption">
                  <v-icon small color="#00a1f1"> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.locations_ }}
                </div>
                <div class="caption">
                  <v-icon small color="#ffbb00"> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.geoMarkers_ }}
                </div>
                <div class="caption">
                  <v-icon small color="#00f166"> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.events_ }}
                </div>
              </div>

              <v-spacer></v-spacer>

              <v-menu v-if="uniqueEventTypes.length > 1">
                <template v-slot:activator="{ props }">
                  <v-btn
                    v-bind="props"
                    icon="mdi-dots-vertical"
                    variant="outlined"
                    size="small"
                    class="mb-2"
                  >
                  </v-btn>
                </template>
                <v-list
                  v-model:selected="selectedLocations"
                  select-strategy="leaf"
                >
                  <v-list-item
                    v-for="(eventType, index) in uniqueEventTypes"
                    :key="index"
                    :title="eventType"
                    :value="eventType"
                  >
                    <template v-slot:prepend="{ isSelected, select }">
                      <v-list-item-action start>
                        <v-checkbox-btn :model-value="isSelected" @update:model-value="select"></v-checkbox-btn>
                      </v-list-item-action>
                    </template>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>

            <div :id="mapId" :style="'resize:vertical;height:'+ mapHeight + 'px'"></div>
          </v-card-text>
        </v-card>
      </div>
    `,
});
