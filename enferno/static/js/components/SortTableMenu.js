const SortTableMenu = Vue.defineComponent({
  props: {
    items: {
      type: Array,
      required: true,
      default: () => [],
    },
    sortItems: {
      type: Array,
      required: true,
      default: () => [],
    },
    selectedItem: {
      type: String,
    },
    selectedSortItem: {
      type: String,
    },
    disableSortItems: {
        type: Boolean,
        default: false,
    }
  },
  emits: [],
  data: () => ({
    translations: window.translations,
    sortItem: null,
    item: null
  }),
  template: `
        <div class="d-flex align-center ga-2">
            <div><v-icon>mdi-sort-variant</v-icon>{{ translations.dataSort_ }}</div>

            <v-menu :close-on-content-click="false">
                <template v-slot:activator="{ props, isActive }">
                    <v-select
                        color="blue"
                        variant="outlined"
                        v-bind="props"
                        readonly
                        hide-details
                        density="compact"
                        :focused="isActive"
                        :style="{ minWidth: '200px' }"
                    ></v-select>
                </template>

                <v-card border="info md opacity-100" class="mt-1" elevation="1">
                    <v-list v-model:selected="item" density="compact" variant="flat">
                        <v-list-subheader>{{ translations.dataType_ }}</v-list-subheader>
                        <v-list-item v-for="(item, index) in items" :key="index" :value="item.value" :active="false">
                            <v-list-item-title>
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
                    <v-list :disabled="disableSortItems" v-model:selected="sortItem" density="compact" class="pb-0">
                        <v-list-subheader>{{ translations.direction_ }}</v-list-subheader>
                        <v-list-item v-for="(item, index) in sortItems" :key="index" :value="item.value" :active="false">
                            <v-list-item-title>
                                <v-icon left small class="me-2">{{ item.icon }}</v-icon>
                                {{ item.title }}
                            </v-list-item-title>

                            <template v-slot:append="{ isSelected }">
                                <v-list-item-action class="flex-column align-end">
                                    <v-spacer></v-spacer>
                                    <v-icon v-if="isSelected" color="blue">mdi-check</v-icon>
                                </v-list-item-action>
                            </template>
                        </v-list-item>
                        <v-btn class="w-100 mt-2" tile color="blue">{{ translations.apply_ }}</v-btn>
                    </v-list>
                </v-card>
            </v-menu>
        </div>
      `,
});
