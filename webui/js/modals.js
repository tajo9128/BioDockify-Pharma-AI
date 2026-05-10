// Import the component loader and page utilities
import { importComponent } from "/js/components.js";
import { callJsExtensions } from "/js/extensions.js";
import { store as rightCanvasStore } from "/components/canvas/right-canvas-store.js";

// Modal functionality
const modalStack = [];
const EXPLICIT_CLOSE_MODAL_PATHS = new Set([
  "plugins/_browser/webui/main.html",
  "plugins/_office/webui/main.html",
]);
const SINGLE_VISIBLE_MODAL_SURFACE_PATHS = new Set([
  "plugins/_browser/webui/main.html",
  "plugins/_office/webui/main.html",
]);
const CANVAS_SURFACE_MODAL_GROUP = "canvas-surfaces";
const DEFAULT_MODAL_SURFACES = [
  {
    id: "browser",
    title: "Browser",
    icon: "language",
    modalPath: "/plugins/_browser/webui/main.html",
  },
  {
    id: "office",
    title: "Desktop",
    icon: "desktop_windows",
    modalPath: "/plugins/_office/webui/main.html",
  },
];

function normalizeModalPath(modalPath = "") {
  return String(modalPath || "").replace(/^\/+/, "");
}

function sameModalPath(left = "", right = "") {
  return normalizeModalPath(left) === normalizeModalPath(right);
}

function modalRequiresExplicitClose(modalOrElement) {
  const element = modalOrElement?.element || modalOrElement;
  const path = normalizeModalPath(modalOrElement?.path || element?.path || "");
  return EXPLICIT_CLOSE_MODAL_PATHS.has(path)
    || element?.classList?.contains("modal-explicit-close")
    || element?.querySelector?.(".modal-inner")?.classList?.contains("modal-explicit-close");
}

function modalSurfaceGroup(modalOrElement) {
  const element = modalOrElement?.element || modalOrElement;
  const path = normalizeModalPath(modalOrElement?.path || element?.path || "");
  return SINGLE_VISIBLE_MODAL_SURFACE_PATHS.has(path) ? CANVAS_SURFACE_MODAL_GROUP : "";
}

function setModalParked(modal, parked = false) {
  const element = modal?.element;
  if (!element) return;
  element.classList.toggle("modal-surface-parked", parked);
  if (parked) {
    element.classList.remove("show");
    element.setAttribute("aria-hidden", "true");
  } else {
    element.classList.add("show");
    element.removeAttribute("aria-hidden");
  }
}

function parkSiblingSurfaceModals(activeModal) {
  const group = modalSurfaceGroup(activeModal);
  if (!group) {
    setModalParked(activeModal, false);
    return;
  }

  for (const modal of modalStack) {
    setModalParked(modal, modal !== activeModal && modalSurfaceGroup(modal) === group);
  }
}

function activateModal(modal) {
  if (!modal) return;
  parkSiblingSurfaceModals(modal);
  updateModalZIndexes();
  restoreModalScrollSnapshot(modal);
}

function findModalIndexByPath(modalPath) {
  return modalStack.findIndex((modal) => sameModalPath(modal.path, modalPath));
}

function focusModal(modalPath) {
  const modalIndex = findModalIndexByPath(modalPath);
  if (modalIndex === -1) return false;
  const currentTopModal = modalStack[modalStack.length - 1];
  if (currentTopModal) {
    currentTopModal.savedScrollSnapshot = captureModalScrollSnapshot(currentTopModal);
  }
  const [modal] = modalStack.splice(modalIndex, 1);
  modalStack.push(modal);
  activateModal(modal);
  return true;
}

function getModalScrollElement(modal) {
  return modal?.element?.querySelector(".modal-scroll");
}

function captureModalScrollSnapshot(modal) {
  const modalScroll = getModalScrollElement(modal);
  if (!modalScroll) return null;
  return {
    scrollTop: modalScroll.scrollTop,
    scrollLeft: modalScroll.scrollLeft,
  };
}

function restoreModalScrollSnapshot(modal) {
  const snapshot = modal?.savedScrollSnapshot;
  if (!snapshot) return;

  requestAnimationFrame(() => {
    const modalScroll = getModalScrollElement(modal);
    if (!modalScroll) return;
    modalScroll.scrollTop = snapshot.scrollTop;
    modalScroll.scrollLeft = snapshot.scrollLeft;
    modal.savedScrollSnapshot = null;
  });
}

// Create a single backdrop for all modals
const backdrop = document.createElement("div");
backdrop.className = "modal-backdrop";
backdrop.style.display = "none";
backdrop.style.backdropFilter = "blur(8px) saturate(112%)";
document.body.appendChild(backdrop);

function modalSuppressesBackdrop(modal) {
  const path = String(modal?.path || "");
  return path === "/plugins/_browser/webui/main.html"
    || path === "plugins/_browser/webui/main.html"
    || path === "/plugins/_office/webui/main.html"
    || path === "plugins/_office/webui/main.html"
    || modal?.element?.classList?.contains("modal-floating")
    || modal?.element?.classList?.contains("modal-no-backdrop")
    || modal?.inner?.classList?.contains("modal-no-backdrop");
}

// Function to update z-index for all modals and backdrop
function updateModalZIndexes() {
  // Base z-index for modals
  const baseZIndex = 3000;

  // Update z-index for all modals
  modalStack.forEach((modal, index) => {
    // For first modal, z-index is baseZIndex
    // For second modal, z-index is baseZIndex + 20
    // This leaves room for the backdrop between them
    modal.element.style.zIndex = baseZIndex + index * 20;
  });

  const backdropModalStack = modalStack.filter((modal) => !modalSuppressesBackdrop(modal));

  if (backdropModalStack.length === 0) {
    backdrop.style.display = "none";
    return;
  }

  backdrop.style.display = "block";
  backdrop.style.backdropFilter = "blur(8px) saturate(112%)";
  backdrop.style.backgroundColor = "";

  if (backdropModalStack.length === modalStack.length && modalStack.length > 1) {
    const topModalIndex = modalStack.length - 1;
    backdrop.style.zIndex = baseZIndex + (topModalIndex - 1) * 20 + 10;
  } else {
    const topBackdropModal = backdropModalStack[backdropModalStack.length - 1];
    const topBackdropModalIndex = modalStack.indexOf(topBackdropModal);
    backdrop.style.zIndex = topBackdropModalIndex > 0
      ? baseZIndex + (topBackdropModalIndex - 1) * 20 + 10
      : baseZIndex - 1;
  }
}

// Function to create a new modal element
function createModalElement(path) {
  // Create modal element
  const newModal = document.createElement("div");
  newModal.className = "modal";
  newModal.path = path; // save name to the object

  // Add click handlers to only close modal if both mousedown and mouseup are on the modal container
  let mouseDownTarget = null;
  newModal.addEventListener("mousedown", (event) => {
    mouseDownTarget = event.target;
  });
  newModal.addEventListener("mouseup", (event) => {
    if (
      event.target === newModal
      && mouseDownTarget === newModal
      && !modalRequiresExplicitClose(newModal)
    ) {
      closeModal();
    }
    mouseDownTarget = null;
  });


  // Create modal structure
  newModal.innerHTML = `
    <div class="modal-inner" x-data>
      <x-extension id="modal-shell-start"></x-extension>
      <div class="modal-header">
        <h2 class="modal-title"></h2>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-scroll">
        <div class="modal-bd"></div>
      </div>
      <div class="modal-footer-slot" style="display: none;"></div>
      <x-extension id="modal-shell-end"></x-extension>
    </div>
  `;

  // Setup close button handler for this specific modal
  const close_button = newModal.querySelector(".modal-close");
  close_button.addEventListener("click", () => closeModal());


  // Add modal to DOM
  document.body.appendChild(newModal);

  // Show the modal
  newModal.classList.add("show");

  // Update modal z-indexes
  updateModalZIndexes();

  return {
    path: path,
    element: newModal,
    title: newModal.querySelector(".modal-title"),
    header: newModal.querySelector(".modal-header"),
    body: newModal.querySelector(".modal-bd"),
    close: close_button,
    footerSlot: newModal.querySelector(".modal-footer-slot"),
    inner: newModal.querySelector(".modal-inner"),
    styles: [],
    scripts: [],
    beforeClose: null,
    savedScrollSnapshot: null,
  };
}

function getDockMetadata(doc, modalPath) {
  const htmlDataset = doc?.documentElement?.dataset || {};
  const bodyDataset = doc?.body?.dataset || {};
  const surfaceId = htmlDataset.canvasSurface || bodyDataset.canvasSurface || "";
  if (!surfaceId) return null;
  return {
    surfaceId,
    modalPath: htmlDataset.canvasModalPath || bodyDataset.canvasModalPath || modalPath,
    title: htmlDataset.canvasDockTitle || bodyDataset.canvasDockTitle || "Open in canvas",
    icon: htmlDataset.canvasDockIcon || bodyDataset.canvasDockIcon || "dock_to_right",
  };
}

function getModalSwitchSurfaces(metadata) {
  const surfacesById = new Map(DEFAULT_MODAL_SURFACES.map((surface) => [surface.id, surface]));
  const surfaces = Array.isArray(rightCanvasStore.panelSurfaces)
    ? rightCanvasStore.panelSurfaces
    : [];

  for (const surface of surfaces) {
    if (!surface?.id || !surface.modalPath || surface.actionOnly) continue;
    surfacesById.set(surface.id, {
      ...surface,
      modalPath: surface.modalPath,
    });
  }

  if (metadata?.surfaceId && !surfacesById.has(metadata.surfaceId)) {
    surfacesById.set(metadata.surfaceId, {
      id: metadata.surfaceId,
      title: metadata.title,
      icon: metadata.icon,
      modalPath: metadata.modalPath,
    });
  }

  return Array.from(surfacesById.values())
    .filter((surface) => surface?.id && surface.modalPath && !surface.actionOnly)
    .sort((left, right) => (left.order ?? 100) - (right.order ?? 100));
}

function createModalSurfaceButton(surface, metadata, modal) {
  const title = surface.title || surface.id;
  const targetModalPath = surface.modalPath || "";
  const isActive = surface.id === metadata.surfaceId || sameModalPath(targetModalPath, modal.path);
  const button = document.createElement("button");
  button.type = "button";
  button.className = "modal-surface-button";
  button.dataset.canvasSurface = surface.id;
  button.setAttribute("aria-label", title);
  button.setAttribute("aria-pressed", isActive.toString());
  if (isActive) button.classList.add("is-active");

  if (surface.image) {
    const image = document.createElement("img");
    image.className = "modal-surface-image";
    image.src = surface.image;
    image.alt = "";
    image.setAttribute("aria-hidden", "true");
    button.appendChild(image);
  } else {
    const icon = document.createElement("span");
    icon.className = "material-symbols-outlined";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = surface.icon || "web_asset";
    button.appendChild(icon);
  }

  button.addEventListener("click", () => {
    if (button.disabled || isActive || !targetModalPath) return;
    button.disabled = true;
    try {
      rightCanvasStore.recordSurfaceMode?.(surface.id, "modal");
      const openPromise = ensureModalOpen(targetModalPath);
      if (openPromise?.catch) {
        openPromise.catch((error) => console.error(`Modal surface ${surface.id} failed to open`, error));
      }
    } finally {
      if (document.contains(button)) button.disabled = false;
    }
  });

  return button;
}

function configureModalSurfaceSwitcher(modal, doc) {
  const metadata = getDockMetadata(doc, modal.path);
  if (!metadata || !modal.header || modal.header.querySelector(".modal-surface-switcher")) {
    return metadata;
  }

  const surfaces = getModalSwitchSurfaces(metadata);
  if (surfaces.length <= 1) return metadata;

  const switcher = document.createElement("div");
  switcher.className = "modal-surface-switcher";
  switcher.setAttribute("role", "group");
  switcher.setAttribute("aria-label", "Modal surfaces");

  for (const surface of surfaces) {
    switcher.appendChild(createModalSurfaceButton(surface, metadata, modal));
  }

  modal.close?.insertAdjacentElement("beforebegin", switcher);
  return metadata;
}

function configureModalDockButton(modal, doc) {
  const metadata = configureModalSurfaceSwitcher(modal, doc);
  if (!metadata || !modal.header || modal.header.querySelector(".modal-dock-button")) {
    return;
  }

  rightCanvasStore.recordSurfaceMode?.(metadata.surfaceId, "modal");

  const button = document.createElement("button");
  button.type = "button";
  button.className = "modal-dock-button";
  button.setAttribute("aria-label", metadata.title);
  button.innerHTML = `<span class="material-symbols-outlined" aria-hidden="true">${metadata.icon}</span>`;
  button.addEventListener("click", async () => {
    if (button.disabled) return;
    button.disabled = true;
    try {
      await rightCanvasStore.dockSurface?.(metadata.surfaceId, {
        modalPath: metadata.modalPath,
        sourceModalPath: modal.path,
        source: "modal",
        closeSourceModal: async () => {
          const closed = await closeModal(modal.path);
          if (closed === false) return false;
          if (document.contains(modal.element)) {
            const fallbackClosed = await closeModal();
            if (fallbackClosed === false) return false;
          }
          return !document.contains(modal.element);
        },
      });
    } finally {
      if (document.contains(button)) button.disabled = false;
    }
  });

  modal.close?.insertAdjacentElement("beforebegin", button);
}

// Function to open modal with content from URL
export async function openModal(modalPath, beforeClose = null) {
  const openCtx = { modalPath, modal: null, cancel: false };
  await callJsExtensions("open_modal_before", openCtx);
  if (openCtx.cancel) return;
  modalPath = openCtx.modalPath;

  return new Promise((resolve) => {
    try {
      const currentTopModal = modalStack[modalStack.length - 1];
      if (currentTopModal) {
        currentTopModal.savedScrollSnapshot = captureModalScrollSnapshot(currentTopModal);
      }

      // Create new modal instance
      const modal = createModalElement(modalPath);
      modal.beforeClose = beforeClose;
      openCtx.modal = modal;

      new MutationObserver(
        (_, o) =>
          !document.contains(modal.element) && (o.disconnect(), resolve())
      ).observe(document.body, { childList: true, subtree: true });

      // Set a loading state
      modal.body.innerHTML = '<div class="loading">Loading...</div>';

      // Already added to stack above

      // Use importComponent to load the modal content
      // This handles all HTML, styles, scripts and nested components
      // Updated path to use the new folder structure with modal.html
      const componentPath = modalPath; // `modals/${modalPath}/modal.html`;

      // Use importComponent which now returns the parsed document
      importComponent(componentPath, modal.body)
        .then((doc) => {
          // Set the title from the document
          modal.title.innerHTML = doc.title || modalPath;
          if (doc.html && doc.html.classList) {
            const inner = modal.element.querySelector(".modal-inner");
            if (inner) inner.classList.add(...doc.html.classList);
          }
          if (doc.body && doc.body.classList) {
            modal.body.classList.add(...doc.body.classList);
          }
          configureModalDockButton(modal, doc);
          updateModalZIndexes();
          
          // Some modals have a footer. Check if it exists and move it to footer slot
          // Use requestAnimationFrame to let Alpine mount the component first
          requestAnimationFrame(() => {
            const componentFooter = modal.body.querySelector('[data-modal-footer]');
            if (componentFooter && modal.footerSlot) {
              // Move footer outside modal-scroll scrollable area
              modal.footerSlot.appendChild(componentFooter);
              modal.footerSlot.style.display = 'block';
              modal.inner.classList.add('modal-with-footer');
            }
          });
        })
        .catch((error) => {
          console.error("Error loading modal content:", error);
          modal.body.innerHTML = `<div class="error">Failed to load modal content: ${error.message}</div>`;
        });

      // Add modal to stack and show it
      // Add modal to stack
      modal.path = modalPath;
      modalStack.push(modal);
      document.body.style.overflow = "hidden";

      activateModal(modal);
    } catch (error) {
      console.error("Error loading modal content:", error);
      resolve();
    }
  });
}

export function isModalOpen(modalPath) {
  return findModalIndexByPath(modalPath) !== -1;
}

export async function ensureModalOpen(modalPath, beforeClose = null) {
  if (focusModal(modalPath)) return null;
  return openModal(modalPath, beforeClose);
}

export async function toggleModal(modalPath, beforeClose = null) {
  if (!isModalOpen(modalPath)) {
    return openModal(modalPath, beforeClose);
  }
  while (isModalOpen(modalPath)) {
    const closed = await closeModal(modalPath);
    if (closed === false) return false;
  }
  return true;
}

// Function to close modal
export async function closeModal(modalPath = null) {
  if (modalStack.length === 0) return;

  let modalIndex = modalStack.length - 1; // Default to last modal
  let modal;

  if (modalPath) {
    // Find the modal with the specified name in the stack
    modalIndex = findModalIndexByPath(modalPath);
    if (modalIndex === -1) return; // Modal not found in stack

    // Get the modal from stack at the found index
    modal = modalStack[modalIndex];
  } else {
    // Just get the last modal (removal happens after beforeClose)
    modal = modalStack[modalStack.length - 1];
  }

  const closeCtx = { modalPath: modalPath ?? null, modal, cancel: false };
  await callJsExtensions("close_modal_before", closeCtx);
  if (closeCtx.cancel) return false;

  const canClose = async () => {
    if (!modal.beforeClose) return true;
    try {
      const result = await Promise.resolve(modal.beforeClose());
      return result !== false;
    } catch (error) {
      console.error("Error in beforeClose handler:", error);
      return true;
    }
  };

  return Promise.resolve(canClose()).then((shouldClose) => {
    if (!shouldClose) return false;

    if (modalPath) {
      // Remove the modal from stack after beforeClose check
      modalStack.splice(modalIndex, 1);
    } else {
      modalStack.pop();
    }

    // Remove modal-specific styles and scripts immediately
    modal.styles.forEach((styleId) => {
      document.querySelector(`[data-modal-style="${styleId}"]`)?.remove();
    });
    modal.scripts.forEach((scriptId) => {
      document.querySelector(`[data-modal-script="${scriptId}"]`)?.remove();
    });

    // First remove the show class to trigger the transition
    modal.element.classList.remove("show");

  // commented out to prevent race conditions

  // // Remove the modal element from DOM after animation
  // modal.element.addEventListener(
  //   "transitionend",
  //   () => {
  //     // Make sure the modal is completely removed from the DOM
  //     if (modal.element.parentNode) {
  //       modal.element.parentNode.removeChild(modal.element);
  //     }
  //   },
  //   { once: true }
  // );

  // // Fallback in case the transition event doesn't fire
  // setTimeout(() => {
  //   if (modal.element.parentNode) {
  //     modal.element.parentNode.removeChild(modal.element);
  //   }
  // }, 500); // 500ms should be enough for the transition to complete

    // remove immediately
    if (modal.element.parentNode) {
      modal.element.parentNode.removeChild(modal.element);
    }


    // Handle backdrop visibility and body overflow
    if (modalStack.length === 0) {
      // Hide backdrop when no modals are left
      backdrop.style.display = "none";
      document.body.style.overflow = "";
    } else {
      activateModal(modalStack[modalStack.length - 1]);
    }

    document.dispatchEvent(
      new CustomEvent("modal-closed", {
        detail: {
          modalPath: modal.path ?? null,
          remainingModalCount: modalStack.length,
        },
      }),
    );

    return true;
  });
}

// Function to scroll to element by ID within the last modal
export function scrollModal(id) {
  if (!id) return;

  // Get the last modal in the stack
  const lastModal = modalStack[modalStack.length - 1].element;
  if (!lastModal) return;

  // Find the modal container and target element
  const modalContainer = lastModal.querySelector(".modal-scroll");
  const targetElement = lastModal.querySelector(`#${id}`);

  if (modalContainer && targetElement) {
    modalContainer.scrollTo({
      top: targetElement.offsetTop - 20, // 20px padding from top
      behavior: "smooth",
    });
  }
}

// Make scrollModal globally available
globalThis.scrollModal = scrollModal;

// Handle modal content loading from clicks
document.addEventListener("click", async (e) => {
  const modalTrigger = e.target.closest("[data-modal-content]");
  if (modalTrigger) {
    e.preventDefault();
    if (
      modalTrigger.hasAttribute("disabled") ||
      modalTrigger.classList.contains("disabled")
    ) {
      return;
    }
    const modalPath = modalTrigger.getAttribute("href");
    await openModal(modalPath);
  }
});

// Close modal on escape key (closes only the top modal)
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && modalStack.length > 0) {
    if (modalRequiresExplicitClose(modalStack[modalStack.length - 1])) return;
    closeModal();
  }
});

// also export as global function
globalThis.openModal = openModal;
globalThis.closeModal = closeModal;
globalThis.scrollModal = scrollModal;
globalThis.isModalOpen = isModalOpen;
globalThis.ensureModalOpen = ensureModalOpen;
globalThis.toggleModal = toggleModal;
