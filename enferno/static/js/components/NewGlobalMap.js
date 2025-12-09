const NewGlobalMap = Vue.defineComponent({
  props: {
    entities: { type: Array, default: () => [] },
    entityLoader: { type: Boolean, default: false },
  },

  emits: ['update:open'],

  data: () => ({
    translations: window.translations,
    selectedEventTypes: [],
  }),

  mounted() {
    // Pre-select all event types by default
    this.selectedEventTypes = this.uniqueEventTypes;
  },

  computed: {
    /* =========================================================
        1️⃣ Merge all entities into a single mapData object
       ========================================================= */
    mapData() {
      const allLocations = [];
      const allFlows = [];

      for (const e of this.entities) {
        if (!e) continue;

        const opts = {
          showParentId: Boolean(e?.showParentId),
          parentId: e?.parentId ?? e?.id ?? null,
        };

        // 1️⃣ Parse events (events → locations + flows)
        if (Array.isArray(e.events)) {
          const parsed = MobilityMapUtils.parseEventsToMapData(e.events, opts);
          allLocations.push(...parsed.locations);
          allFlows.push(...parsed.flows);
        }

        // 2️⃣ Parse locations (pure locations → no flows)
        if (Array.isArray(e.locations)) {
          const parsed = MobilityMapUtils.parseLocationsToMapData(e.locations, opts);
          allLocations.push(...parsed.locations);
        }

        // 3️⃣ NEW: GEO LOCATIONS
        if (Array.isArray(e.geoLocations)) {
          const parsed = MobilityMapUtils.parseGeoLocationsToMapData(e.geoLocations, opts);
          allLocations.push(...parsed.locations);
        }
      }

      // Ensure unique numeric IDs for the map.
      // (Different sources can overlap → missing/merged markers)
      // 1) Build id map
      const idMap = new Map();
      allLocations.forEach((loc, index) => {
        const oldId = loc.id;
        const newId = index + 1;
        idMap.set(oldId, newId);
        loc.id = newId;
      });

      // 2) Remap flows to the new IDs
      allFlows.forEach(flow => {
        if (idMap.has(flow.origin)) flow.origin = idMap.get(flow.origin);
        if (idMap.has(flow.dest))   flow.dest   = idMap.get(flow.dest);

        if (idMap.has(flow.from)) flow.from = idMap.get(flow.from);
        if (idMap.has(flow.to))   flow.to   = idMap.get(flow.to);

        if (idMap.has(flow.fromKey)) flow.fromKey = idMap.get(flow.fromKey);
        if (idMap.has(flow.toKey))   flow.toKey   = idMap.get(flow.toKey);
      });

      return { locations: allLocations, flows: allFlows };
    },

    /* =========================================================
        2️⃣ Extract unique event types from *all* merged locations
       ========================================================= */
    uniqueEventTypes() {
      return [...new Set(
        this.mapData.locations.flatMap(loc =>
          (loc.events || []).map(ev => ev.eventType)
        ).filter(Boolean)
      )];
    },

    /* =========================================================
        3️⃣ Filter locations based on selected event types
       ========================================================= */
    filteredLocations() {
      if (!this.selectedEventTypes.length) return this.mapData.locations;

      return this.mapData.locations.filter(loc => {
        // Locations without events (geo markers) ALWAYS visible
        if (!loc.events?.length) return true;

        return loc.events.some(ev => this.selectedEventTypes.includes(ev.eventType));
      });
    },
  },

  /* =========================================================
      4️⃣ FINAL TEMPLATE
     ========================================================= */
  template: `
    <div>
      <v-card variant="flat">
        <v-card-text>

          <!-- LEGEND & FILTER BUTTON -->
          <div class="d-flex">
            <div class="map-legend d-flex mb-3 align-center" style="column-gap: 10px">
              <div class="caption">
                <v-icon small color="#00a1f1">mdi-checkbox-blank-circle</v-icon>
                {{ translations.locations_ }}
              </div>
              <div class="caption">
                <v-icon small color="#ffbb00">mdi-checkbox-blank-circle</v-icon>
                {{ translations.geoMarkers_ }}
              </div>
              <div class="caption">
                <v-icon small color="#257e74">mdi-checkbox-blank-circle</v-icon>
                {{ translations.events_ }}
              </div>
            </div>

            <!-- EVENT TYPE FILTER -->
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

              <v-list v-model:selected="selectedEventTypes" select-strategy="leaf">
                <v-list-item
                  v-for="(eventType, index) in uniqueEventTypes"
                  :key="index"
                  :title="eventType"
                  :value="eventType"
                >
                  <template v-slot:prepend="{ isSelected, select }">
                    <v-list-item-action start>
                      <v-checkbox-btn :model-value="isSelected" @update:model-value="select" />
                    </v-list-item-action>
                  </template>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>

          <!-- MAP -->
          <v-container fluid class="pa-0 fill-height">
            <mobility-map
              ref="mobilityMapRef"
              :locations="filteredLocations"
              :flows="mapData.flows"
              mode="event"
              :min-zoom="0"
              :scroll-wheel-zoom="false"
              :click-to-zoom-cluster="true"
            />

            <!-- LOADER -->
            <v-overlay
              :model-value="entityLoader"
              persistent
              contained
              class="d-flex align-center justify-center"
            >
              <v-card elevation="6" rounded="lg" class="pa-6 text-center">
                <v-progress-circular indeterminate color="primary" size="64" />
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
