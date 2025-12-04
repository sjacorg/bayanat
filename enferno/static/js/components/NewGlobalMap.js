const NewGlobalMap = Vue.defineComponent({
  props: {
    entity: { type: Object, default: () => null },
    entityLoader: { type: Boolean, default: false },
  },

  emits: ['update:open'],

  data: () => ({
    translations: window.translations,
  }),

  computed: {
    mapData() {
      return MobilityMapUtils.parseEventsToMapData(this.entity?.events);
    },
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

              <!-- <v-menu v-if="uniqueEventTypes.length > 1" :close-on-content-click="false">
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
              </v-menu> -->
            </div>

            <!-- MAP + OVERLAYS -->
            <v-container fluid class="pa-0 fill-height">
              <!-- MAP -->
              <mobility-map
                ref="mobilityMapRef"
                :locations="mapData?.locations"
                :flows="mapData?.flows"
                :mode="'event'"
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
