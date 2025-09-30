const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      searchableDynamicFields: [],
      dynamicFields: [],
      originalFields: []
    },
    fixedFields: ['comments', 'status'],
  }),
  computed: {
    dynamicFieldsBulletinCard() {
      // Keys omited since they are rendered somewhere else in the drawer
      const omitedKeys = ['source_link', 'status', 'tags', 'comments', 'geo_locations']
      return this.formBuilder.dynamicFields.filter(field => !omitedKeys.includes(field.name))
    },
    fixedDynamicFields() {
      return this.formBuilder.dynamicFields.filter(field => this.fixedFields.includes(field.name))        
    },
    movableDynamicFields() {
      return this.formBuilder.dynamicFields.filter(field => !this.fixedFields.includes(field.name))        
    },
  },
  methods: {
    getResponsiveWidth(ui_config) {
      if (ui_config?.width === 'w-50') {
        if (ui_config?.align === 'right') {
          return 'grid-col-2'
        }
        return 'grid-col-span-1'
      }
      if (ui_config?.width === 'w-100') return 'grid-col-span-2'
      return 'grid-col-span-2'
    },
    getResponsiveHeight(height) {
      if (height === 2) return 'grid-row-span-2'
      return 'grid-row-span-1'
    },
    fieldClass(field) {
      return [
        this.getResponsiveWidth(field?.ui_config),
        this.getResponsiveHeight(field?.field_type === 'long_text' ? 2 : 1),
      ]
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

      return field.options.find(option => option?.id === Number(value))
    },
    sortFields(fields) {
      return fields.sort((a, b) => {
        return a.sort_order - b.sort_order; // normal sort
      });
    },
    async fetchDynamicFields({ entityType }) {
      try {
        this.formBuilder.loading = true;
        const response = await api.get(`/admin/api/dynamic-fields/?entity_type=${entityType}&limit=50`);
        this.formBuilder.dynamicFields = response.data.data;
        this.formBuilder.dynamicFields = this.sortFields(this.formBuilder.dynamicFields);
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
        this.formBuilder.searchableDynamicFields = this.sortFields(this.formBuilder.searchableDynamicFields);
      } catch (err) {
        console.error(err);
        this.showSnack(handleRequestError(err));
      } finally {
        this.formBuilder.loading = false;
      }
    },
  },
};
