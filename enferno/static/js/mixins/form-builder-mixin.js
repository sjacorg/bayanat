const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      searchableDynamicFields: [],
      dynamicFields: [],
      originalFields: []
    },
    fixedFields: ['source_link', 'comments'],
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
    getResponsiveWidth(width) {
      switch (width) {
        case 'w-50':
          return 'field-50'; // flex width: 50%, wraps to 100% if container is too small
        case 'w-33':
          return 'field-33'; // flex width: 33.33%, wraps to 100% if container is too small
        default:
          return 'field-100'; // full width
      }
    },
    fieldClass(field) {
      return [this.getResponsiveWidth(field?.ui_config?.width), 'px-3 py-2']
    },
    fieldClassDrawer(field) {
      return [this.getResponsiveWidth(field?.ui_config?.width)]
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
