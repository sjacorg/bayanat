const formBuilderMixin = {
  data: () => ({
    formBuilder: {
      loading: false,
      showRevisions: false,
      searchableDynamicFields: [],
      dynamicFields: [],
      originalFields: [],
      historyState: { items: [], total: 0, page: 1, per_page: 20 },
    },
    excludedFields: {
      bulletin: ['source_link','status','tags','comments','geo_locations'],
      actor: ['source_link','status','tags','roles','comments','geo_locations'],
      incident: ['source_link','status','tags','comments','geo_locations'],
    },
    infiniteScrollCallback: null,
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
    fixedDynamicFields() {
      return this.formBuilder.dynamicFields.filter((field) => this.isFixedField(field) && !field.deleted);
    },
    movableDynamicFields() {
      return this.formBuilder.dynamicFields.filter((field) => !this.isFixedField(field) && !field.deleted);
    },
    hasChanges() {
      const changes = this.computeChanges({
        previousFields: this.formBuilder.originalFields,
        currentFields: this.formBuilder.dynamicFields,
      });
      return Boolean(changes.create.length || changes.update.length || changes.delete.length);
    },
    filteredDynamicFields() {
      if (!this.ui.search) return this.formBuilder.dynamicFields;

      return this.formBuilder.dynamicFields.filter((field) => this.fieldTitleMatchesSearch(field) && !field.deleted);
    },
    filteredMovableDynamicFields() {
      if (!this.ui.search) return this.movableDynamicFields;

      return this.movableDynamicFields.filter((field) => this.fieldTitleMatchesSearch(field));
    },
    filteredFixedDynamicFields() {
      if (!this.ui.search) return this.fixedDynamicFields;

      return this.fixedDynamicFields.filter((field) => this.fieldTitleMatchesSearch(field));
    },
  },
  methods: {
    cardDynamicFields(type = 'bulletin') {
      const excludeKeys = this.excludedFields[type] || [];
      return this.formBuilder.dynamicFields.filter(f => !excludeKeys.includes(f.name));
    },
    isFixedField(field) {
      return this.fixedFields.includes(field.name)
    },
    fieldTitleMatchesSearch(field) {
      return field.title?.toLowerCase().includes(this.ui.search.trim().toLowerCase());
    },
    openRevisionHistoryDrawer() {
      this.formBuilder.showRevisions = true;
    },
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

    buildChangesTable(diff) {
      const changeTypeTranslations = {
        create: window.translations.added_,
        update: window.translations.modified_,
        delete: window.translations.deleted_,
      };

      // Collect all deleted IDs first
      const deletedIds = new Set(diff.delete?.map(item => item.id));

      const changes = Object.entries(diff).flatMap(([changeType, items]) =>
        items
          // Skip create/update if the same field was deleted
          .filter(item => !deletedIds.has(item.id) || changeType === 'delete')
          .map(item => ({
            title: item.item.title || window.translations.newField_,
            type: changeTypeTranslations[changeType],
            key: changeType,
          }))
      );

      return changes;
    },

    showSaveDialog({ entityType }) {
      this.changes.diff = this.computeChanges({
        ignoreSortOrder: true,
        previousFields: this.formBuilder.originalFields,
        currentFields: this.formBuilder.dynamicFields,
      });
      this.changes.table = this.buildChangesTable(this.changes.diff);

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
      const fieldToUpdate = this.formBuilder.dynamicFields.find(
        (dynamicField) => dynamicField.id === field.id,
      );

      fieldToUpdate.active = !fieldToUpdate.active;
      if (fieldToUpdate.active) fieldToUpdate.deleted = false;
    },
    reindexFields() {
      // Reindex fields but keep fixed fields sort_order intact
      this.formBuilder.dynamicFields = this.formBuilder.dynamicFields.map((field, index) => ({
        ...field,
        sort_order: this.fixedFields.includes(field.name) ? field.sort_order : index + 1,
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
          if (String(field.id).startsWith('temp-')) {
            this.formBuilder.dynamicFields = this.formBuilder.dynamicFields.filter(
              (dynamicField) => dynamicField.id !== field.id,
            );
          } else {
            const dynamicField = this.formBuilder.dynamicFields.find(
              (dynamicField) => dynamicField.id === field.id,
            );
            dynamicField.active = false;
            dynamicField.deleted = true;
          }

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
    computeChanges({
      previousFields = [],
      currentFields = [],
      ignoreSortOrder = false,
    } = {}) {
      const changes = { create: [], update: [], delete: [] };

      const prevMap = new Map(previousFields.map(f => [f.id, f]));
      const currMap = new Map(currentFields.map(f => [f.id, f]));

      const sortObjectKeys = (obj) => {
        if (Array.isArray(obj)) return obj.map(sortObjectKeys);
        if (obj && typeof obj === 'object')
          return Object.keys(obj).sort().reduce((acc, key) => {
            acc[key] = sortObjectKeys(obj[key]);
            return acc;
          }, {});
        return obj;
      };

      // 🗑️ Detect removed items (hard deletions)
      for (const [id, prevField] of prevMap.entries()) {
        if (!currMap.has(id)) {
          changes.delete.push({ id, item: prevField });
        }
      }

      // ➕ Detect creations, updates, and soft deletions
      for (const currField of currentFields) {
        const id = currField.id;
        const prevField = id ? prevMap.get(id) : null;

        // Newly created
        if (!id || !prevField || id.startsWith?.('temp-')) {
          if (!currField.deleted) {
            changes.create.push({ item: currField }); // always push create
          } else {
            // If deleted immediately, also push delete
            changes.delete.push({ id: currField.id || `temp-${Math.random()}`, item: currField });
          }

          continue;
        }

        // 🧩 Optionally ignore sort_order
        let fieldToCompare = currField;
        let prevToCompare = prevField;
        if (ignoreSortOrder) {
          const { sort_order, ...restCurr } = currField;
          const { sort_order: __, ...restPrev } = prevField;
          fieldToCompare = restCurr;
          prevToCompare = restPrev;
        }

        // Normalize for consistent comparison
        const normalizedCurr = sortObjectKeys(fieldToCompare);
        const normalizedPrev = sortObjectKeys(prevToCompare);
        const isDifferent =
          JSON.stringify(normalizedCurr) !== JSON.stringify(normalizedPrev);

        // 📝 Any field differences = update
        if (isDifferent || currField.moved) {
          changes.update.push({ id, item: currField });
        }

        // 🚫 Soft delete = add to delete list as well
        if (currField.deleted && !prevField.deleted) {
          changes.delete.push({ id, item: currField });
        }
      }

      return changes;
    },

    isTargetRowHorizontal(target) {
      if (!target) return false;

      return target.classList.contains('grid-col-span-1');
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

      try {
        const diffChanges = this.computeChanges({
          previousFields: this.formBuilder.originalFields,
          currentFields: this.formBuilder.dynamicFields,
        });

        const payload = {
          entity_type: entityType,
          changes: {
            create: diffChanges.create.map(({ item }) => {
              const { deleted, ...rest } = item;
              return rest;
            }),
            update: diffChanges.update.map(({ id, item }) => {
              const { deleted, ...rest } = item;
              return { id, item: rest };
            }),
            delete: diffChanges.delete
              .map(({ id }) => id)
              .filter(id => !id.toString().startsWith('temp-')), // only existing IDs
          },
        };

        const res = await api.post(`/admin/api/dynamic-fields/bulk-save`, payload);

        this.formBuilder.dynamicFields = res.data.fields;
        this.formBuilder.originalFields = deepClone(res.data.fields);
        this.resetHistory();
        this.showSnack(window.translations.fieldsSavedSuccessfully_);
      } catch (err) {
        console.error('Bulk save error:', err);
        this.showSnack(handleRequestError(err));
        throw err; // rethrow for confirm dialog
      } finally {
        this.ui.saving = false;
      }
    },

    closeDrawer(open) {
      this.ui.selectFieldTypeDialog = Boolean(open);
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
    isFieldActiveByName(name) {
      const matchingField = this.formBuilder.dynamicFields.find((field) => field?.name === name);

      return Boolean(matchingField?.active);
    },
    isFieldActiveAndHasContent(field, key, value) {
      if (!this.isFieldActive(field, key)) return false;
      if (Array.isArray(value)) return value.some((v) => !!v);
      return value != null && value !== '';
    },
    findFieldOptionByValue(field, value) {
      if (!Array.isArray(field.options)) return;

      return field.options.find((option) => option?.id === Number(value));
    },
    sortFields(fields) {
      return fields.sort((a, b) => {
        return a.sort_order - b.sort_order
      })
    },
    loadHistory(options) {
      if (options?.done) {
        this.infiniteScrollCallback = options.done;
      }

      const params = {
        page: this.formBuilder.historyState.page,
        per_page: this.formBuilder.historyState.per_page,
      };

      this.formBuilder.loading = true;

      api.get(`/admin/api/dynamic-fields/history/${options.entityType}`, { params })
        .then(response => {
          this.formBuilder.historyState.total = response.data.total;

          if (params.page === 1) {
            this.formBuilder.historyState.items = response.data.items;
          } else {
            this.formBuilder.historyState.items.push(...response.data.items);
          }

          const hasMore = this.formBuilder.historyState.items.length < response.data.total;
          if (hasMore) this.formBuilder.historyState.page++;

          options?.done?.(hasMore ? 'ok' : 'empty');
        })
        .catch(err => {
          console.error(err);
          options?.done?.('error');
        })
        .finally(() => {
          this.formBuilder.loading = false;
        });
    },
    resetHistory() {
      this.formBuilder.historyState = { items: [], total: 0, page: 1, per_page: 20 },
      this.infiniteScrollCallback?.('ok');
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
