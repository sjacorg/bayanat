const relatedSearchMixin = {
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
          q: this.queryFormat === 'single' ? this.q : [this.q],
          per_page: this.perPage,
          cursor: this.nextCursor,
      };

      axios
        .post(this.searchEndpoint, requestData)
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
  watch: {
    q: {
      deep: true,
      handler(nextQuery) {
        this.$emit('changeQuery', nextQuery)
      }
    }
  },
};
