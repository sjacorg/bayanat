const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      searchableDynamicFields: [],
      dynamicFields: [],
      originalFields: []
    }
  }),
  computed: {
    dynamicFieldsBulletinCard() {
      const omitedKeys = ['source_link', 'status', 'tags', 'comments', 'geo_locations']
      return this.formBuilder.dynamicFields.filter(field => !omitedKeys.includes(field.name))
    }
  },
  methods: {
    fieldClass(field) {
      return [field?.ui_config?.width || 'w-100', 'px-3 py-2']
    },
    fieldClassDrawer(field) {
      return [field?.ui_config?.width || 'w-100']
    },
    isFieldActive(field, name) {
      if (!name) return field.active

      return field.active && field.name === name;
    },
    findFieldOptionByValue(field, value) {
      if (!Array.isArray(field.options)) return

      return field.options.find(option => option?.value === value)
    },
    sortDynamicFields() {
      this.formBuilder.dynamicFields = this.formBuilder.dynamicFields.sort((a, b) => {
        return a.sort_order - b.sort_order; // normal sort
      });
    },
    async fetchDynamicFields({ entityType }) {
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
    async fetchSearchableDynamicFields({ entityType }) {
      try {
        this.formBuilder.loading = true;
        const response = await api.get(`/admin/api/dynamic-fields/?entity_type=${entityType}&active=true&searchable=true&limit=50`);
        this.formBuilder.searchableDynamicFields = response.data.data;
      } catch (err) {
        console.error(err);
        this.showSnack(handleRequestError(err));
      } finally {
        this.formBuilder.loading = false;
      }
    },
  },
};
