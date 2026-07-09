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
    // sameTypeInfo: pass the relation-type catalog (e.g. this.atoaInfo) when relating two
    // entities of the same type (actor-actor, bulletin-bulletin, incident-incident). Those
    // relations are stored once, canonically keyed lower_id -> higher_id, so when relating
    // from the higher-id entity's profile, the picked type is in that entity's perspective
    // and must be converted to its reciprocal before being stored against the canonical
    // record. Omit for cross-type relations (e.g. actor-bulletin), which never mirror.
    addItemToRelation({ type, relationList = [], item = {}, relationData = {}, editedItem = {}, sameTypeInfo = null } = {}) {
      this.closeConfirmRelationDialog();
      // get list of existing attached actors
      let existingIds = relationList.map((relation) => relation[type].id);

      if (!existingIds.includes(item.id)) {
        const relation = {
          [type]: item,
          ...relationData,
          related_as: canonicalRelationId(sameTypeInfo, relationData.related_as, editedItem?.id, item.id),
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

    // Wraps a stored same-type relation so the type editor reads/writes it from the
    // currently-edited entity's perspective instead of the raw canonical value. The
    // canonical record is stored once (lower_id -> higher_id); canonicalRelationId is its
    // own inverse, so the same call both displays and saves the perspective-correct type.
    relationEditorProxy({ relation, type, editedItem = {}, sameTypeInfo = null } = {}) {
      const relatedId = relation[type]?.id;
      return {
        [type]: relation[type],
        get related_as() {
          return canonicalRelationId(sameTypeInfo, relation.related_as, editedItem?.id, relatedId);
        },
        set related_as(pickedId) {
          relation.related_as = canonicalRelationId(sameTypeInfo, pickedId, editedItem?.id, relatedId);
        },
        get probability() {
          return relation.probability;
        },
        set probability(value) {
          relation.probability = value;
        },
        get comment() {
          return relation.comment;
        },
        set comment(value) {
          relation.comment = value;
        },
      };
    },
  },
};
