const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
}

const API_URL = "https://telegram-bit-market-store-1.onrender.com/api/products";

let products = [];
let cart = {}; // { productId: quantity }
let selectedCategory = "All";

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const productsGrid = document.getElementById("productsGrid");
  const categoryContainer = document.getElementById("categoryContainer");
  const searchInput = document.getElementById("searchInput");

  const cartBtn = document.getElementById("cartBtn");
  const cartBadge = document.getElementById("cartBadge");
  const cartModal = document.getElementById("cartModal");
  const closeCartBtn = document.getElementById("closeCartBtn");
  const cartItemsList = document.getElementById("cartItemsList");
  const cartTotalPrice = document.getElementById("cartTotalPrice");
  const toCheckoutBtn = document.getElementById("toCheckoutBtn");

  const checkoutModal = document.getElementById("checkoutModal");
  const closeCheckoutBtn = document.getElementById("closeCheckoutBtn");
  const checkoutForm = document.getElementById("checkoutForm");
  const custName = document.getElementById("custName");
  const custPhone = document.getElementById("custPhone");
  const custAddress = document.getElementById("custAddress");
  const custNotes = document.getElementById("custNotes");

  // Fetch active products from Render API
  async function loadProducts() {
    if (!productsGrid) return;

    productsGrid.innerHTML = `
      <div class="col-span-full text-center py-12 text-zinc-500 text-sm">
        <div class="inline-block animate-spin mb-2">⚡</div>
        <p>Loading live catalog...</p>
      </div>
    `;

    try {
      const response = await fetch(API_URL);
      if (!response.ok) {
        throw new Error(`HTTP error: ${response.status}`);
      }
      products = await response.json();
      renderCategories();
      renderProducts();
    } catch (err) {
      console.error("Failed to load products:", err);
      productsGrid.innerHTML = `
        <div class="col-span-full text-center py-12 text-red-400 text-sm">
          Failed to load catalog. Please check your connection.
        </div>
      `;
    }
  }

  // Render Category Chips
  function renderCategories() {
    if (!categoryContainer) return;
    const categories = ["All", ...new Set(products.map((p) => p.category))];

    categoryContainer.innerHTML = categories
      .map(
        (cat) => `
        <button 
          data-category="${cat}"
          class="cat-chip whitespace-nowrap px-3 py-1.5 rounded-xl border transition ${
            cat === selectedCategory
              ? "bg-brand text-white border-brand font-medium shadow-sm"
              : "bg-surface text-zinc-400 border-border hover:text-white"
          }">
          ${cat}
        </button>
      `
      )
      .join("");

    categoryContainer.querySelectorAll(".cat-chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedCategory = btn.dataset.category;
        renderCategories();
        renderProducts();
      });
    });
  }

  // Render Product Grid Cards
  function renderProducts() {
    if (!productsGrid) return;

    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : "";

    let filtered =
      selectedCategory === "All"
        ? products
        : products.filter((p) => p.category === selectedCategory);

    if (searchTerm) {
      filtered = filtered.filter(
        (p) =>
          p.name.toLowerCase().includes(searchTerm) ||
          (p.specs && p.specs.toLowerCase().includes(searchTerm))
      );
    }

    if (filtered.length === 0) {
      productsGrid.innerHTML = `
        <div class="col-span-full text-center py-12 text-zinc-500 text-sm">
          No items found matching your filter.
        </div>
      `;
      return;
    }

    productsGrid.innerHTML = filtered
      .map((p) => {
        const qty = cart[p.id] || 0;
        const isOutOfStock = p.stock_count <= 0;

        return `
        <div class="bg-surface border border-border rounded-2xl overflow-hidden flex flex-col justify-between p-3 transition hover:border-zinc-700">
          <div>
            <div class="relative w-full h-36 rounded-xl overflow-hidden bg-background mb-3">
              <img 
                src="${p.image_url || "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"}" 
                alt="${p.name}" 
                class="w-full h-full object-cover"
                loading="lazy"
                onerror="this.src='https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80';"
              />
              <span class="absolute top-2 left-2 bg-background/80 backdrop-blur text-[10px] text-zinc-300 px-2 py-0.5 rounded-md font-medium border border-border">
                ${p.category}
              </span>
            </div>

            <h3 class="font-semibold text-sm text-white line-clamp-1">${p.name}</h3>
            <p class="text-xs text-zinc-400 mt-1 line-clamp-2">${p.specs || ""}</p>
          </div>

          <div class="mt-3 pt-3 border-t border-border flex items-center justify-between">
            <div>
              <span class="block text-sm font-bold text-white">${Number(p.price).toLocaleString()} ETB</span>
              <span class="text-[10px] ${isOutOfStock ? "text-red-400" : "text-zinc-500"}">
                ${isOutOfStock ? "Out of Stock" : `${p.stock_count} in stock`}
              </span>
            </div>

            ${
              isOutOfStock
                ? `<button disabled class="px-3 py-1.5 bg-zinc-800 text-zinc-500 text-xs rounded-xl cursor-not-allowed">Sold</button>`
                : qty > 0
                ? `
                  <div class="flex items-center gap-2 bg-background border border-border rounded-xl p-1">
                    <button data-id="${p.id}" class="btn-dec w-6 h-6 rounded-lg bg-surface text-zinc-200 hover:bg-zinc-700 flex items-center justify-center font-bold text-xs">-</button>
                    <span class="text-xs font-semibold px-1 text-white">${qty}</span>
                    <button data-id="${p.id}" class="btn-inc w-6 h-6 rounded-lg bg-surface text-zinc-200 hover:bg-zinc-700 flex items-center justify-center font-bold text-xs" ${qty >= p.stock_count ? "disabled" : ""}>+</button>
                  </div>
                `
                : `<button data-id="${p.id}" class="btn-add px-4 py-1.5 bg-brand hover:bg-blue-600 text-white font-medium text-xs rounded-xl transition">Add</button>`
            }
          </div>
        </div>
      `;
      })
      .join("");

    attachProductListeners();
  }

  function attachProductListeners() {
    productsGrid.querySelectorAll(".btn-add").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        cart[id] = 1;
        updateCartState();
        renderProducts();
      });
    });

    productsGrid.querySelectorAll(".btn-inc").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        const prod = products.find((p) => p.id === id);
        if (prod && (cart[id] || 0) < prod.stock_count) {
          cart[id] = (cart[id] || 0) + 1;
          updateCartState();
          renderProducts();
        }
      });
    });

    productsGrid.querySelectorAll(".btn-dec").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = parseInt(btn.dataset.id);
        if (cart[id] > 1) {
          cart[id] -= 1;
        } else {
          delete cart[id];
        }
        updateCartState();
        renderProducts();
      });
    });
  }

  // Update Cart Totals & Badge
  function updateCartState() {
    const itemIds = Object.keys(cart).map((k) => parseInt(k));
    let totalItems = 0;
    let totalPrice = 0;

    itemIds.forEach((id) => {
      const prod = products.find((p) => p.id === id);
      if (prod) {
        totalItems += cart[id];
        totalPrice += prod.price * cart[id];
      }
    });

    if (cartBadge) {
      if (totalItems > 0) {
        cartBadge.classList.remove("hidden");
        cartBadge.textContent = totalItems;
      } else {
        cartBadge.classList.add("hidden");
      }
    }

    if (cartTotalPrice) {
      cartTotalPrice.textContent = `${totalPrice.toLocaleString()} ETB`;
    }

    renderCartItemsList();
  }

  function renderCartItemsList() {
    if (!cartItemsList) return;

    const itemIds = Object.keys(cart).map((k) => parseInt(k));
    if (itemIds.length === 0) {
      cartItemsList.innerHTML = `<p class="text-zinc-500 text-xs text-center py-6">Your cart is empty.</p>`;
      if (toCheckoutBtn) toCheckoutBtn.disabled = true;
      return;
    }

    if (toCheckoutBtn) toCheckoutBtn.disabled = false;

    cartItemsList.innerHTML = itemIds
      .map((id) => {
        const prod = products.find((p) => p.id === id);
        if (!prod) return "";
        const qty = cart[id];
        const lineTotal = prod.price * qty;

        return `
        <div class="flex items-center justify-between gap-3 bg-background border border-border rounded-xl p-3">
          <div class="flex-1">
            <h4 class="text-xs font-semibold text-white line-clamp-1">${prod.name}</h4>
            <span class="text-[11px] text-zinc-400">${Number(prod.price).toLocaleString()} ETB × ${qty}</span>
          </div>
          <span class="text-xs font-bold text-brand">${lineTotal.toLocaleString()} ETB</span>
        </div>
      `;
      })
      .join("");
  }

  // Search filter
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      renderProducts();
    });
  }

  // Cart modal events
  if (cartBtn && cartModal) {
    cartBtn.addEventListener("click", () => {
      cartModal.classList.remove("hidden");
    });
  }

  if (closeCartBtn && cartModal) {
    closeCartBtn.addEventListener("click", () => {
      cartModal.classList.add("hidden");
    });
  }

  // Checkout modal events
  if (toCheckoutBtn && checkoutModal && cartModal) {
    toCheckoutBtn.addEventListener("click", () => {
      cartModal.classList.add("hidden");
      checkoutModal.classList.remove("hidden");
    });
  }

  if (closeCheckoutBtn && checkoutModal && cartModal) {
    closeCheckoutBtn.addEventListener("click", () => {
      checkoutModal.classList.add("hidden");
      cartModal.classList.remove("hidden");
    });
  }

  // Checkout form submit
  if (checkoutForm) {
    checkoutForm.addEventListener("submit", (e) => {
      e.preventDefault();

      const selectedPayment =
        document.querySelector('input[name="paymentMethod"]:checked')?.value ||
        "MOBILE_MONEY";

      const orderPayload = {
        customer: {
          name: custName ? custName.value.trim() : "Unknown",
          phone: custPhone ? custPhone.value.trim() : "",
          address: custAddress ? custAddress.value.trim() : "",
          notes: custNotes ? custNotes.value.trim() : "",
        },
        payment_method: selectedPayment,
        items: Object.keys(cart).map((id) => ({
          product_id: parseInt(id),
          quantity: cart[id],
        })),
      };

      if (tg) {
        tg.sendData(JSON.stringify(orderPayload));
        tg.close();
      } else {
        alert("Order placed successfully! (Test browser mode)");
        console.log("Transmitted payload:", orderPayload);
      }
    });
  }

  // Load the catalog
  loadProducts();
});
