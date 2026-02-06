const LoadingComponent = Vue.defineComponent({
  template: `
    <v-skeleton-loader
        type="paragraph"
    ></v-skeleton-loader>
  `,
});

window.LoadingComponent = LoadingComponent;
