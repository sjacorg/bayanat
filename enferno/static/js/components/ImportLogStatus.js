const ImportLogStatus = Vue.defineComponent({
  props: {
    item: {
      type: Object,
      required: true
    },
  },
  data: function () {
    return {
      translations: window.translations,
      timer: null,
      status: this.item.status,
    };
  },
  mounted() {
    this.startPolling();
  },
  methods: {
    startPolling() {
      if (['Ready', 'Failed'].includes(this.status)) return;
      if (this.timer) return;

      if (this.status === 'Processing' || this.status === 'Pending') {
        this.timer = setInterval(() => {
          api.get(`/import/api/imports/${this.item.id}`)
            .then(response => {
              if (['Ready', 'Failed'].includes(response.data.status)) clearInterval(this.timer);
  
              this.status = response.data.status;
            });
        }, 5000);
      }
    },
  },
  template: `
    <div>
      <v-progress-circular
        v-if="status === 'Processing'"
        indeterminate
        :size="16"
        width="2"
        color="primary"
      ></v-progress-circular>
      <v-tooltip location="top" :text="status" >
        <template #activator="{props}">
          <v-icon v-if="status==='Pending'" icon="mdi-clock-time-eleven-outline" v-bind="props"></v-icon>
          <v-icon v-if="status==='Failed'" icon="mdi-alert-circle" color="error" v-bind="props"></v-icon>
          <v-icon v-if="status==='Ready'" icon="mdi-check-circle" color="success" v-bind="props"></v-icon>
        </template>
      </v-tooltip>
    </div>
  `,
});
