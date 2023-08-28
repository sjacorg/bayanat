Vue.component('pop-date-range-field', {
  props: ['value', 'label'],

  data() {
    return {
      id: null,
      menu: false,
    };
  },

  created() {
    this.id = 'dateRange' + this._uid;
    this.$emit('input', this.value);
  },

  computed: {
    dateRangeFormatted() {
      // Don't display if no value
      if (!this.value) {
        return null;
      }

      // Display single value if one date
      if (this.value.length === 1) {
        return this.value[0];
      }

      // If same date selected only show one, else range
      return this.value[0] === this.value[1] ? this.value[0] : this.value.join(' - ');
    },
  },

  watch: {
    value(val) {

      // Emit empty value if dates cleared
      if (!val) {
        this.$emit('input', val);
        return;
      }

      // allow backward selection
      if (new Date(val[1]) < new Date(val[0])) {
        [val[0], val[1]] = [val[1], val[0]]

      }

      // Valid date range
      if (val.length === 2) {
        this.$emit('input', val);
        this.menu = false;
      }
    },

    menu(isOpen) {
      if (!isOpen) {
        // Edge case where user selects date range,
        // then selects a single date & closes menu
        // handle as if single date selected
        if (this.value && this.value.length === 1) {
          this.$emit('input', [this.value[0], this.value[0]]);
        }
      }
    },
  },

  template: /* HTML */ `
    <v-menu
      v-model="menu"
      ref="dateRangeMenu"
      transition="scale-transition"
      offset-y
      max-width="290px"
      min-width="290px"
      :close-on-content-click="false"
    >
      <template v-slot:activator="{ on, attrs }">
        <v-text-field
          readonly
          @click:prepend="menu=true"
          @click="menu=true"
          dense
          v-model="dateRangeFormatted"
          onClick="event.preventDefault()"
          v-bind="attrs"
          :label="label"
          
          prepend-icon="mdi-calendar"
          clearable
          @click:clear="value = null"
            hint="Select a single date or a range"
            persistent-hint
        ></v-text-field>
      </template>

      <v-date-picker
        range
        scrollable
        no-title
        min="1950-01-01"
        max="2040-01-01"
        v-model="value"
      >
        <v-spacer></v-spacer>
        <v-btn text color="primary" @click="value = null">Clear</v-btn>
      </v-date-picker>
    </v-menu>
  `,
});
