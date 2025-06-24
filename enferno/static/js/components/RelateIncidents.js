const RelateIncidents = Vue.defineComponent({
  props: ['modelValue', 'show', 'exids', 'dialogProps'],
  emits: ['update:modelValue', 'relate'],
  data: () => {
    return {
      translations: window.translations,
      q: {},
      loading: true,
      results: [],
      visible: false,
      page: 1,
      perPage: 10,
      total: 0,
      moreItems: false,
      incident: null,
      showIncident: false,
    };
  },
  watch: {
    modelValue: function (val) {
      this.$emit('update:modelValue', val);
    },
  },

  methods: {
    viewIncident(i) {
      axios
        .get(`/admin/api/incident/${i.id}`)
        .then((response) => {
          console.log(response.data);
          this.incident = response.data;
          this.showIncident = true;
        })
        .catch((error) => {
          this.showIncident = false;
          this.showSnack(translations.notFound_);
        });
    },

    open() {
      this.visible = true;
    },
    close() {
      this.visible = false;
    },
    reSearch() {
      this.page = 1;
      this.results = [];
      this.search();
    },

    search(q = {}) {
      this.loading = true;
      axios
        .post(`/admin/api/incidents/?page=${this.page}&per_page=${this.perPage}&mode=2`, {
          q: this.q,
        })
        .then((response) => {
          this.loading = false;
          this.total = response.data.total;

          // exclude ids of item and related items
          const ex_arr = this.exids || [];
          this.results = this.results.concat(
            response.data.items.filter((x) => !ex_arr.includes(x.id)),
          );

          if (this.page * this.perPage >= this.total) {
            this.moreItems = false;
          } else {
            this.moreItems = true;
          }
        })
        .catch((err) => {
          this.loading = false;
          console.log(err.response.data);
        });
    },
    loadMore() {
      this.page += 1;
      this.search();
    },
    relateItem(item) {
      this.results = this.results.filter(result => result.id !== item.id);
      this.$emit('relate', item);
    },
  },

  template: `
    <v-dialog v-model="visible" v-bind="dialogProps">
      <v-sheet>

        <v-container class="fluid fill-height">
          <v-row>
            <v-col cols="12" lg="6">

              <v-card variant="outlined">
                <incident-search-box 
                  :extra-filters="false" 
                  v-model="q" 
                  search="reSearch">
                </incident-search-box>
              </v-card>

              <v-card  class="text-center">
                <v-card-text>
                  <v-btn color="primary" variant="elevated" @click="reSearch">{{ translations.search_ }}</v-btn>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" lg="6">

              <v-card :loading="loading">

                <v-toolbar>
                  <v-toolbar-title>{{ translations.advSearch_ }}</v-toolbar-title>
                  <v-spacer></v-spacer>
                  <v-btn @click="visible=false" icon="mdi-close"></v-btn>
                </v-toolbar>

                <v-divider></v-divider>

                <v-card-text v-if="loading" class="d-flex pa-5" justify-center align-center>
                  <v-progress-circular class="ma-auto" indeterminate
                                       color="primary"></v-progress-circular>
                </v-card-text>


                <v-card class="pa-2">

                  <incident-result v-for="(item, i) in results" :key="i" :incident="item"
                                   :show-hide="true">
                    <template v-slot:actions>
                      <v-btn variant="elevated" @click="relateItem(item)"  color="primary">{{ translations.relate_ }}
                      </v-btn>
                    </template>
                  </incident-result>
                </v-card>

                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn icon @click="loadMore" v-if="moreItems" color="third">
                    <v-icon>mdi-dots-horizontal</v-icon>
                  </v-btn>
                  <v-sheet small v-else class="heading" color=" grey--text"> {{ translations.noResults_ }}</v-sheet>
                  <v-spacer></v-spacer>
                </v-card-actions>
              </v-card>
            </v-col>
          </v-row>
        </v-container>


        <v-dialog v-model="showIncident" max-width="550">
          <v-sheet>
            <div class="d-flex justify-end">
              <v-btn @click="showIncident=false"  fab right="10">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </div>
            <incident-card :incident="incident"></incident-card>
          </v-sheet>
        </v-dialog>


      </v-sheet>

    </v-dialog>

  `,
});
