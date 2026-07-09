const getDefaultRelation = () => ({
  probability: null,
  related_as: null,
  comment: '',
});

const relationsMixin = {
  data: () => ({
    isConfirmRelationDialogOpen: false,
    relationToConfirm: getDefaultRelation(),
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
      this.relationToConfirm = getDefaultRelation();
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
    // Every relation picked in the dialog (create or edit-in-place) is a plain value in the
    // currently-edited entity's own perspective while the dialog is open. No conversion here
    // - applySameTypePerspective at load/save time handles the flip.
    addItemToRelation({ type, relationList = [], item = {}, relationData = {} } = {}) {
      this.closeConfirmRelationDialog();
      // get list of existing attached actors
      let existingIds = relationList.map((relation) => relation[type].id);

      if (!existingIds.includes(item.id)) {
        const relation = {
          [type]: item,
          ...relationData,
        };
        relationList.push(relation);

        this.showSnack(`Item ${item.id} has been related successfully`);
      }
    },

    removeFromRelationList({ relationList = [], index } = {}) {
      if (confirm(translations.areYouSure_)) {
        relationList.splice(index, 1);
      }
    },

    // Same-type relations (actor-actor, bulletin-bulletin, incident-incident) are stored
    // once, canonically keyed lower_id -> higher_id. A new (unsaved) entity always ends up
    // with the highest id once created, so it's treated as the higher-id side here.
    // canonicalRelationId is its own inverse, so this same helper both converts a freshly
    // loaded/created entity's relations into its own perspective (call after editItem sets
    // editedItem) and converts them back to canonical right before the save payload is sent
    // (call in save(), before posting/putting). Mutates relationList in place.
    applySameTypePerspective({ relationList = [], type, editedItemId = null, sameTypeInfo = null } = {}) {
      const viewedEntityId = editedItemId ?? Infinity;
      relationList.forEach((relation) => {
        relation.related_as = canonicalRelationId({
          relationInfo: sameTypeInfo,
          pickedId: relation.related_as,
          viewedEntityId,
          relatedEntityId: relation[type]?.id,
        });
      });
    },
  },
};
