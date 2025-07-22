const ImageViewer = Vue.defineComponent({
    props: ['media', 'mediaType', 'class'],
    data: () => ({
      translations: window.translations,
      lg: {
        inline: null,
        fullscreen: null,
      },
    }),
    unmounted() {
      this.destroyInlineLightbox();
      this.destroyFullscreenLightbox();
    },
    methods: {
      requestFullscreen(nextOptions) {
        const el = this.$refs.imageViewer;
        if (!el) return;
  
        const defaultOptions = {
          plugins: [lgZoom, lgThumbnail, lgRotate],
          download: false,
          showZoomInOutIcons: true,
          actualSize: false,
          speed: 0,
          selector: '.media-item',
        };
  
        const options = { ...defaultOptions, ...nextOptions };
  
        this.lg.fullscreen = lightGallery(el, options);
        this.lg.fullscreen.openGallery(0);
  
        // Add rotate event listener (same as inline)
        this.addRotateListener(this.lg.fullscreen);
  
        this.lg.fullscreen.el.addEventListener('lgAfterClose', () => {
          this.destroyFullscreenLightbox();
        });
      },
      initInlineLightbox(nextOptions) {
        const el = this.$refs.imageViewer;
        if (!el) return;
  
        const defaultOptions = {
          plugins: [lgZoom, lgThumbnail, lgRotate],
          download: false,
          showZoomInOutIcons: true,
          actualSize: false,
          speed: 0,
          selector: '.media-item',
          container: el,
          closable: false,
        };
  
        const options = { ...defaultOptions, ...nextOptions };
  
        this.lg.inline = lightGallery(el, options);
        this.lg.inline.openGallery(0);
  
        // Add rotate event listener (same as fullscreen)
        this.addRotateListener(this.lg.inline);
      },
      addRotateListener(lgInstance) {
        if (!lgInstance || !lgInstance.el) return;
      
        // Listen for both rotate left and rotate right events
        ['lgRotateLeft', 'lgRotateRight'].forEach(evtName => {
          lgInstance.el.addEventListener(evtName, (evt) => {
            const rotate = evt.detail.rotate; // Rotation angle in degrees (0, 90, 180, 270)

            const c = evt.target.closest('.lg-outer');
      
            const container = lgInstance.el.querySelector('.lg-content');
            const imgWrapper = lgInstance.el.querySelector('.lg-img-rotate');
            const img = lgInstance.el.querySelector('img.lg-object');

            if (!container || !imgWrapper || !img) return;
      
            const { width: containerW, height: containerH } = container.getBoundingClientRect();
            const { naturalWidth: naturalW, naturalHeight: naturalH } = img;
      
            // Check if image is rotated by 90 or 270 degrees (dimensions swap)
            const isRotated = rotate % 180 !== 0;
            const imgW = isRotated ? naturalH : naturalW;
            const imgH = isRotated ? naturalW : naturalH;
      
            // Calculate scale to fit the image inside the container
            const scale = Math.min(containerW / imgW, containerH / imgH);

            if (isRotated) {
              // Apply scaled width and height, swapping due to rotation
              imgWrapper.style.width = `${imgH * scale}px`;
              imgWrapper.style.height = `${imgW * scale}px`;
      
              // Center the image wrapper inside the container
              const leftMargin = (containerW - imgWrapper.offsetWidth) / 2;
              const topMargin = (containerH - imgWrapper.offsetHeight) / 2;
      
              imgWrapper.style.marginLeft = `${leftMargin}px`;
              imgWrapper.style.marginTop = `${topMargin}px`;
            } else {
              // Reset styles when image is not rotated
              ['width', 'height', 'marginLeft', 'marginTop'].forEach(prop => {
                imgWrapper.style[prop] = null;
              });
            }
      
            // Remove any max size constraints on the image itself
            img.style.maxWidth = '';
            img.style.maxHeight = '';
          });
        });
      },      
      destroyInlineLightbox() {
        this.lg.inline?.destroy();
        this.lg.inline = null;
      },
      destroyFullscreenLightbox() {
        this.lg.fullscreen?.destroy();
        this.lg.fullscreen = null;
      },
    },
    watch: {
      media: {
        deep: true,
        immediate: true,
        handler() {
          this.$nextTick(() => {
            this.destroyInlineLightbox();
            this.initInlineLightbox();
          });
        }
      }
    },
    template: `
      <div ref="imageViewer" class="class">
        <a class="media-item h-100 block" :data-src="media.s3url">
          <img :src="media.s3url" class="w-100 h-100 bg-black" style="object-fit: contain;" />
        </a>
      </div>
    `,
  });
  