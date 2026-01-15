const SortTableMenu = Vue.defineComponent({
  props: {
    items: {
      type: Array,
      required: true,
      validator: (items) => items.every((i) => i.value && i.title),
    },
    sortItems: {
      type: Array,
      required: true,
      validator: (items) => items.every((i) => i.value && i.title),
    },
    modelValue: {
      type: Object,
      default: () => ({ sortBy: 'id', sortDirection: 'desc' }),
    },
  },
  emits: ['update:modelValue', 'apply'],
  data() {
    return {
      translations: window.translations,
      menuOpen: false,
      localSortBy: [this.modelValue.sortBy],
      localSortDirection: [this.modelValue.sortDirection],
    };
  },
  computed: {
    selectedItem() {
      return this.items.find((i) => i.value === this.localSortBy[0]);
    },
    sortItem() {
      return this.sortItems.find((i) => i.value === this.localSortDirection[0]);
    },
    displayText() {
      const isDefault = this.localSortBy?.[0] === 'id' && this.localSortDirection?.[0] === 'desc';

      if (!this.selectedItem || !this.sortItem) return '';

      const text = `${this.selectedItem.title} ${this.sortItem.title}`;
      return isDefault ? `${text} (${this.translations.default_})` : text;
    },
    buttonWidth() {
      const extraSpace = 2;

      return `${this.displayText.length + extraSpace}ch`
    }
  },
  watch: {
    modelValue: {
      handler(newVal) {
        this.localSortBy = [newVal.sortBy];
        this.localSortDirection = [newVal.sortDirection];
      },
    },
  },
  methods: {
    applySort() {
      const payload = {
        sortBy: this.localSortBy[0],
        sortDirection: this.localSortDirection[0],
      };

      this.$emit('update:modelValue', payload);
      this.$emit('apply', payload);
      this.menuOpen = false;
    },
  },
  template: `
        <div class="d-flex align-center ga-2">
            <div class="d-flex align-center text-medium-emphasis ga-1"><v-icon>mdi-sort-variant</v-icon><div class="text-body-2 font-weight-medium text-no-wrap">{{ translations.dataSort_ }}</div></div>

            <v-menu v-model="menuOpen" :close-on-content-click="false">
                <template v-slot:activator="{ props, isActive }">
                    <v-text-field
                        :value="displayText"
                        color="blue"
                        :class="['sort-table-menu', { 'sort-table-menu--focused': isActive }]"
                        variant="outlined"
                        v-bind="props"
                        readonly
                        hide-details
                        density="compact"
                        min-width="200"
                        :width="buttonWidth"
                        :append-inner-icon="isActive ? 'mdi-menu-up' : 'mdi-menu-down'"
                    ></v-text-field>
                </template>

                <v-card border="info sm opacity-100" class="mt-1" elevation="1">
                    <v-list v-model:selected="localSortBy" mandatory density="compact" variant="flat">
                        <v-list-subheader class="text-caption font-weight-medium">{{ translations.dataType_ }}</v-list-subheader>
                        <v-list-item v-for="(item, index) in items" :key="index" :value="item.value" :active="false" min-height="34">
                            <v-list-item-title class="text-body-2">
                                {{ item.title }}
                                <template v-if="item.default">({{ translations.default_ }})</template>
                            </v-list-item-title>

                            <template v-slot:append="{ isSelected }">
                                <v-list-item-action class="flex-column align-end">
                                    <v-spacer></v-spacer>
                                    <v-icon v-if="isSelected" color="blue">mdi-check</v-icon>
                                </v-list-item-action>
                            </template>
                        </v-list-item>
                    </v-list>
                    <v-divider class="border-opacity-25"></v-divider>
                    <v-list :disabled="selectedItem?.type === 'date'" mandatory v-model:selected="localSortDirection" density="compact" class="pb-0">
                        <v-list-subheader class="text-caption font-weight-medium">{{ translations.direction_ }}</v-list-subheader>
                        <v-list-item v-for="(item, index) in sortItems" :key="index" :value="item.value" :active="false" min-height="34">
                            <v-list-item-title class="text-body-2">
                                <v-icon left small class="me-2">{{ item.icon }}</v-icon>
                                {{ item.title }}
                            </v-list-item-title>

                            <template v-if="selectedItem?.type !== 'date'" v-slot:append="{ isSelected }">
                                <v-list-item-action class="flex-column align-end">
                                    <v-spacer></v-spacer>
                                    <v-icon v-if="isSelected" color="blue">mdi-check</v-icon>
                                </v-list-item-action>
                            </template>
                        </v-list-item>
                    </v-list>
                    <v-btn @click="applySort()" class="w-100 mt-2" tile color="blue">{{ translations.apply_ }}</v-btn>
                </v-card>
            </v-menu>
        </div>
      `,
});
