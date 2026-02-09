const ocrMixin = {
  data() {
    return {
      mediaDialog: {
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
        this.mediaDialog.loading = true;
        this.mediaDialog.show = true;

        api.get(`/admin/api/media/${id}`).then(response => {
            // Only update if dialog is still open
            if (this.mediaDialog.show) {
                this.mediaDialog.data = response.data;
                this.mediaDialog.data.ocr_status = this.$root.getEffectiveStatus(response.data);
            }
        }).catch(error => {
            console.error('Error loading media:', error);
            this.showSnack("{{ _('Error loading media') }}");
            this.mediaDialog.show = false;
        }).finally(() => {
            this.mediaDialog.loading = false;
        });
    },
    resetMediaDialog() {
        this.mediaDialog.show = false;
        this.mediaDialog.data = null;
        this.mediaDialog.loading = false;
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
