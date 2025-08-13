const RelateIncidents = Vue.defineComponent({
  props: {
    exids: {
      type: Array,
      default: () => ([])
    },
    dialogProps: {
      type: Object,
      default: () => ({})
    }
  },
  emits: ['relate'],
  data() {
    return {
      translations: window.translations,
      q: {},
      loading: true,
      results: [],
      visible: false,
      perPage: 10,
      hasMore: false,
      nextCursor: null,
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
      this.results = [];
      this.nextCursor = null;
      this.search();
    },

    search() {
      this.loading = true;

      const requestData = {
          q: [this.q],
          per_page: this.perPage,
          cursor: this.nextCursor,
      };

      axios
        .post(`/admin/api/incidents/?mode=2`, requestData)
        .then((response) => {
          this.loading = false;

          // exclude ids of item and related items
          const ex_arr = this.exids || [];
          this.results = this.results.concat(
            response.data.items.filter((x) => !ex_arr.includes(x.id)),
          );

          this.hasMore = response.data.meta.hasMore;
          this.nextCursor = response.data.nextCursor || null;
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
    relateItem({ item, relationData }) {
      this.results = this.results.filter((result) => result.id !== item.id);
      this.$emit('relate', { item, relationData });
    },
  },

  template: /*html*/ `
    <relate-items-template
      v-model:visible="visible"
      :dialog-props="dialogProps"
      :loading="loading"
      :results="results"
      @search="reSearch"
      @load-more="loadMore"
      :has-more="hasMore"
      :multi-relation="$root.incidentRelationMultiple"
      :relation-types="$root.incidentRelationTypes"
      @relate="relateItem"
    >
      <template v-if="$slots.actions" #actions>
        <slot name="actions"></slot>
      </template>
      <template #search-box>
        <incident-search-box 
          v-model="q"
          @search="reSearch"
          :extra-filters="false"
          :show-op="false"
        ></incident-search-box>
      </template>
      <template #results-list>
        <incident-result
          v-for="(item, i) in results"
          :key="i"
          :incident="item"
          :show-hide="true"
        >
          <template #actions>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="$root.openConfirmRelationDialog(item)"
                  color="primary"
                  variant="elevated"
                  icon="mdi-link-plus"
                  size="small"
                ></v-btn>
              </template>
              {{ translations.addAsRelated_ }}
            </v-tooltip>
          </template>
        </incident-result>
      </template>
    </relate-items-template>
    `,
});
