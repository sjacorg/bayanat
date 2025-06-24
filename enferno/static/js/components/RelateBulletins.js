const RelateBulletins = Vue.defineComponent({
  props: ['modelValue', 'show', 'exids', 'dialogProps'], // Changed 'value' to 'modelValue'
  emits: ['update:modelValue', 'relate'], // Explicitly define emitted events

  data() {
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
      bulletin: null,
      showBulletin: false,
    };
  },
  watch: {
    results: {
      handler(val, old) {},
      deep: true,
    },

    modelValue: function (val) {
      this.$emit('update:modelValue', val); // Changed 'input' to 'update:modelValue'
    },
  },

  methods: {
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

    search( ) {
      this.loading = true;

      axios
        .post(`/admin/api/bulletins/?page=${this.page}&per_page=${this.perPage}&mode=2`, {
          q: [this.q],
        })
        .then((response) => {
          this.loading = false;
          this.total = response.data.total;
          
          // exclude ids of item and related items
          const ex_arr = this.exids || [];
          this.results = this.results.concat(
            response.data.items.filter((x) => !ex_arr.includes(x.id)),
          );

          this.moreItems = this.page * this.perPage < this.total;
        })
        .catch((err) => {
          console.log(err.response.data);
          this.loading = false;
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

        <v-container fluid class="h-100">
          <v-row>
            <v-col cols="12" lg="6">

              <v-card variant="outlined">
                <bulletin-search-box 
                  @search="reSearch"
                  :extra-filters="false"
                  v-model="q"
                  :show-op="false">
                </bulletin-search-box>
              </v-card>

              <v-card  class="text-center  search-toolbar" >
                <v-card-text>
                  <v-btn color="primary" @click="reSearch">{{ translations.search_ }}</v-btn>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" lg="6">

              <v-card :loading="loading">

                <v-toolbar class="handle">
                    <v-toolbar-title>{{ translations.advSearch_ }}</v-toolbar-title>
                  <v-spacer></v-spacer>
                  <v-btn icon="mdi-close" @click="visible=false"></v-btn>
                </v-toolbar>

                <v-divider></v-divider>

                <v-card-text v-if="loading" class="d-flex pa-5" justify-center align-center>
                  <v-progress-circular class="ma-auto" indeterminate
                                       color="primary"></v-progress-circular>
                </v-card-text>

                <v-card class="pa-2">

                  <bulletin-result v-for="(item, i) in results" :key="i" :bulletin="item"
                                   :show-hide="true">
                    <template v-slot:actions>
                      <v-btn @click="relateItem(item)"  variant="elevated" color="primary">{{ translations.relate_ }}
                      </v-btn>

                    </template>
                  </bulletin-result>
                </v-card>

                <v-card-actions>
                  <v-spacer></v-spacer>
                  <v-btn icon="mdi-dots-horizontal" @click="loadMore" v-if="moreItems" color="third">
                  </v-btn>
                  <v-sheet small v-else class="heading" color="grey--text"> {{ translations.noResults_ }} </v-sheet>
                  <v-spacer></v-spacer>
                </v-card-actions>
              </v-card>
            </v-col>

          </v-row>
        </v-container>

        <v-dialog v-model="showBulletin" max-width="550">
          <v-sheet>
            <div class="d-flex justify-end">
              <v-btn @click="showBulletin=false"    right="10">
                <v-icon>mdi-close</v-icon>
              </v-btn>
            </div>
            <bulletin-card :bulletin="bulletin"></bulletin-card>
          </v-sheet>
        </v-dialog>

      </v-sheet>

      </v-dialog>
    `,
});
