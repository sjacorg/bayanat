const ImageViewer = Vue.defineComponent({
    props: {
        media: {
            type: Object,
            required: true
        },
        mediaType: {
            type: String,
            default: 'image'
        },
        mode: {
            type: String,
            default: 'inline', // 'inline' or 'click'
            validator: (value) => ['inline', 'click'].includes(value)
        },
        initialOrientation: {
            type: Number,
            default: 0,
        },
        // Additional options to pass to lightGallery
        galleryOptions: {
            type: Object,
            default: () => ({})
        }
    },
    emits: ['orientation-changed'],
    data() {
        return {
            translations: window.translations,
            lg: {
                inline: null,
                fullscreen: null
            },
            pluginsMap: {
                'lgZoom': lgZoom,
                'lgThumbnail': lgThumbnail,
                'lgRotate': lgRotate,
            }
        };
    },
    computed: {
        thumbnailUrl() {
            return this.media.thumbnail_url || this.media.s3url;
        },
        fullSizeUrl() {
            return this.media.url || this.media.s3url;
        },
        pluginsList() {
            return Object.values(this.pluginsMap);
        }
    },
    mounted() {
        if (this.mode === 'inline') {
            this.$nextTick(() => {
                this.initInlineLightbox();
            });
        }
    },
    unmounted() {
        this.destroyInlineLightbox();
        this.destroyFullscreenLightbox();
    },
    methods: {
        getRotatePlugin(lgInstance) {
            if (!lgInstance?.plugins) return null;
            const rotateIndex = Object.keys(this.pluginsMap).indexOf('lgRotate');
            return lgInstance.plugins[rotateIndex];
        },
        
        applyInitialRotation(lgInstance) {
            if (this.initialOrientation === 0) return;
            
            const handler = (e) => {
                const rotatePlugin = this.getRotatePlugin(lgInstance);
                const index = e.detail.index;
                
                if (rotatePlugin?.rotateValuesList?.[index]) {
                    rotatePlugin.rotateValuesList[index].rotate = this.initialOrientation;
                    rotatePlugin.applyStyles();
                }
            };
            
            lgInstance.el.addEventListener('lgSlideItemLoad', handler, { once: true });
        },
        
        handleClick() {
            if (this.mode === 'click') {
                this.requestFullscreen();
            }
        },
        
        requestFullscreen(nextOptions) {
            const el = this.$refs.imageViewer;
            if (!el) return;

            const defaultOptions = {
                plugins: this.pluginsList,
                download: false,
                showZoomInOutIcons: true,
                actualSize: false,
                speed: 0,
                selector: '.media-item',
            };

            const options = { ...defaultOptions, ...this.galleryOptions, ...nextOptions };
        
            this.lg.fullscreen = lightGallery(el, options);
            this.lg.fullscreen.openGallery(0);

            this.applyInitialRotation(this.lg.fullscreen);

            this.lg.fullscreen.el.addEventListener('lgAfterClose', () => {
                this.destroyFullscreenLightbox();
            }, { once: true });

            this.addRotateListener(this.lg.fullscreen);
            this.setupZoomHack(this.lg.fullscreen);
        },
        
        initInlineLightbox(nextOptions) {
            const el = this.$refs.imageViewer;
            if (!el) return;

            const defaultOptions = {
                plugins: this.pluginsList,
                download: false,
                showZoomInOutIcons: true,
                actualSize: false,
                speed: 0,
                selector: '.media-item',
                container: el,
                closable: false,
            };

            const options = { ...defaultOptions, ...this.galleryOptions, ...nextOptions };
        
            this.lg.inline = lightGallery(el, options);
            this.lg.inline.openGallery(0);

            this.applyInitialRotation(this.lg.inline);

            this.addRotateListener(this.lg.inline);
            this.setupZoomHack(this.lg.inline);
        },
        
        addRotateListener(lgInstance) {
            if (!lgInstance?.el) return;

            const handleRotate = (evt) => {
                const rotate = evt.detail.rotate;
                const container = lgInstance.$content.firstElement;
                const imgWrapper = container?.querySelector('.lg-img-rotate');
                const img = container?.querySelector('img.lg-object');

                if (!container || !imgWrapper || !img) return;

                this.$emit('orientation-changed', rotate);

                const { width: containerW, height: containerH } = container.getBoundingClientRect();
                const { naturalWidth: naturalW, naturalHeight: naturalH } = img;

                const isRotated = rotate % 180 !== 0;
                const imgW = isRotated ? naturalH : naturalW;
                const imgH = isRotated ? naturalW : naturalH;
                const scale = Math.min(containerW / imgW, containerH / imgH);

                if (isRotated) {
                    imgWrapper.style.width = `${imgH * scale}px`;
                    imgWrapper.style.height = `${imgW * scale}px`;
                    imgWrapper.style.marginLeft = `${(containerW - imgWrapper.offsetWidth) / 2}px`;
                    imgWrapper.style.marginTop = `${(containerH - imgWrapper.offsetHeight) / 2}px`;
                } else {
                    // Reset orientation-related dimensions
                    ['width', 'height', 'marginLeft', 'marginTop'].forEach(prop => {
                        imgWrapper.style[prop] = null;
                    });
                }

                img.style.maxWidth = '';
                img.style.maxHeight = '';
            };

            ['lgRotateLeft', 'lgRotateRight'].forEach(evtName => {
                lgInstance.el.addEventListener(evtName, handleRotate);
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
            immediate: false,
            handler() {
                this.$nextTick(() => {
                    this.destroyInlineLightbox();
                    this.destroyFullscreenLightbox();
                });
                if (this.mode === 'inline') {
                    this.$nextTick(() => {
                        this.initInlineLightbox();
                    });
                }
            }
        }
    },
    template: `
        <div ref="imageViewer">
            <a 
                class="media-item h-100 block" 
                :class="{ 'cursor-pointer': mode === 'click' }"
                :data-src="fullSizeUrl"
                @click.prevent="handleClick"
            >
                <img 
                    :src="mode === 'click' ? thumbnailUrl : fullSizeUrl" 
                    class="w-100 h-100 bg-black" 
                    style="object-fit: contain;"
                />
            </a>
        </div>
    `,
});