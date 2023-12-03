Vue.component("log-status", {
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
               this.setupInterval();
        },

    },

    mounted: function () {
        this.setupInterval();

    },

    methods: {

        setupInterval() {
            if ((this.item.status === 'Processing' || this.item.status === 'Pending') && !this.timer) {
                const splitInterval = Math.random() * 5 + 3;
                this.timer = setInterval(this.checkStatus, splitInterval * 1000);
            }
        },

        checkStatus() {
            if (this.item.status === 'Ready') {
                    clearInterval(this.timer);
                    return;
            }

            // else
            axios.get(`/import/api/imports/${this.item.id}`).then(response => {
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

            <v-icon v-tippy content="Failed"
                v-if="item.status==='Failed'" color="error">mdi-alert-circle
            </v-icon>

            <v-icon v-tippy content="Ready"
                v-if="item.status==='Ready'" color="success">mdi-check-circle
            </v-icon>
          </div>
        `,
});
