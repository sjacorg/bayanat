const UpdateProgressDialog = Vue.defineComponent({
  data() {
    return {
      open_: false,
      state: null,
      timer: null,
    };
  },
  methods: {
    open() {
      this.open_ = true;
      this.poll();
    },
    close() {
      this.open_ = false;
      if (this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
    },
    async poll() {
      await this.fetchState();
      if (this.timer) clearInterval(this.timer);
      this.timer = setInterval(this.fetchState, 2000);
    },
    async fetchState() {
      try {
        const resp = await axios.get('/admin/api/updates/status');
        const data = resp?.data?.data ?? {};
        this.state = data;
        if (!data.running) {
          if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
          }
        }
      } catch (_e) {
        // tolerate transient errors; dialog stays visible
      }
    },
    phaseColor() {
      const phase = (this.state && this.state.phase) || 'IDLE';
      if (phase === 'SUCCESS') return 'success';
      if (phase === 'ROLLED_BACK') return 'warning';
      if (phase === 'NEEDS_INTERVENTION') return 'error';
      return 'primary';
    },
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer);
  },
  template: `
    <v-dialog v-model="open_" max-width="520" persistent>
      <v-card v-if="state">
        <v-card-title>
          <v-icon :color="phaseColor()" class="me-2">mdi-autorenew</v-icon>
          {{ state.phase_label || state.phase }}
        </v-card-title>
        <v-card-text>
          <p v-if="state.target"><strong>Target:</strong> {{ state.target }}</p>
          <p v-if="state.previous"><strong>Previous:</strong> {{ state.previous }}</p>
          <v-progress-linear
            v-if="state.running"
            indeterminate
            :color="phaseColor()"
            class="my-3"
          />
          <p v-if="state.progress_text" class="text-body-2">
            {{ state.progress_text }}
          </p>
          <v-alert
            v-if="state.error"
            type="error"
            variant="tonal"
            density="compact"
            class="mt-2"
          >
            {{ state.error }}
          </v-alert>
          <v-alert
            v-if="state.phase === 'NEEDS_INTERVENTION'"
            type="error"
            variant="tonal"
            class="mt-2"
          >
            Operator intervention required. Snapshot:
            <code>{{ state.snapshot }}</code>. See the update runbook for
            recovery steps.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="close" :disabled="state.running">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  `,
});
