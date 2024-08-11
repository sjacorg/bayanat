const PopDateTimeField = Vue.defineComponent({
  props: {
    modelValue: {
      type: String,
      default: '',
    },
    label: {
      type: String,
    },
    timeLabel: {
      type: String,
      default: 'Time',
    },
  },
  emits: ['update:modelValue'],
  components: {
    PopDateField,
  },
  data: function () {
    return {
      dt: this.modelValue ? dayjs(this.modelValue).toDate() : null,
      tm: this.modelValue ? dayjs(this.modelValue).format('HH:mm') : null,
    };
  },
  watch: {
    dt: function () {
      this.emitInput();
    },

    tm: function () {
        this.emitInput();
    },

    modelValue: function (newVal, oldVal) {
      if (newVal) {
        this.dt = dayjs(newVal).toDate();
        this.tm = dayjs(newVal).format('HH:mm');
      } else {
        this.dt = null;
        this.tm = null;
      }
    },
  },
  created() {
    //this.emitInput();
  },

  computed: {
    datetime() {
      if (this.dt && this.tm) {
        // Combine dt and tm into a datetime string
        return dayjs(this.dt).format('YYYY-MM-DD') + 'T' + this.tm;
      } else if (this.dt) {
        // Default time to 00:00 if no time is selected
        return dayjs(this.dt).format('YYYY-MM-DD') + 'T00:00';
      } else {
        return null;
      }
    },
  },

  methods: {
    emitInput() {
      if (dayjs(this.datetime).isValid()) {
        this.$emit('update:modelValue', this.datetime);
      } else {
        this.$emit('update:modelValue', null);
      }
    },
  },

  template: `
      <v-sheet class="d-flex">
        <pop-date-field :label="label" v-bind="$attrs" v-model="dt"></pop-date-field>
        <v-text-field  variant="plain"  class="mt-2 ml-2 flex-0-0" @update:modelValue="emitInput" v-model="tm" type="time" :label="timeLabel"></v-text-field>
      </v-sheet>
    `,
});
