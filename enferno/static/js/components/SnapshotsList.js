const SnapshotsList = Vue.defineComponent({
  data() {
    return {
      items: [],
      loading: false,
    };
  },
  mounted() {
    this.load();
  },
  methods: {
    async load() {
      this.loading = true;
      try {
        const resp = await axios.get('/admin/api/snapshots/');
        this.items = resp?.data?.data ?? [];
      } catch (_e) {
        this.items = [];
      } finally {
        this.loading = false;
      }
    },
  },
  template: `
    <v-card>
      <v-card-title>
        {{ translations.preUpdateSnapshots_ }}
        <v-spacer />
        <v-btn icon="mdi-refresh" variant="text" @click="load" :loading="loading"></v-btn>
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" density="compact" class="mb-3">
          {{ translations.restoreIsCliOnly_ }}
          <code>sudo bayanat restore &lt;name&gt;</code>
          ({{ translations.restoreCommandExplanation_ }}).
        </v-alert>
        <v-data-table
          :items="items"
          :headers="[
            { title: translations.snapshotName_, key: 'name' },
            { title: translations.snapshotSize_, key: 'size' },
            { title: translations.snapshotAge_, key: 'age' }
          ]"
          :loading="loading"
          :no-data-text="translations.noSnapshotsAvailable_"
        ></v-data-table>
      </v-card-text>
    </v-card>
  `,
});
