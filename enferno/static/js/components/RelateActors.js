const RelateActors = Vue.defineComponent({
  props: ['exids', 'dialogProps', 'showCreateActorButton'],
  emits: ['relate'],
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
      actor: null,
      showSearch: true,
      relation: {
        probability: null,
        related_as: [],
        comment: '',
      }
    };
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

    search() {
      this.loading = true;
      axios
        .post(`/admin/api/actors/?page=${this.page}&per_page=${this.perPage}&mode=2`, {
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
      this.results = this.results.filter((result) => result.id !== item.id);
      this.$emit('relate', { item, relation: this.relation });
    },
    toggleSearchPanel() {
      this.showSearch = !this.showSearch
    }
  },

  template: /*html*/ `
    <v-dialog v-model="visible" v-bind="dialogProps">
      <v-card class="d-flex flex-column h-screen pa-0" :loading="loading">
        
        <!-- Top Toolbar -->
        <v-toolbar color="dark-primary">
          <v-btn variant="outlined" @click="toggleSearchPanel" class="ml-2">
            {{ showSearch ? translations.hideSearch_ : translations.showSearch_ }}
          </v-btn>
          <v-spacer></v-spacer>
          <v-btn v-if="showCreateActorButton" variant="outlined" @click="this.$root.actorDialog = true">
            {{ translations.createRelatedActor_ }}
          </v-btn>
          <v-btn icon @click="visible = false" class="ml-2">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <!-- Content -->
        <div class="overflow-y-auto">
          <split-view :left-slot-visible="showSearch" :left-width-percent="50">
            <template #left>
              <!-- Left Column: Search -->
              <v-col>
                <!-- Sub-Toolbar -->
                <div class="d-flex justify-space-between align-center mb-2">
                  <h3 class="text-h6 mb-0">{{ translations.advSearch_ }}</h3>
                </div>

                <actor-search-box 
                  v-model="q"
                  @search="reSearch"
                  :extra-filters="false"
                  :show-op="false"
                ></actor-search-box>

                <div class="text-center mt-4 position-sticky" style="bottom: 16px;">
                  <v-btn color="primary" @click="reSearch" block>{{ translations.search_ }}</v-btn>
                </div>
              </v-col>
            </template>
            <template #right>
              <!-- Right Column -->
              <v-col>
                <!-- Sub-Toolbar -->
                <div class="d-flex justify-space-between align-center mb-2">
                  <h3 class="text-h6 mb-0">{{ translations.actors_ }}</h3>
                </div>

                <v-card>
                  <v-card-text v-if="loading && !results.length" class="d-flex justify-center align-center pa-5">
                    <v-progress-circular indeterminate color="primary"></v-progress-circular>
                  </v-card-text>

                  <v-card-text>
                    <actor-result
                      v-for="(item, i) in results"
                      :key="i"
                      :actor="item"
                      :show-hide="true"
                    >
                      <template #actions>
                        <v-btn @click="$root.openConfirmRelationDialog(item)" variant="elevated" color="primary">
                          {{ translations.relate_ }}
                        </v-btn>
                      </template>
                    </actor-result>
                  </v-card-text>

                  <!-- Load More / No Results -->
                  <v-card-actions class="px-4 pb-4">
                    <v-spacer></v-spacer>
                    <v-btn v-if="moreItems" @click="loadMore" color="primary">{{ translations.loadMore_ }}</v-btn>
                    <span v-else class="text-grey">{{ translations.noResults_ }}</span>
                    <v-spacer></v-spacer>
                  </v-card-actions>
                </v-card>
              </v-col>
            </template>
          </split-view>
        </div>
      </v-card>
    </v-dialog>

    <v-dialog v-if="visible" max-width="450" v-model="$root.isConfirmRelationDialogOpen">
      <v-card>
        <relation-editor-card
          variant="text"
          v-model:relation="relation"
          :multi-relation="$root.actorRelationMultiple"
          :relation-types="$root.actorRelationTypes"
        ></relation-editor-card>
        
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="$root.closeConfirmRelationDialog" variant="text">{{ translations.cancel_ }}</v-btn>
          <v-btn @click="relateItem($root.relationToConfirm)" color="primary" variant="elevated">{{ translations.relate_ }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    `,
});
