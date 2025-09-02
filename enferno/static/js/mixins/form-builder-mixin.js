const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      dynamicFields: [],
      originalFields: []
    }
  }),
  methods: {
    isActiveField(field, name) {
      if (!name) return field.active

      return field.active && field.name === name;
    },
    sortDynamicFields() {
      this.formBuilder.dynamicFields = this.formBuilder.dynamicFields.sort((a, b) => {
        return a.sort_order - b.sort_order; // normal sort
      });
    },
    async fetchDynamicFields(entityType) {
      try {
        this.formBuilder.loading = true;
        const response = await api.get(`/admin/api/dynamic-fields/?entity_type=${entityType}&limit=50`);
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
