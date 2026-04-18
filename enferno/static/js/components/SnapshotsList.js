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
        Pre-update Snapshots
        <v-spacer />
        <v-btn icon="mdi-refresh" variant="text" @click="load" :loading="loading"></v-btn>
      </v-card-title>
      <v-card-text>
        <v-alert type="info" variant="tonal" density="compact" class="mb-3">
          Restore is CLI-only for safety. SSH to the server and run
          <code>sudo bayanat restore &lt;name&gt;</code> (needs root; it stops
          services, runs <code>pg_restore</code>, and starts services again).
        </v-alert>
        <v-data-table
          :items="items"
          :headers="[
            { title: 'Name', key: 'name' },
            { title: 'Size', key: 'size' },
            { title: 'Age', key: 'age' }
          ]"
          :loading="loading"
          no-data-text="No snapshots available yet."
        ></v-data-table>
      </v-card-text>
    </v-card>
  `,
});
