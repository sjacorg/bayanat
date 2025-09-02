const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      dynamicFields: [],
      originalFields: []
    }
  }),
  methods: {
    async fetchDynamicFields(entityType) {
      try {
        this.formBuilder.loading = true;
        const response = await axios.get(`/admin/api/dynamic-fields/?entity_type=${entityType}`);
        this.formBuilder.dynamicFields = response.data.data;
        this.sortDynamicFields();
        this.formBuilder.originalFields = deepClone(this.formBuilder.dynamicFields); // deep clone
      } catch (err) {
        console.error(err);
        this.showSnack(handleRequestError(err));
      } finally {
        this.formBuilder.loading = false;
      }
    },
  },
};
