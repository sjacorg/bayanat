// Only one date picker may be open at a time: opening one closes the previous, otherwise the
// stale menu keeps focus and the new field needs several clicks (two From/To fields side by side).
let openDateField = null;

const PopDateField = {
  props: ['modelValue', 'label', 'rules'],
  emits: ['update:modelValue'],
  data: () => ({
    validationRules: validationRules,
    menu: false,
  }),
  watch: {
    menu(open) {
      if (open) {
        if (openDateField && openDateField !== this) openDateField.menu = false;
        openDateField = this;
      } else if (openDateField === this) {
        openDateField = null;
      }
    },
  },
  beforeUnmount() {
    if (openDateField === this) openDateField = null;
  },
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
    <v-date-input :placeholder="$root.dateFormats.standardDate" :display-format="(date) => $root.formatDate(date, $root.dateFormats.standardDate)" :input-format="$root.dateFormats.standardDate" class="flex-fill" :label="label" v-bind="$attrs" :rules="rules ?? [validationRules.date()]" variant="outlined" hide-actions v-model="date" v-model:menu="menu" @click:clear="$emit('update:modelValue', null)" clearable></v-date-input>
  `
};
