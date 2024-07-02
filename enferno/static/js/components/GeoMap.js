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

  computed: {
    mapStyle() {
      return {
        height: this.mapHeight + 'px',
        width: '100%',
      };
    },

    mapCenter: {
      get() {
        if (this.lat && this.lng) {
          return [this.lat, this.lng];
        }
        return geoMapDefaultCenter;
      },
      set(value) {
        [this.lat, this.lng] = value;
        this.emitValue();
      },
    },

    additionalMarkers() {
      return this.others && this.modelValue
        ? this.others.filter(
            ({ lat, lng }) => lat !== this.modelValue.lat || lng !== this.modelValue.lng,
          )
        : [];
    },
  },

  data: function () {
    return {
      mapId: 'map-' + this.$.uid,
      map: null,
      mapKey: 0,
      lat: this.modelValue?.lat,
      lng: this.modelValue?.lng,
      radius: this.modelValue?.radius || 1000,
      marker: null,
      subdomains: null,
      mapsApiEndpoint: mapsApiEndpoint,

      location: null,
      attribution:
        '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      osmAttribution:
        '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',

      defaultTile: true,
      satellite: null,

      radiusCircle: null,
    };
  },

  watch: {
    lat(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.updateMap();
        this.emitValue();
      }
    },
    lng(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.updateMap();
        this.emitValue();
      }
    },
    radius(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.updateRadiusCircle();
        this.emitValue();
      }
    },
      modelValue: {
        deep: true,
        immediate: true,
        handler(newVal, oldVal) {
          if (!newVal) {
            this.lat = undefined;
            this.lng = undefined;
            this.radius = 1000; // reset
            return;
          }

          // Update lat if different
          if (newVal.lat !== this.lat) {
            this.lat = newVal.lat;
          }

          // Update lng if different
          if (newVal.lng !== this.lng) {
            this.lng = newVal.lng;
          }

          // Prevent string or negative radius on backend and update radius if different
          if (typeof newVal.radius !== 'string' && newVal.radius >= 0 && newVal.radius !== this.radius) {
            this.radius = newVal.radius;
            this.clearAddRadiusCircle();
          }
        },
      }

  },

  mounted() {
    this.initMap();
    const { lat, lng, radius = 1000 } = this.modelValue || {};
    if (lat && lng) {
      this.lat = lat;
      this.lng = lng;
      this.radius = radius;
      this.setOrUpdateMarker(lat, lng);
      this.updateRadiusCircle();
      // add additional markers
      this.addAdditionalMarkers();
    } else {
      // Set default center if lat and lng are not provided
      this.map.setView(geoMapDefaultCenter, 13);
    }
  },

  // clean up resize event listener

  methods: {
    initMap() {
      // Create the map instance
      this.map = L.map(this.mapId, {
        center: this.mapCenter,
        zoom: 13,
        scrollWheelZoom: false,
      });

      // Add the OpenStreetMap tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(this.map);

      // Add the fullscreen control with improved readability
      this.map.addControl(
        new L.Control.Fullscreen({
          title: {
            false: this.$root.translations.enterFullscreen_,
            true: this.$root.translations.exitFullscreen_,
          },
        }),
      );

      // Initialize the satellite layer (optional: specify options if needed)
      this.satellite = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');

      // Add a click event listener to the map for marker setting
      this.map.on('click', this.setMarker);

      // Update the map with initial lat, lng, and radius
      this.updateMap();

      // Ensure the map size adjusts to window resizing for responsive behavior
      const resizeListener = () => this.fixMap();
      window.addEventListener('resize', resizeListener);

      // Immediately adjust map size to fit container
      this.fixMap();
    },
    addAdditionalMarkers() {
      this.additionalMarkers.forEach((marker) => {
        L.marker([marker.lat, marker.lng], {
          draggable: false,
          opacity: 0.4,
        }).addTo(this.map);
      });
    },

    updateMap() {
      if (this.lat && this.lng && this.map) {
        this.map.setView([this.lat, this.lng]);
        this.setMarker({ latlng: { lat: this.lat, lng: this.lng } });
      } else {
        this.clearMarker();
      }
    },

    updateRadiusCircle() {
      if (this.radiusControls && this.lat && this.lng) {
        if (this.radiusCircle) {
          this.map.removeLayer(this.radiusCircle);
        }
        this.radiusCircle = L.circle([this.lat, this.lng], {
          radius: this.radius,
        });
        this.map.addLayer(this.radiusCircle); // Add this line
        debounce(() => {
          if (this.radiusCircle) {
            const bounds = this.radiusCircle.getBounds();
            this.map.fitBounds(bounds);
          }
        }, 250)();
      } else {
        this.clearRadiusCircle();
      }
    },

    fixMap() {
      this.$nextTick(() => {
        if (this.map) {
          this.map.invalidateSize();
        }

        if (!this.tileLayer) {
          this.tileLayer = L.tileLayer(this.mapsApiEndpoint, {
            attribution: this.attribution,
          }).addTo(this.map);

          this.tileLayer.on('error', function (error) {
            console.error('Tile layer error:', error);
          });
        }
      });
    },

    toggleSatellite() {
      if (!this.satellite) {
        // Initialize the satellite layer once and reuse it
        this.satellite = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution:
            '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        });
      }

      if (this.defaultTile) {
        this.map.addLayer(this.satellite);
        this.defaultTile = false;
      } else {
        this.map.removeLayer(this.satellite);
        this.defaultTile = true;
      }
    },

    clearMarker() {
      if (this.marker) {
        this.map.removeLayer(this.marker);
        this.marker = null; // Clear the reference
      }
      if (this.radiusCircle) {
        this.map.removeLayer(this.radiusCircle);
        this.radiusCircle = null;
      }
      // Reset lat, lng
      this.lat = null;
      this.lng = null;
    },

    setMarker(evt) {
      if (this.editMode) {
        // Clear existing marker
        if (this.marker) {
          this.clearMarker();
        }

        // Set new marker
        const { lat, lng } = evt.latlng;
        this.setOrUpdateMarker(lat, lng);
        this.updateRadiusCircle(); // Add this line

        this.broadcast();
      }
    },

    setOrUpdateMarker(lat, lng) {
      // Clear existing marker
      if (this.marker) {
        this.map.removeLayer(this.marker);
      }

      // Update lat and lng
      this.lat = lat;
      this.lng = lng;
      // Set new marker
      this.marker = L.marker([lat, lng]).addTo(this.map);
    },

    clearRadiusCircle() {
      if (this.radiusCircle) {
        this.map.removeLayer(this.radiusCircle);
        this.radiusCircle = null;
      }
    },

    emitValue() {
      const newValue =
        this.lat !== null && this.lng !== null
          ? { lat: this.lat, lng: this.lng, radius: this.radius }
          : null;
      this.$emit('update:modelValue', newValue);
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
        radius: this.radius,
      }).addTo(this.map);

      debounce(() => {
        const bounds = this.radiusCircle.getBounds();
        this.map.fitBounds(bounds);
      }, 250)();
    },

    broadcast() {
      const newValue =
        this.lat !== null && this.lng !== null
          ? { lat: this.lat, lng: this.lng, radius: this.radius }
          : null;
      this.$emit('update:modelValue', newValue);
    },
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
