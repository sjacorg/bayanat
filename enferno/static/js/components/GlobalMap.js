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
      return this.locations.filter(loc => this.selectedLocations.includes(loc.eventtype) || !('eventtype' in loc));
    },
    currentYear() {
      return new Date().getFullYear();
    },
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
      googleAttribution: `&copy; <a href="https://www.google.com/maps">Google Maps</a>, Imagery ©${this.currentYear} Google, Maxar Technologies`,
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
        this.selectedLocations = [...this.uniqueEventTypes];
        this.fitMarkers();
        this.updateMapBounds();
      }
      if (val.length === 0) {
        this.map.setView([this.lat, this.lng]);
      }
    },
    selectedLocations(val) {
      this.clearAllLayers();
      this.fitMarkers();
    },
    locations() {
      this.$emit('update:modelValue', this.locations);
    },
  },

  methods: {
    generatePopupContent(loc) {
      const t = this.translations;

      // Dates
      const dates = [];
      if (loc.from_date) dates.push(`<span class="chip">${this.$root.formatDate(loc.from_date, loc.from_date.includes('T00:00') ? this.$root.dateFormats.standardDate : this.$root.dateFormats.standardDatetime)}</span>`);
      if (loc.from_date && loc.to_date) dates.push(`<i class="mdi mdi-arrow-right mr-1">`);
      if (loc.to_date) dates.push(`<span></i>${this.$root.formatDate(loc.to_date, loc.to_date.includes('T00:00') ? this.$root.dateFormats.standardDate : this.$root.dateFormats.standardDatetime)}</span>`);

      const estimated = loc.estimated
        ? `<i class="mdi mdi-calendar-question mr-1" title="${t.timingForThisEventIsEstimated_}"></i>`
        : '<i class="mdi mdi-calendar-clock mr-1"></i>';

      const dateRange = dates.length ? `<div class="d-flex">${estimated} ${dates.join(' ')}</div>` : '';

      const parentId = loc?.parentId && loc?.show_parent_id ? `<div><i class="mdi mdi-link mr-1"></i>${loc.parentId}</div>` : '';

      // Copy button using data-copy instead of onclick
      const copyCoordsBtn = (Number.isFinite(loc.lat) && Number.isFinite(loc.lng))
        ? `<button type="button" class="ml-1" title="${t.copyCoordinates_}" data-copy="${loc.lat.toFixed(6)}, ${loc.lng.toFixed(6)}">
            <i class="mdi mdi-content-copy" aria-hidden="true"></i>
          </button>`
        : '';

      const eventType = loc.eventtype ? `<div class="d-flex align-center"><i class="mdi mdi-calendar-range mr-1"></i>${loc.eventtype || ''}</div>` : '';

      const locNumber = loc.number ? `<div class="d-flex align-center">#${loc.number || ''}</div>` : '';

      const html = `<div class="popup-content d-flex flex-column ga-1">
        <div class="d-flex ga-2">${locNumber} ${parentId} ${eventType}</div>
        <h4>${loc.title || ''}</h4>
        <div class="d-flex align-center">
          <i class="mdi mdi-map-marker-outline mr-1"></i>
          ${loc.full_string || ''}
          ${copyCoordsBtn}
        </div>
        ${loc.main ? `<div>${t.mainIncident_}</div>` : ''}
        ${dateRange}
      </div>`;

      // Turn into DOM so we can attach events
      const wrapper = document.createElement('div');
      wrapper.innerHTML = html;

      const btn = wrapper.querySelector('button[data-copy]');
      if (btn) {
        btn.addEventListener('click', () => {
          navigator.clipboard.writeText(btn.getAttribute('data-copy'))
            .then(() => this.$root.showSnack(t.copiedToClipboard_))
            .catch(() => this.$root.showSnack(t.failedToCopyCoordinates_))
        });
      }

      return wrapper;
    },

    initMap() {
      this.map = L.map(this.mapId, {
        center: [this.lat, this.lng],
        zoom: this.zoom,
        scrollWheelZoom: false,
        zoomAnimation: false,
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
    updateMapBounds() {
      // Fit map of bounds of clusterLayer
      let bounds = this.markerGroup.getBounds();
      if (bounds.isValid()){
        this.map.fitBounds(bounds, { padding: [20, 20] });
      }


      if (this.map.getZoom() > 14) {
        // flyout of center when map is zoomed in too much (single marker or many dense markers)
        this.map.flyTo(this.map.getCenter(), 10, { duration: 1 });
      }
    },
    clearAllLayers() {
      // Remove marker cluster group
      this.markerGroup?.clearLayers?.();

      // Remove event links group
      this.eventLinks?.clearLayers?.();
    },
    fitMarkers() {
      // construct a list of markers to build a feature group
      if (this.markerGroup) {
        this.map.removeLayer(this.markerGroup);
      }

      this.markerGroup = L.markerClusterGroup({
        maxClusterRadius: 20,
      });

      const visibleLocations = this.filteredLocations || [];
      if (visibleLocations?.length) {
        let eventLocations = [];

        const locationsWithCoordinates = visibleLocations.filter(loc => loc.lat && loc.lng);
        for (const loc of locationsWithCoordinates) {

          if (loc.main) {
            loc.color = '#000000';
          }

          let marker = L.circleMarker([loc.lat, loc.lng], {
            color: 'white',
            fillColor: loc.color,
            fillOpacity: 0.65,
            radius: 8,
            weight: 2,
            stroke: 'white',
          });

          if (loc.type === 'Event') {
            // Add the events latlng to the latlngs array
            eventLocations.push(loc);
          }

          marker.bindPopup(this.generatePopupContent(loc));

          this.markerGroup.addLayer(marker);
        }

        // Add event linestring links
        this.addEventRouteLinks(eventLocations);

        if (!this.measureControls) {
          this.measureControls = L.control.polylineMeasure({
            position: 'topleft',
            unit: 'kilometres',
            fixedLine: {
              // Styling for the solid line
              color: 'rgba(67,157,146,0.77)', // Solid line color
              weight: 2, // Solid line weight
            },

            arrow: {
              // Styling of the midway arrow
              color: 'rgba(67,157,146,0.77)', // Color of the arrow
            },
            showBearings: false,
            clearMeasurementsOnStop: false,
            showClearControl: true,
            showUnitControl: true,
          });

          this.measureControls.addTo(this.map);
        }

        this.markerGroup.addTo(this.map);
      }
    },

    addEventRouteLinks(eventLocations) {
      // Remove existing eventRoute linestrings
      if (this.eventLinks) {
        this.map.removeLayer(this.eventLinks);
      }
      this.eventLinks = L.layerGroup().addTo(this.map);

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

              <v-menu v-if="uniqueEventTypes.length > 1" :close-on-content-click="false">
                <template v-slot:activator="{ props: menuProps }">
                  <v-tooltip location="bottom">
                    <template v-slot:activator="{ props: tooltipProps }">
                      <v-btn
                        v-bind="{ ...menuProps, ...tooltipProps }"
                        icon="mdi-dots-vertical"
                        variant="outlined"
                        density="compact"
                        class="ml-2 mb-4"
                        @click="this.map.closePopup()"
                      />
                    </template>
                    {{ translations.showOrHideEventTypes_ }}
                  </v-tooltip>
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
                        <v-checkbox-btn
                          :model-value="isSelected"
                          @update:model-value="select"
                        />
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
