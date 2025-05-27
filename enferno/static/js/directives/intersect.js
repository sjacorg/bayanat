const intersect = {
    mounted(el, binding) {
      const options = binding.value?.options || {};
      const callback = binding.value?.callback;
  
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          callback && callback();
        }
      }, options);

      el._observer = observer;
      observer.observe(el);
    },
    unmounted(el) {
      if (el._observer) {
        el._observer.disconnect();
        delete el._observer;
      }
    }
  };