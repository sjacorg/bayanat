const GeoMap = Vue.defineComponent({
  mixins: [globalMixin],
  props: {
    title: String,
    modelValue: Object,
    mapHeight: {
      type: Number,
      default: 300,
    },
    mapZoom: {
      type: Number,
      default: 10,
    },
    editMode: {
      type: Boolean,
      default: true,
    },
    radiusControls: {
      type: Boolean,
      default: false,
    },
    others: {
      type: Array,
      default: () => [],
    },
  },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    const translations = window.translations
    const mapId = 'map-' + Vue.getCurrentInstance().uid
    const map = Vue.shallowRef(null)
    const lat = Vue.ref(geoMapDefaultCenter.lat)
    const lng = Vue.ref(geoMapDefaultCenter.lng)
    const radius = Vue.ref(props.modelValue?.radius || 1000)
    const marker = Vue.shallowRef(null)
    const attribution = '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    const googleAttribution = '&copy; <a href="https://www.google.com/maps">Google Maps</a>, Imagery ©2025 Google, Maxar Technologies'
    const radiusCircle = Vue.ref(null)

    const mapStyle = Vue.computed(() => ({
      height: props.mapHeight + 'px',
      width: '100%',
    }));
    const mapCenter = Vue.computed({
      get() {
        if (lat.value && lng.value) {
          return [lat.value, lng.value];
        }
        return geoMapDefaultCenter;
      },
      set() {
        emitValue();
      },
    })
    const additionalMarkers = Vue.computed(() => {
      return props.others && props.modelValue
        ? props.others.filter(
          (other) => other.lat !== props.modelValue.lat || other.lng !== props.modelValue.lng,
        )
        : [];
    });

    function initMap() {
      // Create the map instance
      map.value = L.map(mapId, {
        center: mapCenter.value,
        zoom: 13,
        scrollWheelZoom: false,
      });

      // Define the OpenStreetMap tile layer
      const osmLayer = L.tileLayer(mapsApiEndpoint, {
        attribution: attribution,
      }).addTo(map.value); // Add as the default layer

      // Define the Google Maps satellite tile layer
      const googleLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
        attribution: googleAttribution,
        maxZoom: 20,
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
      });

      // Add the fullscreen control
      map.value.addControl(
        new L.Control.Fullscreen({
          title: {
            false: translations.enterFullscreen_,
            true: translations.exitFullscreen_,
          },
        }),
      );

      // Add a layer control for toggling between OSM and Google Maps
      const baseMaps = {
        'OpenStreetMap': osmLayer,
        'Google Satellite': googleLayer,
      };

      if (window.__GOOGLE_MAPS_API_KEY__) {
        L.control.layers(baseMaps).addTo(map.value);
      }

      // Add a click event listener to the map for marker setting
      map.value.on('click', setMarker);

      // Update the map with initial lat, lng, and radius
      updateMap();

      // Ensure the map size adjusts to window resizing for responsive behavior
      const resizeListener = () => fixMap();
      window.addEventListener('resize', resizeListener);

      // Immediately adjust map size to fit container
      fixMap();
    }

    function addAdditionalMarkers() {
      additionalMarkers.value.forEach((marker) => {
        L.marker([marker.lat, marker.lng], {
          draggable: false,
          opacity: 0.4,
        }).addTo(map.value);
      });
    }

    function updateMap() {
      if (lat.value && lng.value && map.value) {
        map.value.setView([lat.value, lng.value]);
        setMarker({ latlng: { lat: lat.value, lng: lng.value } });
      } else {
        clearMarker();
      }
    }

    function updateRadiusCircle() {
      if (props.radiusControls && lat.value && lng.value) {
        if (radiusCircle.value) {
          map.value.removeLayer(radiusCircle.value);
        }
        radiusCircle.value = L.circle([lat.value, lng.value], {
          radius: radius.value,
        });
        map.value.addLayer(radiusCircle.value); // Add this line
        debounce(() => {
          if (radiusCircle.value) {
            const bounds = radiusCircle.value.getBounds();
            map.value.fitBounds(bounds);
          }
        }, 250)();
      } else {
        clearRadiusCircle();
      }
    }

    function fixMap() {
      Vue.nextTick(() => map.value?.invalidateSize?.());
    }

    function clearMarker() {
      if (marker.value) {
        map.value.removeLayer(marker.value);
        marker.value = null; // Clear the reference
      }
      if (radiusCircle.value) {
        map.value.removeLayer(radiusCircle.value);
        radiusCircle.value = null;
      }
      // Reset lat, lng
      lat.value = null;
      lng.value = null;
    }

    function setMarker(evt) {
      if (props.editMode) {
        // Clear existing marker
        if (marker.value) {
          clearMarker();
        }

        // Set new marker
        const { lat: latitude, lng: longitude } = evt.latlng;
        setOrUpdateMarker(latitude, longitude);
        updateRadiusCircle(); // Add this line

        emitValue();
      }
    }

    function setOrUpdateMarker(latitude, longitude) {
      // Clear existing marker
      if (marker.value) {
        map.value.removeLayer(marker.value);
      }

      // Update lat and lng
      lat.value = latitude;
      lng.value = longitude;

      // Set new marker
      marker.value = L.marker([latitude, longitude]).addTo(map.value);
    }

    function clearRadiusCircle() {
      if (radiusCircle.value) {
        map.value.removeLayer(radiusCircle.value);
        radiusCircle.value = null;
      }
    }

    
    function clearAddRadiusCircle() {
      if (!props.radiusControls) {
        return;
      }

      // Remove existing radius circle if it exists
      if (radiusCircle.value) {
        map.value.removeLayer(radiusCircle.value);
      }

      // If radius is not provided, return
      if (!radius.value) {
        return;
      }

      if (!lat.value || !lng.value) {
        return;
      }
      radiusCircle.value = L.circle([lat.value, lng.value], {
        radius: radius.value,
      }).addTo(map.value);

      debounce(() => {
        const bounds = radiusCircle.value.getBounds();
        map.value.fitBounds(bounds);
      }, 250)();
    }
    
    function emitValue() {
      const newValue =
        lat.value !== null && lng.value !== null
          ? { lat: lat.value, lng: lng.value, radius: radius.value }
          : null;
      emit('update:modelValue', newValue);
    }

    Vue.watch(lat, (newVal, oldVal) => {
      if (newVal !== oldVal) {
        updateMap();
        emitValue();
      }
    });

    // Watch lng changes
    Vue.watch(lng, (newVal, oldVal) => {
      if (newVal !== oldVal) {
        updateMap();
        emitValue();
      }
    });

    // Watch radius changes
    Vue.watch(radius, (newVal, oldVal) => {
      if (newVal !== oldVal) {
        updateRadiusCircle();
        emitValue();
      }
    });

    Vue.watch(() => props.modelValue, (newVal, oldVal) => {
      if (!newVal) {
        lat.value = undefined;
        lng.value = undefined;
        radius.value = 1000; // reset
        return;
      }

      // Update lat if different
      if (newVal.lat !== lat.value) {
        lat.value = newVal.lat;
      }

      // Update lng if different
      if (newVal.lng !== lng.value) {
        lng.value = newVal.lng;
      }

      // Prevent string or negative radius on backend and update radius if different
      if (typeof newVal.radius !== 'string' && newVal.radius >= 0 && newVal.radius !== radius.value) {
        radius.value = newVal.radius;
        clearAddRadiusCircle();
      }
    }, { deep: true, immediate: true });

    Vue.onMounted(() => {
      initMap();
      const { lat: nextLat, lng: nextLng, radius: nextRadius = 1000 } = props.modelValue || {};
      if (nextLat && nextLng) {
        lat.value = nextLat;
        lng.value = nextLng;
        radius.value = nextRadius;
        setOrUpdateMarker(nextLat, nextLng);
        updateRadiusCircle();
        // add additional markers
        addAdditionalMarkers();
      } else {
        // Set default center if lat and lng are not provided
        map.value.setView(geoMapDefaultCenter, 13);
      }
    })

    Vue.onUnmounted(() => {
      map?.remove?.()
    });

    return {
      lat,
      lng,
      clearMarker,
      radius,
      mapId,
      mapStyle
    }
  },
  template: `
      <v-card class="pa-1" elevation="0">
        <v-card-text>
          <h3 v-if="title" class="mb-5">{{ title }}</h3>
          <div v-if="editMode" class="d-flex" style="column-gap: 20px;">
            <v-text-field  type="number" min="-90" max="90" label="Latitude"
                          :rules="[rules.required]"
                          v-model.number="lat"></v-text-field>
            <v-text-field  type="number" min="-180" max="180" label="Longitude"
                          :rules="[rules.required]"
                          v-model.number="lng"></v-text-field>
            <v-btn icon variant="flat" v-if="lat && lng" @click="clearMarker">
              <v-icon>mdi-close</v-icon>
            </v-btn>
          </div>

          <div v-if="editMode && radiusControls" class="mt-1 align-center">
            <v-slider
                :min="100"
                :max="100000"
                :step="100"
                color="primary"
                thumb-label
                track-color="gray lighten-2"
                v-model.number="radius"
                label="Radius (meters)">
              <template v-slot:append>
                <v-text-field
                    readonly
                    variant="solo-filled"
                    style="width: 150px;"
                    v-model.number="radius"
                    suffix="meters"
                    type="number"
                    :rules="[rules.required]"
                    outlined
                    dense>
                </v-text-field>
              </template>
            </v-slider>
          </div>

          <!-- Leaflet Map Container -->
          <div ref="mapContainer"
               :id="mapId"
               class="leaflet-map"
               :style="mapStyle"></div>

        </v-card-text>
      </v-card>


    `,
});
