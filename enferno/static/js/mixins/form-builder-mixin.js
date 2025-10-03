const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      searchableDynamicFields: [],
      dynamicFields: [],
      originalFields: [],
    },
    fixedFields: ['comments', 'status'],
    dragDrop: {
      dropLine: { id: null, cls: '' },
      draggingId: null,
      sortables: {},
    },
    ui: {
      selectFieldTypeDialog: false,
      saving: false,
      search: '',
    },
    form: {
      editedItem: {},
    },
    changes: {
      diff: '',
      table: [],
    },
  }),
  computed: {
    dynamicFieldsBulletinCard() {
      // Keys omited since they are rendered somewhere else in the drawer
      const omitedKeys = ['source_link', 'status', 'tags', 'comments', 'geo_locations'];
      return this.formBuilder.dynamicFields.filter((field) => !omitedKeys.includes(field.name));
    },
    dynamicFieldsActorCard() {
      // Keys omited since they are rendered somewhere else in the drawer
      const omitedKeys = ['source_link', 'status', 'tags', 'roles', 'comments', 'geo_locations']
      return this.formBuilder.dynamicFields.filter(field => !omitedKeys.includes(field.name))
    },
    fixedDynamicFields() {
      return this.formBuilder.dynamicFields.filter((field) =>
        this.fixedFields.includes(field.name),
      );
    },
    movableDynamicFields() {
      return this.formBuilder.dynamicFields.filter(
        (field) => !this.fixedFields.includes(field.name),
      );
    },
    hasChanges() {
      const changes = this.computeChanges();
      return Boolean(changes.create.length || changes.update.length || changes.delete.length);
    },
    filteredDynamicFields() {
      if (!this.ui.search) return this.formBuilder.dynamicFields;

      return this.formBuilder.dynamicFields.filter((field) =>
        field.title?.toLowerCase().includes(this.ui.search.trim().toLowerCase()),
      );
    },
    filteredMovableDynamicFields() {
      if (!this.ui.search) return this.movableDynamicFields;

      return this.movableDynamicFields.filter((field) =>
        field.title?.toLowerCase().includes(this.ui.search.trim().toLowerCase()),
      );
    },
    filteredFixedDynamicFields() {
      if (!this.ui.search) return this.fixedDynamicFields;

      return this.fixedDynamicFields.filter((field) =>
        field.title?.toLowerCase().includes(this.ui.search.trim().toLowerCase()),
      );
    },
  },
  methods: {
    discardChanges() {
      this.$confirm({
        title: window.translations.youreAboutToDiscardChanges_,
        message: `${window.translations.discardingWillRemoveAllUnsavedEdits_}\r\n\r\n${window.translations.doYouWantToContinue_}`,
        acceptProps: {
          text: window.translations.discardChanges_,
          color: 'red',
        },
        dialogProps: { width: 780 },
        onAccept: () => {
          this.formBuilder.dynamicFields = deepClone(this.formBuilder.originalFields);
          this.$toast({
            message: window.translations.allUnsavedEditsHaveBeenDiscarded_,
            hideActions: true,
            snackbarProps: {
              color: 'green-lighten-5',
              contentClass: 'border',
            },
            iconProps: {
              icon: 'mdi-check-circle',
              color: 'green',
            },
          });
        },
      });
    },
    edit({ field }) {
      const matchingField = this.formBuilder.dynamicFields.find(
        (dynamicField) => dynamicField.id === field.id,
      );
      this.form.editedItem = matchingField;
      this.ui.selectFieldTypeDialog = true;
    },
    saveField(evt) {
      let idx = this.formBuilder.dynamicFields.findIndex(
        (dynamicField) => dynamicField.id === evt.id,
      );

      if (this.formBuilder.dynamicFields[idx] && evt.id) {
        // Update existing field
        this.formBuilder.dynamicFields[idx] = { ...evt };
      } else {
        // Add new field
        this.formBuilder.dynamicFields.push(evt);
        this.$nextTick(() => {
          const el = document.querySelector(`[data-field-id="${evt.id}"]`);
          el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
      }

      this.formBuilder.dynamicFields = this.sortFields(this.formBuilder.dynamicFields);
    },

    buildChangesTable() {
      const changeTypeTranslations = {
        create: translations.added_,
        update: translations.modified_,
        delete: translations.deleted_,
      };

      this.changes.table = Object.entries(this.changes.diff).flatMap(([changeType, change]) =>
        change.map((item) => ({
          title: item.item.title || window.translations.newField_,
          type: changeTypeTranslations[changeType],
          key: changeType,
        })),
      );
    },

    showSaveDialog({ entityType }) {
      this.changes.diff = this.computeChanges({ ignoreSortOrder: true });
      this.buildChangesTable();

      this.$refs.reviewAndConfirmDialog.show({
        title: window.translations.reviewAndConfirmChanges_,
        dialogProps: { width: 780 },
        onAccept: async () => {
          await this.save({ entityType });
        },
      });
    },
    getSearchOperatorFromFieldType(field) {
      switch (field.field_type) {
        case 'text':
        case 'long_text':
          return 'contains';
        case 'number':
          return 'eq';
        case 'select':
          return 'all';
        case 'datetime':
          return 'between';
        default:
          return 'eq';
      }
    },
    async toggleFieldVisibility({ field }) {
      const matchingField = this.formBuilder.dynamicFields.find(
        (dynamicField) => dynamicField.id === field.id,
      );
      matchingField.active = !matchingField.active;
      if (matchingField.active && matchingField?.delete) {
        delete matchingField.delete;
      }
    },
    reindexFields() {
      this.formBuilder.dynamicFields = this.formBuilder.dynamicFields.map((field, index) => ({
        ...field,
        sort_order: index + 1,
      }));
    },
    async deleteField({ field }) {
      this.$root.$confirm({
        title: window.translations.youreAboutToDeleteAField_,
        message: `${window.translations.deletingTheFieldWillRemoveItFromYourForm_(
          field.title || window.translations.newField_,
        )}\r\n\r\n${window.translations.doYouWantToContinue_}`,
        acceptProps: { text: window.translations.deleteField_, color: 'red' },
        dialogProps: { width: 780 },
        onAccept: () => {
          const dynamicField = this.formBuilder.dynamicFields.find(
            (dynamicField) => dynamicField.id === field.id,
          );
          dynamicField.active = false;
          dynamicField.delete = true;

          this.$root.$toast({
            message: window.translations.fieldHasBeenDeletedSuccessfully_(
              field.title || window.translations.newField_,
            ),
            hideActions: true,
            snackbarProps: {
              color: 'green-lighten-5',
              contentClass: 'border',
            },
            iconProps: {
              icon: 'mdi-check-circle',
              color: 'green',
            },
          });
        },
      });
    },
    initSortable(el) {
      if (!el) return;

      const sortable = new Sortable(el, {
        group: 'fields',
        draggable: '.sortable-item',
        sort: true,
        animation: 150,
        handle: '.drag-handle',
        ghostClass: 'sortable-ghost',
        scroll: true,
        bubbleScroll: true,
        forceAutoScrollFallback: true,
        forceFallback: true,
        scrollSensitivity: 100,

        onStart: (evt) => {
          this.dragDrop.draggingId = evt.item?.dataset?.id ?? null;
          document.body.classList.add('cursor-grabbing');
        },

        onMove: (evt, originalEvent) => {
          const target = evt.related?.closest?.('.sortable-item');
          if (!target) {
            this.dragDrop.dropLine.id = null;
            this.dragDrop.dropLine.cls = '';
            return false;
          }

          const overId = target.dataset?.id;
          if (!overId || overId == this.dragDrop.draggingId) {
            this.dragDrop.dropLine.id = null;
            this.dragDrop.dropLine.cls = '';
            return false;
          }

          const rect = target.getBoundingClientRect();
          let cls = '';

          const sameRow = this.isTargetRowHorizontal(target);

          if (sameRow) {
            // Horizontal logic
            const midX = rect.left + rect.width / 2;
            cls = originalEvent.clientX < midX ? 'drop-line-left' : 'drop-line-right';
          } else {
            // Vertical logic
            const midY = rect.top + rect.height / 2;
            cls = originalEvent.clientY < midY ? 'drop-line-above' : 'drop-line-below';
          }

          // 🔍 Hide drop line if dropping wouldn't move the item
          const fromIdx = this.formBuilder.dynamicFields.findIndex(
            (i) => i.id == this.dragDrop.draggingId,
          );
          const tgtIdx = this.formBuilder.dynamicFields.findIndex((i) => i.id == overId);
          if (!this.wouldMove(fromIdx, tgtIdx, cls)) cls = '';

          // Update drop line state
          if (cls) {
            this.dragDrop.dropLine.id = overId;
            this.dragDrop.dropLine.cls = cls;
          } else {
            this.dragDrop.dropLine.id = null;
            this.dragDrop.dropLine.cls = '';
          }

          return false; // cancel DOM swap
        },

        onEnd: (evt) => {
          document.body.classList.remove('cursor-grabbing');
          const overId = this.dragDrop.dropLine.id;
          const cls = this.dragDrop.dropLine.cls;

          const resetUI = () => {
            this.dragDrop.draggingId = null;
            this.dragDrop.dropLine.id = null;
            this.dragDrop.dropLine.cls = '';
          };

          if (!overId || !cls || !this.dragDrop.draggingId) {
            resetUI();
            return;
          }

          const arr = this.formBuilder.dynamicFields;

          const fromIdx = arr.findIndex((i) => i.id == this.dragDrop.draggingId);
          const tgtIdx = arr.findIndex((i) => i.id == overId);

          if (fromIdx === -1 || tgtIdx === -1) {
            resetUI();
            return;
          }

          // No-op check: don't move if drop wouldn't change anything
          if (!this.wouldMove(fromIdx, tgtIdx, cls)) {
            resetUI();
            return;
          }

          const after = cls === 'drop-line-below' || cls === 'drop-line-right';
          let insertIndex = tgtIdx + (after ? 1 : 0);

          if (fromIdx < insertIndex) insertIndex -= 1;

          const [moved] = arr.splice(fromIdx, 1);
          arr.splice(insertIndex, 0, moved);

          // Mark field as moved so we can display it as modified on diff dialog
          moved.moved = true;

          resetUI();
          this.reindexFields();
        },
      });

      this.dragDrop.sortables.main = sortable;
    },
    computeChanges(options) {
      const changes = { create: [], update: [], delete: [] };
      const originalMap = new Map(this.formBuilder.originalFields.map((f) => [f.id, f]));

      for (const field of this.formBuilder.dynamicFields) {
        // Deletions
        if (field.delete) {
          if (field.id) {
            changes.delete.push({ id: field.id, item: field });
            originalMap.delete(field.id);
          }
          continue;
        }

        // Creations
        if (!field.id || field.id?.startsWith?.('temp-')) {
          changes.create.push({ item: field });
        } else {
          const orig = originalMap.get(field.id);
          if (orig) {
            let fieldToCompare = field;
            let origToCompare = orig;

            // 🔧 Optionally ignore sort_order
            if (options?.ignoreSortOrder) {
              const { sort_order, ...restField } = field;
              const { sort_order: __, ...restOrig } = orig;
              fieldToCompare = restField;
              origToCompare = restOrig;
            }

            const isDifferent = JSON.stringify(fieldToCompare) !== JSON.stringify(origToCompare);

            // ✅ Show if real diff OR if moved was flagged
            if (isDifferent || field.moved) {
              changes.update.push({ id: field.id, item: field });
            }

            originalMap.delete(field.id);
          }
        }
      }

      return changes;
    },

    mergeFailedItems(dynamicFields, failedItems) {
      const merged = [...dynamicFields];

      // Failed creates: add directly
      for (const { item } of failedItems.create) {
        merged.push(item);
      }

      // Failed updates: overwrite by id with edited version
      for (const { id, item } of failedItems.update) {
        const idx = merged.findIndex((f) => f.id === id);
        if (idx !== -1) merged[idx] = item;
        else merged.push(item);
      }

      // Failed deletes: mark as inactive
      for (const { id, item } of failedItems.delete) {
        const idx = merged.findIndex((f) => f.id === id);
        if (idx !== -1) merged[idx] = { ...item, active: false };
        else merged.push({ ...item, active: false });
      }

      return merged;
    },

    isTargetRowHorizontal(target) {
      if (!target) return false;
      return (
        target.classList.contains('w-50') ||
        target.classList.contains('w-33') ||
        target.classList.contains('w-25')
      );
    },

    wouldMove(fromIdx, tgtIdx, cls) {
      if (fromIdx === tgtIdx) return false;

      if (cls === 'drop-line-above' || cls === 'drop-line-left') {
        return fromIdx !== tgtIdx - 1; // moving above a next neighbor → no-op
      } else if (cls === 'drop-line-below' || cls === 'drop-line-right') {
        return fromIdx !== tgtIdx + 1; // moving below a previous neighbor → no-op
      }
      return true;
    },
    async save({ entityType }) {
      this.ui.saving = true;
      const diffChanges = this.computeChanges();
      const failedItems = { create: [], update: [], delete: [] };

      try {
        const requests = [];

        // Create
        for (const { item } of diffChanges.create) {
          const { id, ...payload } = item;

          requests.push(
            api
              .post(`/admin/api/dynamic-fields/`, { item: payload })
              .then((res) => {
                // ✅ mark as saved
                this.formBuilder.originalFields.push(res.data.item);
              })
              .catch((err) => {
                failedItems.create.push({ item });
                throw err;
              }),
          );
        }

        // Update
        for (const { id, item } of diffChanges.update) {
          requests.push(
            api
              .put(`/admin/api/dynamic-fields/${id}`, { item })
              .then((res) => {
                const idx = this.formBuilder.originalFields.findIndex((f) => f.id === id);
                if (idx !== -1) this.formBuilder.originalFields[idx] = res.data.item;
              })
              .catch((err) => {
                failedItems.update.push({ id, item });
                throw err;
              }),
          );
        }

        // Delete
        for (const { id, item } of diffChanges.delete) {
          if (!id || id.startsWith?.('temp-')) continue;

          requests.push(
            api
              .delete(`/admin/api/dynamic-fields/${id}`)
              .then(() => {
                const originalField = this.formBuilder.originalFields.find((f) => f.id === id);
                if (originalField) originalField.active = false;
              })
              .catch((err) => {
                failedItems.delete.push({ id, item });
                throw err;
              }),
          );
        }

        // Run all in parallel, but don’t throw
        const results = await Promise.allSettled(requests);

        const failed = results.filter((r) => r.status === 'rejected');
        if (failed.length > 0) {
          console.log('Some requests failed:', failed);
          this.showSnack(failed.map((r) => handleRequestError(r.reason)).join('<br />'));

          this.formBuilder.dynamicFields = this.mergeFailedItems(
            this.formBuilder.originalFields,
            failedItems,
          );

          // Only keep failed items in the diff
          this.changes.diff = {
            create: failedItems.create,
            update: failedItems.update,
            delete: failedItems.delete,
          };
          this.buildChangesTable();
          throw failed?.[0]?.reason;
        } else {
          this.showSnack(window.translations.fieldsSavedSuccessfully_);
          await this.fetchDynamicFields({ entityType });
        }
      } catch (err) {
        console.error(err);
        this.showSnack(handleRequestError(err));
        throw err;
      } finally {
        this.ui.saving = false;
      }
    },

    closeDrawer(open) {
      this.ui.selectFieldTypeDialog = open;
      this.form.editedItem = {};
    },
    getResponsiveWidth(ui_config) {
      if (ui_config?.width === 'w-50') {
        if (ui_config?.align === 'right') {
          return 'grid-col-2';
        }
        return 'grid-col-span-1';
      }
      if (ui_config?.width === 'w-100') return 'grid-col-span-2';
      return 'grid-col-span-2';
    },
    getResponsiveHeight(height) {
      if (height === 2) return 'grid-row-span-2';
      return 'grid-row-span-1';
    },
    fieldClass(field) {
      return [
        this.getResponsiveWidth(field?.ui_config),
        this.getResponsiveHeight(field?.field_type === 'long_text' ? 2 : 1),
      ];
    },
    fieldClassDrawer(field) {
      return [field?.ui_config?.width || 'w-100'];
    },
    isFieldActive(field, name) {
      if (!name) return field.active;

      return field.active && field.name === name;
    },
    findFieldOptionByValue(field, value) {
      if (!Array.isArray(field.options)) return;

      return field.options.find((option) => option?.id === Number(value));
    },
    sortFields(fields) {
      return fields.sort((a, b) => {
        return a.sort_order - b.sort_order; // normal sort
      });
    },
    async fetchDynamicFields({ entityType }) {
      try {
        this.formBuilder.loading = true;
        const response = await api.get(
          `/admin/api/dynamic-fields/?entity_type=${entityType}&limit=50`,
        );
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
        const response = await api.get(
          `/admin/api/dynamic-fields/?entity_type=${entityType}&active=true&searchable=true&limit=50`,
        );
        this.formBuilder.searchableDynamicFields = response.data.data;
        this.formBuilder.searchableDynamicFields = this.sortFields(
          this.formBuilder.searchableDynamicFields,
        );
      } catch (err) {
        console.error(err);
        this.showSnack(handleRequestError(err));
      } finally {
        this.formBuilder.loading = false;
      }
    },
  },
};
