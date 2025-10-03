const PopDateField = {
  props: ['modelValue', 'label', 'rules'],
  emits: ['update:modelValue'],
  data: () => ({
    validationRules: validationRules
  }),
  computed: {
    date: {
      get() {
        return dayjs(this.modelValue).isValid() ? dayjs(this.modelValue).toDate() : null;
      },
      set(value) {
        if (value === '') {
          this.$emit('update:modelValue', null);
        } else {
          this.$emit('update:modelValue', this.$root.formatDate(value, this.$root.dateFormats.isoDatetime) );
        }
      }
    }
  },
  template: `
    <v-date-input :placeholder="$root.dateFormats.standardDate" :display-format="(date) => $root.formatDate(date, $root.dateFormats.standardDate)" :input-format="$root.dateFormats.standardDate" class="flex-fill" :label="label" v-bind="$attrs" :rules="rules ?? [validationRules.date()]" variant="outlined" hide-actions v-model="date" @click:clear="$emit('update:modelValue', null)" clearable></v-date-input>
  `
};
