Vue.component('pop-date-field', {
    props: ['value', 'label'],

    data() {
        return {
            id: null,
            menu: false,
            pickerDate: this.value,
            textDate: this.value,
            errorMsg: null,
        };
    },

    created() {
        this.id = 'date' + this._uid;
        this.$emit('input', this.value);
    },

    methods: {
        isValidDate() {
            if (!this.pickerDate) return true;

            const regex = /^(19[5-9]\d|20[0-3]\d|2040)-\d{2}-\d{2}$/;
            const dateString = this.pickerDate.trim();

            if (!regex.test(dateString)) {
                this.errorMsg = 'Must be >1950 and <2040';
                return false;
            }

            if (isNaN(new Date(dateString).getTime())) {
                this.errorMsg = 'Invalid date format';
                return false;
            }

            return true; // Valid date
        },

        dateInputFieldEdited() {
            this.errorMsg = null;

            if (this.pickerDate && this.isValidDate()) {

                this.$emit('input', this.pickerDate);
            }

        },

    },

    watch: {
        pickerDate(val) {
            this.$emit('input', val);
        },

        value(val, old) {
            if (val !== old) {
                this.textDate = val;
                this.pickerDate = val;
            }
        },
    },

    template: `
      <v-menu
          v-model="menu"
          ref="dateMenu"
          transition="scale-transition"
          offset-y
          max-width="290px"
          min-width="290px"
          :close-on-content-click="false"
      >
      <template v-slot:activator="{ on, attrs }">
        <v-text-field
            @click:prepend="menu=true"
            dense
            v-model="textDate"
            type="date"
            min="1950-01-01"
            max="2040-01-01"
            placeholder="YYYY-MM-DD"
            onClick="event.preventDefault()"
            v-bind="attrs"
            :label="label"
            persistent-hint
            prepend-icon="mdi-calendar"
            clearable
            @blur="dateInputFieldEdited"
            
            :error-messages="errorMsg"
        />
      </template>

      <v-date-picker
          scrollable
          no-title
          min="1950-01-01"
          max="2040-01-01"
          v-model="pickerDate"
          @input="menu = false">
      </v-date-picker>
      </v-menu>
    `,
});
