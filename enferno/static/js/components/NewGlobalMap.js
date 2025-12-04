const NewGlobalMap = Vue.defineComponent({
  props: {
    entity: { type: Object, default: () => null },
    entityLoader: { type: Boolean, default: false },
  },

  emits: ['update:open'],

  data: () => ({
    translations: window.translations,
    selectedLocations: [],
  }),

  mounted() {
    this.selectedLocations = this.uniqueEventTypes
  },

  computed: {
    uniqueEventTypes() {
      return [...new Set(this.mapData.locations.flatMap(loc => loc.events.map(event => event.eventType)).filter(Boolean))];
    },
    filteredLocations() {
      // If no filters selected → show all
      if (!this.selectedLocations.length) return this.mapData.locations;

      return this.mapData.locations.filter(loc => {
        // If a location has no events → keep it (same behavior as your original logic)
        if (!loc.events?.length) return true;

        // Keep if ANY of its events matches a selected event type
        return loc.events.some(ev => this.selectedLocations.includes(ev.eventType));
      });
    },
    mapData() {
      const e = this.entity || {};

      if (e.class === 'actor') 
        return MobilityMapUtils.parseEventsToMapData(e.events);

      if (['incident', 'bulletin'].includes(e.class))
        return MobilityMapUtils.parseLocationsToMapData(e.locations);

      // Fallback (smart)
      return Array.isArray(e.events)
        ? MobilityMapUtils.parseEventsToMapData(e.events)
        : MobilityMapUtils.parseLocationsToMapData(e.locations);
    }
  },

  template: `
    <div>
        <v-card variant="flat">
          <v-card-text>
            <div class="d-flex">
              <div class="map-legend d-flex mb-3 align-center" style="column-gap: 10px">
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

            <!-- MAP + OVERLAYS -->
            <v-container fluid class="pa-0 fill-height">
              <!-- MAP -->
              <mobility-map
                ref="mobilityMapRef"
                :locations="filteredLocations"
                :flows="mapData.flows"
                mode="event"
                :min-zoom="0"
                disable-clustering
                :scroll-wheel-zoom="false"
              />

              <!-- LOADING OVERLAY -->
              <v-overlay
                :model-value="entityLoader"
                persistent
                contained
                class="d-flex align-center justify-center"
              >
                <v-card elevation="6" rounded="lg" class="pa-6 text-center">
                  <v-progress-circular
                    indeterminate
                    color="primary"
                    size="64"
                  />
                  <div class="text-subtitle-1 mt-4">
                    {{ translations.preparingMap_ }}
                  </div>
                </v-card>
              </v-overlay>
            </v-container>
          </v-card-text>
        </v-card>
      </div>
  `,
});
