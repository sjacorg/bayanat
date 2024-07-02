const ExportDownload = Vue.defineComponent({
  props: {
    item: {},
    i18n: {},
  },
  data: function () {
    return {
      timer: null,
    };
  },

  watch: {
    item: function (val) {
      this.setupInterval();
    },
  },

  mounted: function () {
    this.setupInterval();
    console.log(this.i18n)
  },

  methods: {
    setupInterval() {
      if (this.item.status === 'Processing' && !this.timer) {
        const splitInterval = Math.random() * 5 + 3;
        this.timer = setInterval(this.checkStatus, splitInterval * 1000);
      }
    },

    checkStatus() {
      if (this.item.status === 'Ready') {
        clearInterval(this.timer);
        this.timer = null;
        this.$root.refresh();
        return;
      }
      axios
        .get(`/export/api/export/${this.item.id}`)
        .then((response) => {
          this.item = response.data;
        })
        .catch((error) => {
          console.log(error);
        })
        .finally(() => {
          // Handle finally case if needed
        });
    },
  },
  template: `

          <div>
            <v-progress-circular v-if="item.status === 'Processing'"
                                 indeterminate
                                 :size="16"
                                 width="2"
                                 color="primary"
            ></v-progress-circular>
            <v-tooltip :text="item.status">
            <template #activator="{props}">
            <v-icon 
                    v-if="item.status==='Pending'">mdi-clock-time-eleven-outline v-bind="props"
            </v-icon>

            <v-icon 
                    v-if="item.status==='Rejected'" color="error">mdi-cancel v-bind="props"
            </v-icon>
            <v-icon 
                    v-if="item.status==='Failed'" color="error">mdi-alert-circle v-bind="props"
            </v-icon>
            <v-icon 
                    v-if="item.status==='Expired'"
                    color="grey">mdi-close-circle
                    v-bind="props"
            </v-icon>
            </template>
            </v-tooltip>
            <v-tooltip location="top" :text="i18n.download_">
            <template #activator="{props}">
            <v-btn @click.stop="" 
                  v-bind="props"
                   variant="text"
                   download 
                   :href="'/export/api/exports/download?exportId=' + encodeURIComponent(this.item.uid)"
                   v-if="item.status === 'Ready'" icon="mdi-download-circle" color="success">

              
            </v-btn>
            </template>
            </v-tooltip>


      </div>

    `,
});
