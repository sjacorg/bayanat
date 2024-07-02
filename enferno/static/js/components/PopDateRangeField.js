const PopDateRangeField = {
  props: ['modelValue', 'label'],
  emits: ['update:modelValue'],

  computed: {
    dates: {
      get() {
        if (this.modelValue) {
          return this.modelValue.map(dateStr => this.parseDate(dateStr));
        }
        return [];
      },
      set(values) {
        if (!values || values.length === 0) {
          this.$emit('update:modelValue', []);
        } else {
          const sortedDates = values.sort((a, b) => a - b);
          const limitedDates = sortedDates.length > 1 ? [sortedDates[0], sortedDates[sortedDates.length - 1]] : sortedDates;
          this.$emit('update:modelValue', limitedDates.map(date => this.formatDate(date)));
        }
      }
    }
  },

  methods: {
    formatDate(date) {
      return date ? dayjs(date).format('YYYY-MM-DD') : '';
    },
    parseDate(dateStr) {
      return dateStr ? dayjs(dateStr).toDate() : null;
    }
  },

  template: `
    <v-date-input multiple="range" :label="label" variant="outlined" v-model="dates" @click:clear="$emit('update:modelValue', [])" clearable></v-date-input>
  `
};
