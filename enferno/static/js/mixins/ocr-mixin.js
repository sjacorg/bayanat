const ocrMixin = {
  data() {
    return {
      ocrDialog: {
        loading: false,
        show: false,
        data: null
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
    showOcrDialog(id) {
        this.ocrDialog.loading = true;
        this.ocrDialog.show = true;

        api.get(`/admin/api/media/${id}`).then(response => {
            // Only update if dialog is still open
            if (this.ocrDialog.show) {
                this.ocrDialog.data = response.data;
                this.ocrDialog.data.ocr_status = this.$root.getEffectiveStatus(response.data);
            }
        }).catch(error => {
            console.error('Error loading media:', error);
            this.showSnack("{{ _('Error loading media') }}");
            this.ocrDialog.show = false;
        }).finally(() => {
            this.ocrDialog.loading = false;
        });
    },
    resetOcrDialog() {
        this.ocrDialog.show = false;
        this.ocrDialog.data = null;
        this.ocrDialog.loading = false;
    },
    countWords(text) {
      if (!text || !text.trim()) return 0;
      return text.trim().split(/\s+/).filter(word => word.length > 0).length;
    },
    getEffectiveStatus(item, processingIds) {
      // Check if currently being processed
      if (processingIds?.has(item.id)) {
          return 'processing';
      }
      
      // Show 'manual' status for manually transcribed items
      if (item.extraction?.manual && item.ocr_status === 'processed') {
          return 'manual';
      }
      return item.ocr_status;
    },
  }
};
