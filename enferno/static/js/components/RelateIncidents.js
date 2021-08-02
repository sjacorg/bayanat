Vue.component('relate-incidents', {
    props: ['value', 'show', 'exids', 'i18n'],
    data: () => {
        return {
            q: {},
            loading: true,
            results: [],
            visible: false,
            page: 1,
            perPage: 10,
            total: 0,
            moreItems: false,
            incident: null,
            showIncident: false

        }

    }
    ,
    mounted() {

    },


    watch: {

        results: {
            handler(val, old) {

            },
            deep: true
        },

        value: function (val) {

            this.$emit('input', val);
        }
    },

    methods: {

        viewIncident(i) {
            axios.get(`/admin/api/incident/${i.id}`).then(response => {
                console.log(response.data);
                this.incident = response.data;
                this.showIncident = true;


            }).catch(error => {
                this.showIncident = false;
                this.showSnack('Oops! We couldn\'t find this item.')

            });
        },


        open() {
            this.visible = true;

        },
        close() {
            this.visible = false
        },
        reSearch() {
            this.page = 1;
            this.results = [];
            this.search();

        },

        search(q = {}) {
            this.loading = true;
            axios.post(`/admin/api/incidents/?page=${this.page}&per_page=${this.perPage}&mode=2`, {q: this.q}).then(response => {
                this.exids = this.exids || [];
                this.loading = false;
                this.total = response.data.total;

                this.results = this.results.concat(response.data.items.filter(x => !this.exids.includes(x.id)));


                if (this.page * this.perPage >= this.total) {
                    this.moreItems = false;
                } else {
                    this.moreItems = true;
                }
            }).catch(err => {
                this.loading = false;
                console.log(err.response.data);
            });


        },
        loadMore() {
            this.page += 1;
            this.search()
        },
        relateItem(item) {
            this.results.removeById(item.id);
            this.$emit('relate', item);

        }

    },


    template: `
      <v-dialog v-model="visible" max-width="1220">
      <v-sheet>

        <v-container class="fluid fill-height">
          <v-row>
            <v-col cols="12" md="4">
              <v-card outlined>
                <incident-search-box v-model="q" @search="reSearch" :i18n="$root.translations"></incident-search-box>
              </v-card>
            </v-col>
            <v-col cols="12" md="8">

              <v-card :loading="loading">

                <v-card-title class="handle">
                  {{ i18n.advSearch_ }}
                  <v-spacer></v-spacer>
                  <v-btn @click="visible=false" small text fab>
                    <v-icon>mdi-close</v-icon>
                  </v-btn>
                </v-card-title>

                <v-divider></v-divider>

                <v-card-text v-if="loading" class="d-flex pa-5" justify-center align-center>
                  <v-progress-circular class="ma-auto" indeterminate
                                       color="primary"></v-progress-circular>
                </v-card-text>


                <v-card class="pa-2" tile color="grey lighten-4">

                  <incident-result :i18n="i18n" v-for="(item, i) in results" :key="i" :incident="item" :show-hide="true">
                    <template v-slot:actions>
                      <v-btn @click="relateItem(item)" small depressed color="primary">{{ i18n.relate_ }}
                      </v-btn>
                    </template>
                  </incident-result>
                </v-card>

                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn icon @click="loadMore" v-if="moreItems" color="third">
                    <v-icon>mdi-dots-horizontal</v-icon>
                  </v-btn>
                  <v-sheet small v-else class="heading" color=" grey--text"> {{ i18n.noResults_ }} </v-sheet>
                  <v-spacer></v-spacer>
                </v-card-actions>
              </v-card>
            </v-col>

          </v-row>
        </v-container>


        <v-dialog v-model="showIncident" max-width="550">
          <v-sheet>
            <div class="d-flex justify-end">
              <v-btn @click="showIncident=false" small text fab right="10">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </div>
            <incident-card :incident="incident"></incident-card>
          </v-sheet>
        </v-dialog>


      </v-sheet>


      </v-dialog>

    `
})