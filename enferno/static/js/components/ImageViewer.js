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
    mounted() {
        this.initInlineLightbox();
    },
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
            }

            const options = { ...defaultOptions, ...nextOptions }
        
            this.lg.fullscreen = lightGallery(el, options);
            this.lg.fullscreen.openGallery(0); // Open the first image by default

            // Add an event listener to destroy the fullscreen lightbox on close
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
            }

            const options = { ...defaultOptions, ...nextOptions }
        
            this.lg.inline = lightGallery(el, options);
            this.lg.inline.openGallery(0); // Open the first image by default
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
    template: `
        <div ref="imageViewer">
            <a class="media-item h-100 block" :data-src="media.s3url">
                <img :src="media.s3url" class="w-100 h-100 bg-black" style="object-fit: cover;"></img>
            </a>
        </div>
      `,
  });
  