const idNumberMixin = {
    data: () => ({
        idNumberTypes: [],
        idNumberTypesMap: {},
        idNumberTypesLoading: false
    }),
    methods: {
        fetchIdNumberTypes() {
            // If already loaded the exit
            if (this.idNumberTypes.length) return
            // If it's already loading exit
            if (this.idNumberTypesLoading) return

            this.idNumberTypesLoading = true

            // Fetch and cache IDNumberType data for ID number display and editing
            axios.get('/admin/api/idnumbertypes/').then(res => {
                this.idNumberTypes = res.data.items || [];
                // Create a lookup map for quick access
                this.idNumberTypesMap = {};
                this.idNumberTypes.forEach(type => {
                    this.idNumberTypesMap[type.id] = type;
                });
            }).catch(err => {
                this.idNumberTypes = [];
                this.idNumberTypesMap = {};
                console.error('Error fetching id number types:', err);
                this.showSnack(handleRequestError(err));
            }).finally(() => {
                this.idNumberTypesLoading = false;
            })
        },
    }
  };
  