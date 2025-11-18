const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: "/admin/api/flowmap/visualize" },
    statusEndpoint:    { type: String, default: "/admin/api/flowmap/status" },
    dataEndpoint:      { type: String, default: "/admin/api/flowmap/data" },
    query: { type: Array, default: () => [{}] },
  },

  emits: ["update:open", "advancedSearch"],

  data: () => ({
    translations: window.translations,

    loading: false,
    loadingMessage: "",
    errorMessage: "",

    locations: [],
    flows: [],

    sheetStyle: {
      position: "relative",
      width: "100%",
      height: "calc(100vh - 64px)", // subtract toolbar height
      overflow: "hidden"
    },
  }),

  watch: {
    open(val) {
      if (val) this.initMapFlow();
    }
  },

  methods: {
    /* -------------------------------------------------
       API ORCHESTRATION
    ------------------------------------------------- */
    async initMapFlow() {
      this.loading = true;
      this.errorMessage = "";
      this.loadingMessage = this.translations.preparingMap_ ?? "Preparing map...";

      const result = await this.fetchData();

      if (this.errorMessage) {
        this.loading = false;
        return;
      }

      this.locations = result.locations;
      this.flows = result.flows;

      this.loading = false;
    },

    async fetchData() {
      this.loading = true;
      this.loadingMessage = this.translations.startingGeneration_ ?? "Starting…";

      try {
        const start = await api.post(this.visualizeEndpoint, { q: this.query });
        const taskId = start?.data?.task_id;

        if (!taskId) throw new Error("Flowmap generation failed.");

        let status = "pending";
        let error = null;

        while (status === "pending") {
          const res = await api.get(this.statusEndpoint);
          status = res?.data?.status;
          error = res?.data?.error;

          if (status === "pending") {
            this.loadingMessage = this.translations.waitingForMapGeneration_ ?? "Processing…";
            await new Promise(r => setTimeout(r, 1500));
          }
        }

        if (status === "error") throw new Error(error || "Map generation error.");

        this.loadingMessage = this.translations.fetchingVisualizationData_ ?? "Loading data…";

        const dataRes = await api.get(this.dataEndpoint);

        return {
          locations: Array.isArray(dataRes.data?.locations) ? dataRes.data.locations : [],
          flows: Array.isArray(dataRes.data?.flows) ? dataRes.data.flows : [],
        };

      } catch (err) {
        console.error(err);
        this.errorMessage = err.message || "Something went wrong";
        return { locations: [], flows: [] };
      } finally {
        this.loading = false;
      }
    },

    retry() {
      this.errorMessage = "";
      this.initMapFlow();
    }
  },

  template: `
    <v-dialog fullscreen :model-value="open">
      <v-toolbar color="primary" dark>
        <v-toolbar-title>{{ translations.mapVisualization_ }}</v-toolbar-title>
        <v-spacer></v-spacer>

        <v-btn prepend-icon="mdi-ballot"
               variant="elevated"
               @click="$emit('advancedSearch')">
          Advanced search
        </v-btn>

        <v-btn icon="mdi-close"
               @click="$emit('update:open', false)"></v-btn>
      </v-toolbar>

      <div :style="sheetStyle">
        
        <!--  MAP  -->
        <flowmap
          v-if="!loading && !errorMessage"
          :locations="locations"
          :flows="flows"
          style="width:100%; height:100%;"
        />

        <!-- LOADING OVERLAY -->
        <v-overlay
          v-model="loading"
          persistent
          class="d-flex align-center justify-center"
          :content-class="'d-flex flex-column align-center justify-center'"
        >
          <v-progress-circular
            indeterminate
            color="primary"
            size="64"
          />
          <div style="margin-top:16px; font-size:17px;">
            {{ loadingMessage }}
          </div>
        </v-overlay>

        <!-- ERROR -->
        <v-container v-if="errorMessage" style="height:100%; display:flex; align-items:center; justify-content:center;">
          <v-card style="padding:32px; text-align:center;">
            <v-icon color="error" size="64">mdi-alert-circle-outline</v-icon>
            <div style="margin-top:12px; font-size:18px;">{{ errorMessage }}</div>
            <v-btn color="primary" style="margin-top:16px;" @click="retry">
              Retry
            </v-btn>
          </v-card>
        </v-container>

</div>
    </v-dialog>
  `,
});
