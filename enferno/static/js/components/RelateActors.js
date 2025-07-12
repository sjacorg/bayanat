const RelateActors = Vue.defineComponent({
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
  emits: ['relate', 'changeQuery'],
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
      hasMore: false,
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

          this.hasMore = this.page * this.perPage < this.total;
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
  watch: {
    q: {
      deep: true,
      handler(nextQuery) {
        this.$emit('changeQuery', nextQuery)
      }
    }
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
      :multi-relation="$root.actorRelationMultiple"
      :relation-types="$root.actorRelationTypes"
      @relate="relateItem"
    >
      <template v-if="$slots.actions" #actions>
        <slot name="actions"></slot>
      </template>
      <template #search-box>
        <actor-search-box 
          v-model="q"
          @search="reSearch"
          :extra-filters="false"
          :show-op="false"
        ></actor-search-box>
      </template>
      <template #results-list>
        <actor-result
          v-for="(item, i) in results"
          :key="i"
          :actor="item"
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
        </actor-result>
      </template>
    </relate-items-template>
    `,
});
