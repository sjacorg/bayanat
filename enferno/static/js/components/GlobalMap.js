const GlobalMap = Vue.defineComponent({
  props: {
    modelValue: {
      default: [],
    },
    legend: {
      default: true,
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const translations = window.translations
    const mapId = 'map-' + Vue.getCurrentInstance().uid
    const map = Vue.shallowRef(null)
    const locations = Vue.ref(props.modelValue?.length ? props.modelValue : [])
    const mapHeight = 300
    const zoom = 10
    // Marker cluster
    const markerGroup = Vue.shallowRef(null)
    // Event routes
    const eventLinks = Vue.shallowRef(null)
    const lat = geoMapDefaultCenter.lat
    const lng =  geoMapDefaultCenter.lng
    const attribution = '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    const measureControls = Vue.shallowRef(null)

    function generatePopupContent(loc) {
      function renderIfExists(label, value) {
        return value ? `${label ? `<b>${label}:</b>` : ''} ${value}` : ''
      }
      // Simple HTML structure for popup content. Adjust as needed.
      return `<div class="popup-content">
      <h4>${renderIfExists('', loc.title)}</h4>
      <div>${renderIfExists(translations.number_, loc.number)} ${renderIfExists(translations.parentId_, loc.parentId)}</div>
      <div>${renderIfExists(translations.coordinates_, `${loc.lat?.toFixed(6)}, ${loc.lng?.toFixed(6)}`)}</div>
      <div>${renderIfExists('', loc.full_string)}</div>
      ${loc.main ? `<div>${translations.mainIncident_}</div>` : ''}
      <div>${renderIfExists(translations.type_, loc.geotype?.title)}</div>
      <div>${renderIfExists(translations.eventType_, loc.eventtype)}</div>
    </div>`;
    }

    function initMap() {
      map.value = L.map(mapId, {
        center: [lat, lng],
        zoom: zoom,
        scrollWheelZoom: false,
      });

      // Define the default OSM tile layer
      const osmLayer = L.tileLayer(mapsApiEndpoint, {
        attribution: attribution,
      }).addTo(map.value); // Add to map initially

      // Define the Google Maps tile layer
      const googleLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      });

      // Add fullscreen control
      map.value.addControl(
        new L.Control.Fullscreen({
          title: {
            false: translations.enterFullscreen_,
            true: translations.exitFullscreen_,
          },
        }),
      );

      // Define the base layers
      const baseMaps = {
        'OpenStreetMap': osmLayer,
        'Google Satellite': googleLayer,
      };

      // Add layer control to toggle between OSM and Google Maps
      if (window.__GOOGLE_MAPS_API_KEY__) {
        L.control.layers(baseMaps).addTo(map.value);
      }

      // Fit markers or other elements
      fitMarkers();
    }

    function fitMarkers() {
      // construct a list of markers to build a feature group

      if (markerGroup.value) {
        map.value.removeLayer(markerGroup.value);
      }

      markerGroup.value = L.markerClusterGroup({
        maxClusterRadius: 20,
      });
      if (locations.value?.length) {
        let eventLocations = [];

        const locationsWithCoordinates = locations.value.filter(loc => loc.lat && loc.lng);

        for (const loc of locationsWithCoordinates) {

          let mainStr = false;
          if (loc.main) {
            mainStr = translations.mainIncident_;
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

          marker.bindPopup(generatePopupContent(loc));

          markerGroup.value.addLayer(marker);
        }

        // Add event linestring links if any available
        if (eventLocations.length > 1) {
          addEventRouteLinks(eventLocations);
        }

        if (!measureControls.value) {
          measureControls.value = L.control.polylineMeasure({
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

          measureControls.value.addTo(map.value);
        }

        // Fit map of bounds of clusterLayer
        let bounds = markerGroup.value.getBounds();
        markerGroup.value.addTo(map.value);
        if (bounds.isValid()) {
          map.value.fitBounds(bounds, { padding: [20, 20] });
        }


        if (map.value.getZoom() > 14) {
          // flyout of center when map is zoomed in too much (single marker or many dense markers)

          map.value.flyTo(map.value.getCenter(), 10, { duration: 1 });
        }
      }

      map.value.invalidateSize();
    }

    function addEventRouteLinks(eventLocations) {
      // Remove existing eventRoute linestrings
      if (eventLinks.value) {
        map.value.removeLayer(eventLinks.value);
      }
      eventLinks.value = L.layerGroup({}).addTo(map.value);

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
          }).addTo(eventLinks.value);
          continue; // Skip to the next iteration
        }

        const midpointCoord = getCurveMidpointFromCoords(startCoord, endCoord);

        // Create bezier curve path between events
        const curve = L.curve(['M', startCoord, 'Q', midpointCoord, endCoord], {
          color: '#00f166',
          weight: 4,
          opacity: 0.4,
          dashArray: '5',
          animate: { duration: 15000, iterations: Infinity },
        }).addTo(eventLinks.value);

        const curveMidPoints = curve.trace([0.8]);
        const arrowIcon = L.icon({
          iconUrl: '/static/img/direction-arrow.svg',
          iconSize: [12, 12],
          iconAnchor: [6, 6],
        });

        curveMidPoints.forEach((point) => {
          const rotationAngle = getVectorDegrees(startCoord, endCoord);
          L.marker(point, { icon: arrowIcon, rotationAngle: rotationAngle }).addTo(eventLinks.value);
        });
      }
    }

    function getCurveMidpointFromCoords(startCoord, endCoord) {
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
    }

    function getVectorDegrees(start, end) {
      const dx = end[0] - start[0];
      const dy = end[1] - start[1];
      return Math.atan2(dy, dx) * (180 / Math.PI);
    }

    Vue.onMounted(() => {
      initMap();
    });
    Vue.onUnmounted(() => {
      map?.remove?.()
    });

    Vue.watch(() => props.modelValue, (val, old) => {
      if (val?.length || val !== old) {
        locations.value = val;
        fitMarkers();
      }
      if (val.length === 0) {
        map.value.setView([lat.value, lng.value]);
      }
    });

    // Watch for changes in `locations`
    Vue.watch(locations, () => {
      emit('update:modelValue', locations.value);
    });

    return {
      translations,
      mapId,
      mapHeight
    }
  },

  template: `
      <div>
        <v-card  variant="flat">

          <v-card-text>
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

            <div :id="mapId" :style="'resize:vertical;height:'+ mapHeight + 'px'"></div>


          </v-card-text>
        </v-card>
      </div>
    `,
});
