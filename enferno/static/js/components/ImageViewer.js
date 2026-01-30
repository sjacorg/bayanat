const ImageViewer = Vue.defineComponent({
    props: ['media', 'mediaType'],
    data: () => {
      return {
        translations: window.translations,
        lg: {
            inline: null,
            fullscreen: null
        },
      };
    },
    unmounted() {
        this.destroyInlineLightbox();
        this.destroyFullscreenLightbox();
    },
    methods: {
        async loadLibraries() {
          await loadAsset([
            '/static/js/lightgallery/css/lg-rotate.css',
            '/static/js/lightgallery/css/lg-zoom.css',
            '/static/js/lightgallery/css/lg-thumbnail.css',
            '/static/js/lightgallery/css/lightgallery.css',
            '/static/js/lightgallery/plugins/rotate/lg-rotate.min.js',
            '/static/js/lightgallery/plugins/zoom/lg-zoom.min.js',
            '/static/js/lightgallery/plugins/thumbnail/lg-thumbnail.min.js',
            '/static/js/lightgallery/lightgallery.min.js'
          ]);
        },
        async requestFullscreen(nextOptions) {
            const el = this.$refs.imageViewer;
            if (!el) return;

            await this.loadLibraries()

            const defaultOptions = {
                plugins: [lgZoom, lgThumbnail, lgRotate],
                download: false,
                showZoomInOutIcons: true,
                actualSize: false,
                speed: 0,
                selector: '.media-item',
            }

            const options = { ...defaultOptions, ...nextOptions }
        
            this.lg.fullscreen = lightGallery(el, options);
            this.lg.fullscreen.openGallery(0); // Open the first image by default

            // Add an event listener to destroy the fullscreen lightbox on close
            this.lg.fullscreen.el.addEventListener('lgAfterClose', () => {
                this.destroyFullscreenLightbox();
            });

            // When the user rotates the image, it may overflow the preview container.
            // This is a workaround to force the image to fit within the container.
            this.addRotateListener(this.lg.fullscreen);
            this.setupZoomHack(this.lg.fullscreen);
        },
        async initInlineLightbox(nextOptions) {
            const el = this.$refs.imageViewer;
            if (!el) return;
            
            await this.loadLibraries()

            const defaultOptions = {
                plugins: [lgZoom, lgThumbnail, lgRotate],
                download: false,
                showZoomInOutIcons: true,
                actualSize: false,
                speed: 0,
                selector: '.media-item',
                container: el,
                closable: false,
            }

            const options = { ...defaultOptions, ...nextOptions }

            this.lg.inline = lightGallery(el, options);
            this.lg.inline.openGallery(0); // Open the first image by default

            // When the user rotates the image, it may overflow the preview container.
            // This is a workaround to force the image to fit within the container.
            this.addRotateListener(this.lg.inline);
            this.setupZoomHack(this.lg.inline);
        },
        addRotateListener(lgInstance) {
          if (!lgInstance?.el) return;
  
          ['lgRotateLeft', 'lgRotateRight'].forEach(evtName => {
            lgInstance.el.addEventListener(evtName, (evt) => {
              const rotate = evt.detail.rotate;
  
              const container = lgInstance.$content.firstElement;
              const imgWrapper = container.querySelector('.lg-img-rotate');
              const img = container.querySelector('img.lg-object');
  
              if (!container || !imgWrapper || !img) return;
  
              const { width: containerW, height: containerH } = container.getBoundingClientRect();
              const { naturalWidth: naturalW, naturalHeight: naturalH } = img;
  
              const isRotated = rotate % 180 !== 0;
              const imgW = isRotated ? naturalH : naturalW;
              const imgH = isRotated ? naturalW : naturalH;
  
              const scale = Math.min(containerW / imgW, containerH / imgH);
  
              // Image gets rotated, so we flip width/height
              if (isRotated) {
                imgWrapper.style.width = `${imgH * scale}px`;
                imgWrapper.style.height = `${imgW * scale}px`;
  
                const leftMargin = (containerW - imgWrapper.offsetWidth) / 2;
                const topMargin = (containerH - imgWrapper.offsetHeight) / 2;
  
                imgWrapper.style.marginLeft = `${leftMargin}px`;
                imgWrapper.style.marginTop = `${topMargin}px`;
              } else {
                // Reset any rotation-related dimensions
                ['width', 'height', 'marginLeft', 'marginTop'].forEach(prop => {
                  imgWrapper.style[prop] = null;
                });
              }
  
              img.style.maxWidth = '';
              img.style.maxHeight = '';
            });
          });
        },
        // HACK: Flip twice to fix zoom-drag not working after zoom in via button
        forceEnableDrag(lgInstance) {
          const flipBtn = lgInstance.$toolbar?.firstElement?.querySelector('#lg-flip-hor');
          if (flipBtn) {
            flipBtn.click();
            flipBtn.click();
          }
        },
        // Setup event listeners on zoom buttons to trigger drag fix
        setupZoomHack(lgInstance) {
          const zoomInBtn = lgInstance.$toolbar?.firstElement?.querySelector('.lg-zoom-in');
          const zoomOutBtn = lgInstance.$toolbar?.firstElement?.querySelector('.lg-zoom-out');

          const handler = () => this.forceEnableDrag(lgInstance);

          zoomInBtn?.addEventListener('click', handler);
          zoomOutBtn?.addEventListener('click', handler);
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
          async handler() {
            this.$nextTick(async () => {
              this.destroyInlineLightbox();
              await this.initInlineLightbox(); // re-init with latest DOM
            });
          }
        }
    },
    template: `
        <div ref="imageViewer">
            <a class="media-item h-100 block" :data-src="media.s3url">
                <img :src="media.s3url" class="w-100 h-100 bg-black" style="object-fit: contain;"></img>
            </a>
        </div>
      `,
  });
  