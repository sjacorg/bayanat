/*!
 * FilePondPluginImageOverlay 1.0.4
 * Licensed under MIT, https://opensource.org/licenses/MIT/
 * Please visit undefined for details.
 */

/* eslint-disable */

(function(global, factory) {
  typeof exports === 'object' && typeof module !== 'undefined'
    ? (module.exports = factory())
    : typeof define === 'function' && define.amd
    ? define(factory)
    : ((global = global || self),
      (global.FilePondPluginImageOverlay = factory()));
})(this, function() {
  'use strict';

  const isImage = file => /^image/.test(file.type);

  const getImageSize = (url, cb) => {
    let image = new Image();

    image.onload = () => {
      const width = image.naturalWidth;
      const height = image.naturalHeight;
      image = null;
      cb(width, height);
    };

    image.src = url;
  };

  /**
   * Register the full size overlay so that it will be instantiated upon clicking the image preview wrapper
   */

  const registerFullSizeOverlay = (item, el, labelButtonOverlay) => {
    const info = el.querySelector('.filepond--file-info-main'),
      magnifyIcon = getMagnifyIcon(labelButtonOverlay);
    info.prepend(magnifyIcon);
    magnifyIcon.addEventListener('click', () => createFullSizeOverlay(item)); // in case the image preview plugin is loaded, make the preview clickable as well.
    // we don't have a hook to determine whether that plugin is loaded, as listening to FilePond:pluginloaded doesn't work

    window.setTimeout(() => {
      const imagePreview = el.querySelector('.filepond--image-preview');

      if (imagePreview) {
        imagePreview.classList.add('clickable');
        imagePreview.addEventListener('click', () =>
          createFullSizeOverlay(item)
        );
      }
    }, 1000);
  };
  const getMagnifyIcon = labelButtonOverlay => {
    let icon = document.createElement('span');
    icon.className = 'filepond--magnify-icon';
    icon.title = labelButtonOverlay;
    return icon;
  };
  /**
   * Generate the full size overlay and present the image in it.
   */

  const createFullSizeOverlay = item => {
    const overlay = document.createElement('div');
    overlay.className = 'filepond--fullsize-overlay';
    const imgContainer = document.createElement('div');
    const imgUrl = URL.createObjectURL(item.file);
    imgContainer.className = 'image-container';
    imgContainer.style.backgroundImage = 'url(' + imgUrl + ')';
    determineImageOverlaySize(imgUrl, imgContainer);
    let body = document.getElementsByTagName('body')[0];
    overlay.appendChild(imgContainer);
    body.appendChild(overlay);
    overlay.addEventListener('click', () => overlay.remove());
  };
  /**
   * Determines whether the image is larger than the viewport.
   * If so, set the backgroundSize to 'contain' to scale down the image so it fits the overlay.
   */

  const determineImageOverlaySize = (imgUrl, imgContainer) => {
    const w = Math.max(
        document.documentElement.clientWidth,
        window.innerWidth || 0
      ),
      h = Math.max(
        document.documentElement.clientHeight,
        window.innerHeight || 0
      );
    getImageSize(imgUrl, (width, height) => {
      if (width > w || height > h) {
        imgContainer.style.backgroundSize = 'contain';
      }
    });
  };

  /**
   * Image Overlay Plugin
   */

  const plugin = fpAPI => {
    const { addFilter, utils } = fpAPI;
    const { Type, createRoute } = utils; // called for each view that is created right after the 'create' method

    addFilter('CREATE_VIEW', viewAPI => {
      // get reference to created view
      const { is, view, query } = viewAPI; // only hook up to item view

      if (!is('file')) {
        return;
      } // create the image overlay plugin, but only do so if the item is an image

      const didLoadItem = ({ root, props }) => {
        const { id } = props;
        const item = query('GET_ITEM', id);

        if (!item || item.archived || !isImage(item.file)) {
          return;
        }

        const labelButtonOverlay = root.query('GET_LABEL_BUTTON_IMAGE_OVERLAY');
        registerFullSizeOverlay(item, root.element, labelButtonOverlay); // now ready

        root.dispatch('DID_MEDIA_PREVIEW_CONTAINER_CREATE', {
          id
        });
      }; // start writing

      view.registerWriter(
        createRoute(
          {
            DID_LOAD_ITEM: didLoadItem
          },
          ({ root, props }) => {
            const { id } = props;
            const item = query('GET_ITEM', id); // don't do anything while not an image file or hidden

            if (!isImage(item.file) || root.rect.element.hidden) return;
          }
        )
      );
    }); // expose plugin

    return {
      options: {
        labelButtonImageOverlay: ['Open image in overlay', Type.STRING]
      }
    };
  }; // fire pluginloaded event if running in browser, this allows registering the plugin when using async script tags

  const isBrowser =
    typeof window !== 'undefined' && typeof window.document !== 'undefined';

  if (isBrowser) {
    document.dispatchEvent(
      new CustomEvent('FilePond:pluginloaded', {
        detail: plugin
      })
    );
  }

  return plugin;
});
