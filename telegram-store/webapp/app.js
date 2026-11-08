const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
}

const API_URL = "https://telegram-bit-market-store-1.onrender.com/api/products";

let products = [];
let cart = {}; // { productId: quantity }
let selectedCategory = "All";

// DOM Elements
const productsGrid = document.getElementById("products-grid");
const categoryChips = document.getElementById("category-chips");
const cartFooter = document.getElementById("cart-footer");
const cartTotalEl = document.getElementById("cart-total");
const checkoutModal = document.getElementById("checkout-modal");
const checkoutForm = document.getElementById("checkout-form");
const closeModalBtn = document.getElementById("close-modal");
const openCheckoutBtn = document.getElementById("open-checkout-btn");

// Fetch active products from backend API
async function loadProducts() {
  if (!productsGrid) return;

  try {
    productsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #8e8e93;">
        Loading catalog...
      </div>
    `;

    const response = await fetch(API_URL);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    products = await response.json();
    renderCategories();
    renderProducts();
  } catch (error) {
    console.error("Failed to load products:", error);
    productsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #ff453a;">
        Failed to load catalog. Please pull down to refresh.
      </div>
    `;
  }
}

// Render dynamic category filter chips
function renderCategories() {
  if (!categoryChips) return;
  const categories = ["All", ...new Set(products.map((p) => p.category))];

  categoryChips.innerHTML = categories
    .map(
      (cat) => `
        <button class="chip ${cat === selectedCategory ? "active" : ""}" data-category="${cat}">
          ${cat}
        </button>
      `
    )
    .join("");

  categoryChips.querySelectorAll(".chip").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedCategory = btn.dataset.category;
      renderCategories();
      renderProducts();
    });
  });
}

// Render product catalog cards
function renderProducts() {
  if (!productsGrid) return;

  const filtered =
    selectedCategory === "All"
      ? products
      : products.filter((p) => p.category === selectedCategory);

  if (filtered.length === 0) {
    productsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #8e8e93;">
        No items found in this category.
      </div>
    `;
    return;
  }

  productsGrid.innerHTML = filtered
    .map((product) => {
      const qtyInCart = cart[product.id] || 0;
      const isOutOfStock = product.stock_count <= 0;

      return `
        <div class="product-card" data-id="${product.id}">
          <div class="product-image-wrap">
            <img 
              src="${product.image_url || "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"}" 
              alt="${product.name}" 
              class="product-image" 
              loading="lazy" 
              onerror="this.src='https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80';"
            />
            <span class="category-tag">${product.category}</span>
          </div>
          <div class="product-info">
            <h3 class="product-name">${product.name}</h3>
            <p class="product-specs">${product.specs || ""}</p>
            <div class="product-bottom">
              <div>
                <span class="product-price">${Number(product.price).toLocaleString()} ETB</span>
                <span class="stock-badge ${isOutOfStock ? "out" : ""}">${isOutOfStock ? "Out of Stock" : `${product.stock_count} in stock`}</span>
              </div>
              ${
                isOutOfStock
                  ? `<button class="add-btn disabled" disabled>Sold Out</button>`
                  : qtyInCart > 0
                  ? `
                    <div class="qty-control">
                      <button class="qty-btn dec" data-id="${product.id}">-</button>
                      <span class="qty-count">${qtyInCart}</span>
                      <button class="qty-btn inc" data-id="${product.id}" ${qtyInCart >= product.stock_count ? "disabled" : ""}>+</button>
                    </div>
                  `
                  : `<button class="add-btn" data-id="${product.id}">Add</button>`
              }
            </div>
          </div>
        </div>
      `;
    })
    .join("");

  attachProductListeners();
}

function attachProductListeners() {
  document.querySelectorAll(".add-btn[data-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.id);
      cart[id] = 1;
      updateCartUI();
      renderProducts();
    });
  });

  document.querySelectorAll(".qty-btn.inc").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.id);
      const product = products.find((p) => p.id === id);
      if (product && (cart[id] || 0) < product.stock_count) {
        cart[id] = (cart[id] || 0) + 1;
        updateCartUI();
        renderProducts();
      }
    });
  });

  document.querySelectorAll(".qty-btn.dec").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = parseInt(btn.dataset.id);
      if (cart[id] > 1) {
        cart[id] -= 1;
      } else {
        delete cart[id];
      }
      updateCartUI();
      renderProducts();
    });
  });
}

function updateCartUI() {
  if (!cartFooter || !cartTotalEl) return;

  const itemIds = Object.keys(cart).map((k) => parseInt(k));
  let totalAmount = 0;
  let totalCount = 0;

  itemIds.forEach((id) => {
    const prod = products.find((p) => p.id === id);
    if (prod) {
      totalAmount += prod.price * cart[id];
      totalCount += cart[id];
    }
  });

  if (totalCount > 0) {
    cartFooter.classList.remove("hidden");
    cartTotalEl.innerText = `${totalAmount.toLocaleString()} ETB (${totalCount} item${totalCount > 1 ? "s" : ""})`;
  } else {
    cartFooter.classList.add("hidden");
  }
}

// Checkout Form submission via Telegram WebApp Data
if (openCheckoutBtn) {
  openCheckoutBtn.addEventListener("click", () => {
    if (checkoutModal) checkoutModal.classList.remove("hidden");
  });
}

if (closeModalBtn) {
  closeModalBtn.addEventListener("click", () => {
    if (checkoutModal) checkoutModal.classList.add("hidden");
  });
}

if (checkoutForm) {
  checkoutForm.addEventListener("submit", (e) => {
    e.preventDefault();

    const orderPayload = {
      customer: {
        name: document.getElementById("cust-name")?.value.trim() || "",
        phone: document.getElementById("cust-phone")?.value.trim() || "",
        address: document.getElementById("cust-address")?.value.trim() || "",
        notes: document.getElementById("cust-notes")?.value.trim() || "",
      },
      payment_method: document.getElementById("cust-payment")?.value || "MOBILE_MONEY",
      items: Object.keys(cart).map((id) => ({
        product_id: parseInt(id),
        quantity: cart[id],
      })),
    };

    if (tg) {
      tg.sendData(JSON.stringify(orderPayload));
      tg.close();
    } else {
      alert("Order placed! (Simulated outside Telegram WebApp)");
      console.log("Order payload:", orderPayload);
    }
  });
}

// Initial load
loadProducts();
