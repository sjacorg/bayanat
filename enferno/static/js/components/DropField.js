const DropField = Vue.defineComponent({
  props: {
    caption: String,
    samples: Array,
    modelValue: Array,
  },
  emits: ['update:modelValue', 'change'],
  data: function () {
    return {
      colmap: this.modelValue || [],
      disabled: false,
    };
  },

  watch: {
    modelValue(val) {
      this.colmap = val || [];
    },
    colmap: {
      handler: 'refresh',
      deep: true,
    },
  },

  mounted: function () {
    //this.broadcast();
  },

  methods: {
    refresh() {
      // restrict to one item
      if (this.colmap.length > 0) {
        this.disabled = true;
      } else {
        this.disabled = false;
      }
      this.broadcast();
    },

    broadcast() {
      this.$emit('update:modelValue', this.colmap);
      this.$emit('change', this.colmap);
    },
    removeMe(i) {
      let item = this.colmap.splice(i, 1);
      this.$root.returnToStack(item);
    },
  },
  template: `

    <v-sheet class="d-flex stripe-1 align-center  ma-2 pa-2" elevation="0">
      <h5 class="text-caption mr-1">{{ caption }}</h5>
      <v-card   variant="outlined">
        <draggable
            :disabled="disabled"
            tag="v-layout"
            v-model="colmap"
            item-key="id"
            @change="refresh"
            class="drag-area list-group"
            :group="{ name: 'columns', pull: false, put: true, ghostClass: 'ghost', animation: 100 }"
        >
          <template #item="{ element, index }">
            <v-chip size="small" closable
                    @click:close="removeMe(index)"
                    class="ma-1 list-group-item" dark :key="element.id"  color="primary">
              {{ element }}
            </v-chip>
          </template>
        </draggable>
      </v-card>
      <slot name="extra"></slot>
    </v-sheet>

  `,
});

export default DropField;