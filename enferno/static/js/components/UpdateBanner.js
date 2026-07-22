const UpdateBanner = Vue.defineComponent({
  data() {
    return {
      current: null,
      latest: null,
      releaseNotesUrl: null,
      dialog: false,
    };
  },
  computed: {
    hasUpdate() {
      return !!(this.latest && this.current && this.latest !== this.current);
    },
  },
  mounted() {
    this.fetchAvailable();
    this.pollTimer = setInterval(this.fetchAvailable, 6 * 60 * 60 * 1000);
  },
  beforeUnmount() {
    if (this.pollTimer) clearInterval(this.pollTimer);
  },
  methods: {
    async fetchAvailable() {
      try {
        const resp = await axios.get('/admin/api/updates/available');
        const data = resp?.data?.data ?? {};
        this.current = data.current ?? null;
        this.latest = data.latest ?? null;
        this.releaseNotesUrl = data.release_notes_url ?? null;
      } catch (_e) {
        // silent: background poll should never spam the UI
      }
    },
  },
  template: `
    <v-chip
      v-if="hasUpdate"
      color="amber-accent-4"
      variant="elevated"
      prepend-icon="mdi-arrow-up-bold-circle"
      @click="dialog = true"
      class="ms-2 me-2"
    >
      {{ translations.updateAvailable_ }}: {{ latest }}
      <v-dialog v-model="dialog" max-width="520">
        <v-card>
          <v-card-title>{{ translations.updateBayanatTo_ }} {{ latest }}</v-card-title>
          <v-card-text>
            <p>{{ translations.currentVersion_ }}: <strong>{{ current }}</strong></p>
            <p>{{ translations.targetVersion_ }}: <strong>{{ latest }}</strong></p>
            <p v-if="releaseNotesUrl">
              <a :href="releaseNotesUrl" target="_blank" rel="noopener">{{ translations.releaseNotes_ }}</a>
            </p>
            <v-alert type="info" variant="tonal" density="compact" class="mt-3">
              {{ translations.updateCommandInstruction_ }}
              <pre class="mt-2 mb-0"><code>sudo bayanat update {{ latest }}</code></pre>
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="dialog = false">{{ translations.close_ }}</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </v-chip>
  `,
});
