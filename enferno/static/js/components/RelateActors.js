const RelateActors = Vue.defineComponent({
  mixins: [relatedSearchMixin],
  data: () => ({
    searchEndpoint: `/admin/api/actors/?mode=2`,
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
      :multi-relation="$root.actorRelationMultiple"
      :relation-types="$root.actorRelationTypes"
      @relate="relateItem"
    >
      <template v-if="$slots.actions" #actions>
        <slot name="actions"></slot>
      </template>
      <template #search-box>
        <actor-search-box 
          v-model="q"
          @search="reSearch"
          :extra-filters="false"
          :show-op="false"
        ></actor-search-box>
      </template>
      <template #results-list>
        <actor-result
          v-for="(item, i) in results"
          :key="i"
          :actor="item"
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
        </actor-result>
      </template>
    </relate-items-template>
    `,
});
