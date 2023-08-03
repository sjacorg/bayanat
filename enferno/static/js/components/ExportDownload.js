Vue.component("export-download", {
    props: {
        item: {},
        i18n: {}
    },
    data: function () {
        return {

            timer: null,

        };
    },

    watch: {
        item: function (val) {

            

            if (this.item.status === 'Processing') {

                const splitInterval = Math.random() * 5 + 3;
                // set timer only once
                if (!this.timer){
                    this.timer = setInterval(this.checkStatus, splitInterval * 1000)
                }



            }

        },


    },

    mounted: function () {


    },

    methods: {

        checkStatus() {
            if (this.item.status === 'Ready') {

                    clearInterval(this.timer);
                    this.$root.refresh();
                    return;
            }
            // else
            axios.get(`/export/api/export/${this.item.id}`).then(response => {
                this.item = response.data;
            }).catch(error => {
                console.log(error);
            }).finally(() => {

            });
        }

    },
    template:
        `
          <div>
          <v-progress-circular v-if="item.status === 'Processing'"
                               indeterminate
                               :size="16"
                               width="2"
                               color="primary"
          ></v-progress-circular>

          <v-icon v-tippy content="Pending"
                  v-if="item.status==='Pending'">mdi-clock-time-eleven-outline
          </v-icon>
          <v-icon v-tippy content="Not Approved"
                  v-if="item.status==='Rejected'" color="error">mdi-cancel
          </v-icon>
          <v-icon v-tippy content="Failed"
                  v-if="item.status==='Failed'" color="error">mdi-alert-circle
          </v-icon>
          <v-icon v-tippy content="Expired"
                  v-if="item.status==='Expired'"
                  color="grey">mdi-close-circle
          </v-icon>

          <v-btn @click.stop="" v-tippy content="Download"
                 download :href="'/export/api/exports/download?exportId=' + encodeURIComponent(this.item.uid)"
                 v-if="item.status === 'Ready'" icon color="success">

            <v-icon>mdi-download-circle</v-icon>
          </v-btn>

          </div>

        `,
});
