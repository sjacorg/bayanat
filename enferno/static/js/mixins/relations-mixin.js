const defaultRelation = {
  probability: null,
  related_as: [],
  comment: '',
};

const relationsMixin = {
  data: () => ({
    isConfirmRelationDialogOpen: false,
    relationToConfirm: { ...defaultRelation },
    itobInfo: [],
    itoaInfo: [],
    atobInfo: [],
    atoaInfo: [],
    btobInfo: [],
    itoiInfo: [],
  }),
  created() {
    this.fetchRelationInfo();
  },
  methods: {
    fetchRelationInfo() {
      axios
        .get('/admin/api/relation/info')
        .then((response) => {
          this.itobInfo = response.data.itobInfo;
          this.itoaInfo = response.data.itoaInfo;
          this.atobInfo = response.data.atobInfo;
          this.atoaInfo = response.data.atoaInfo;
          this.btobInfo = response.data.btobInfo;
          this.itoiInfo = response.data.itoiInfo;
        })
        .catch((error) => {
          console.error('Error fetching relation info:', error);
          this.showSnack('Error fetching relation info');
        });
    },
    openConfirmRelationDialog(item) {
      this.relationToConfirm = item;
      this.isConfirmRelationDialogOpen = true;
    },
    closeConfirmRelationDialog() {
      this.relationToConfirm = { ...defaultRelation };
      this.isConfirmRelationDialogOpen = false;
    },
    getExcludedIds({ type, includeSelf = false, editedItem, reviewItem } = {}) {
      const ids = [];

      const getRelations = (item) => {
        if (!item?.id) return [];
        const relationItems = item[`${type}_relations`] || [];
        return relationItems.map((relation) => relation[type]?.id);
      };

      if (includeSelf) {
        if (editedItem?.id) ids.push(editedItem.id);
        else if (reviewItem?.id) ids.push(reviewItem.id);
      }

      ids.push(...getRelations(editedItem));
      ids.push(...getRelations(reviewItem));

      return ids;
    },
    searchRelatedItems({ ref = {}, searchTerm = '' } = {}) {
      ref?.open();
      this.$nextTick(() => {
        if ('q' in ref) ref.q = { tsv: searchTerm };
        ref?.reSearch();
      });
    },
    addItemToRelation({ type, relationList = [], item = {}, relationData = {} } = {}) {
      this.closeConfirmRelationDialog();
      // get list of existing attached actors
      let ex = relationList.map((x) => x[type].id);

      if (!ex.includes(item.id)) {
        const relation = {
          [type]: item,
          ...relationData,
        };
        relationList.push(relation);
      }
    },

    removeFromRelationList({ relationList = [], index } = {}) {
      if (confirm(translations.confirm_)) {
        relationList.splice(index, 1);
      }
    },
  },
};
