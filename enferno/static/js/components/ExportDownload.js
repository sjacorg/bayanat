const ExportDownload = Vue.defineComponent({
  props: {
    item: {},
  },
  data() {
    return {
      translations: window.translations,
      timer: null,
      status: this.item.status,
    };
  },

  watch: {
    'item.status'(newStatus) {
      this.status = newStatus;
      this.setupInterval();
    }
  },

  mounted() {
    this.setupInterval();
  },

  methods: {
    setupInterval() {
      if (this.status === 'Processing' && !this.timer) {
        const splitInterval = Math.random() * 5 + 3;
        this.timer = setInterval(this.checkStatus, splitInterval * 1000);
      }
    },

    checkStatus() {
      if (this.status === 'Ready') {
        clearInterval(this.timer);
        this.timer = null;
        this.$root.refresh();
        return;
      }
      axios
        .get(`/export/api/export/${this.item.id}`)
        .then((response) => {
          this.status = response.data.status;
        });
    },
  },
  template: `

          <div>
            <v-progress-circular v-if="status === 'Processing'"
                                 indeterminate
                                 :size="16"
                                 width="2"
                                 color="primary"
            ></v-progress-circular>
            <v-tooltip :text="status">
            <template #activator="{props}">
            <v-icon 
                    v-if="status==='Pending'">mdi-clock-time-eleven-outline v-bind="props"
            </v-icon>

            <v-icon 
                    v-if="status==='Rejected'" color="error">mdi-cancel v-bind="props"
            </v-icon>
            <v-icon 
                    v-if="status==='Failed'" color="error">mdi-alert-circle v-bind="props"
            </v-icon>
            <v-icon 
                    v-if="status==='Expired'"
                    color="grey">mdi-close-circle
                    v-bind="props"
            </v-icon>
            </template>
            </v-tooltip>
            <v-tooltip location="top" :text="translations.download_">
            <template #activator="{props}">
            <v-btn @click.stop="" 
                  v-bind="props"
                   variant="text"
                   download 
                   :href="'/export/api/exports/download?exportId=' + encodeURIComponent(this.item.uid)"
                   v-if="status === 'Ready'" icon="mdi-download-circle" color="success">

              
            </v-btn>
            </template>
            </v-tooltip>


      </div>

    `,
});

window.ExportDownload = ExportDownload;
