const ocrMixin = {
  data() {
    return {
      ocr: {
        dialog: {
          loading: false,
          show: false,
          data: null
        },
        statuses: {
          pending: { key: 'pending', text: window.translations.pending_, color: 'grey', icon: 'mdi-clock-outline' },
          processing: { key: 'processing', text: window.translations.processing_, color: 'blue', icon: 'mdi-cog-outline' },
          processed: { key: 'processed', text: window.translations.processed_, color: 'green', icon: 'mdi-check-circle-outline' },
          manual: { key: 'manual', text: window.translations.manuallyTranscribed_, color: 'indigo', icon: 'mdi-account-edit-outline' },
          cant_read: { key: 'cant_read', text: window.translations.cantRead_, color: 'brown', icon: 'mdi-eye-off-outline' },
          failed: { key: 'failed', text: window.translations.failed_, color: 'red', icon: 'mdi-close-circle-outline' },
          unsupported: { key: 'unsupported', text: window.translations.unsupported_, color: 'grey-darken-1', icon: 'mdi-file-cancel-outline' },
        },
      },
    };
  },
  computed: {
    selectableStatuses() {
      return ['pending', 'failed', 'cant_read'];
    },
    selectableFileTypes() {
      return ['image'];
    }
  },
  methods: {
    getStatusText(status) {
        return this.ocr.statuses[status]?.text || status;
    },
    getStatusColor(status) {
        return this.ocr.statuses[status]?.color || 'grey';
    },
    getStatusIcon(status) {
        return this.ocr.statuses[status]?.icon || 'mdi-help-circle-outline';
    },
    showOcrDialog(id) {
        this.ocr.dialog.loading = true;
        this.ocr.dialog.show = true;

        api.get(`/admin/api/media/${id}`).then(response => {
            // Only update if dialog is still open
            if (this.ocr.dialog.show) {
                this.ocr.dialog.data = response.data;
                this.ocr.dialog.data.ocr_status = this.$root.getEffectiveStatus(response.data);
            }
        }).catch(error => {
            console.error('Error loading media:', error);
            this.showSnack("{{ _('Error loading media') }}"); // TODO: Translate this
            this.ocr.dialog.show = false;
        }).finally(() => {
            this.ocr.dialog.loading = false;
        });
    },
    resetOcrDialog() {
        this.ocr.dialog.show = false;
        this.ocr.dialog.data = null;
        this.ocr.dialog.loading = false;
    },
    countWords(text) {
      if (!text || !text.trim()) return 0;
      return text.trim().split(/\s+/).filter(word => word.length > 0).length;
    },
    getEffectiveStatus(item, processingIds) {
      // Check if file type is supported first
      const fileType = this.$root.getFileTypeFromMimeType(item.fileType);
      if (!this.selectableFileTypes.includes(fileType)) {
        return 'unsupported';
      }
      
      const ocrStatus = item.extraction?.status || 'pending';
      
      if (processingIds?.has(item.id)) {
        return 'processing';
      }
      
      if (item.extraction?.manual && ocrStatus === 'processed') {
        return 'manual';
      }
      
      return ocrStatus;
    },
  }
};
