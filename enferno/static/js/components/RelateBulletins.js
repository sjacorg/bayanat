const RelateBulletins = Vue.defineComponent({
  mixins: [relatedSearchMixin],
  data: () => ({
    searchEndpoint: `/admin/api/bulletins/?mode=2`,
    queryFormat: 'array',
  }),
  template: /*html*/ `
    <relate-items-template
      v-model:visible="visible"
      :dialog-props="dialogProps"
      :loading="loading"
      :results="results"
      @search="reSearch"
      @load-more="loadMore"
      :has-more="hasMore"
      :multi-relation="$root.bulletinRelationMultiple"
      :relation-types="$root.bulletinRelationTypes"
      @relate="relateItem"
    >
      <template v-if="$slots.actions" #actions>
        <slot name="actions"></slot>
      </template>
      <template #search-box>
        <bulletin-search-box 
          v-model="q"
          @search="reSearch"
          :extra-filters="false"
          :show-op="false"
        ></bulletin-search-box>
      </template>
      <template #results-list>
        <bulletin-result
          v-for="(item, i) in results"
          :key="i"
          :bulletin="item"
          :show-hide="true"
        >
          <template #actions>
            <v-tooltip location="bottom">
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  @click="$root.openConfirmRelationDialog(item)"
                  color="primary"
                  variant="elevated"
                  icon="mdi-link-plus"
                  size="small"
                ></v-btn>
              </template>
              {{ translations.addAsRelated_ }}
            </v-tooltip>
          </template>
        </bulletin-result>
      </template>
    </relate-items-template>
    `,
});
