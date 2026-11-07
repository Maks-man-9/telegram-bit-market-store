const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

// Store Configuration
const BOT_TOKEN = "9240762684:AAHSN8oFTAar5r827lbLeQnOKVy4ewxknmA";
const ADMIN_CHAT_ID = "YOUR_ADMIN_ID_HERE"; // Replace with your numeric ID from @myidbot

// Catalog items
let products = [
  {
    "id": 1,
    "sku": "CHG-65W-GAN",
    "name": "65W GaN Dual USB-C Fast Charger",
    "category": "Chargers",
    "price": 38.99,
    "specs": { "Ports": "2x USB-C, 1x USB-A", "Tech": "GaN III", "Power": "65W Max" },
    "stock_count": 25,
    "image_url": "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?w=600&auto=format&fit=crop&q=80"
  },
  {
    "id": 2,
    "sku": "CBL-TB4-2M",
    "name": "Braided Thunderbolt 4 / USB-C Cable (2m)",
    "category": "Cables",
    "price": 24.50,
    "specs": { "Bandwidth": "40Gbps", "Length": "2 meters", "Power": "100W PD" },
    "stock_count": 50,
    "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=600&auto=format&fit=crop&q=80"
  },
  {
    "id": 3,
    "sku": "SSD-NVME-1TB",
    "name": "Rugged Portable NVMe SSD (1TB)",
    "category": "Storage",
    "price": 109.00,
    "specs": { "Read Speed": "1050 MB/s", "Durability": "IP55 Water/Dust", "Interface": "USB 3.2 Gen 2" },
    "stock_count": 14,
    "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=600&auto=format&fit=crop&q=80"
  },
  {
    "id": 4,
    "sku": "AUD-ANC-PRO",
    "name": "Hi-Res Wireless ANC Earbuds",
    "category": "Audio Gear",
    "price": 89.95,
    "specs": { "ANC": "Hybrid Active", "Battery": "32h total", "Codec": "LDAC / AAC" },
    "stock_count": 18,
    "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=600&auto=format&fit=crop&q=80"
  },
  {
    "id": 5,
    "sku": "ADP-8IN1-HUB",
    "name": "8-in-1 Aluminium USB-C Hub Adapter",
    "category": "Adapters",
    "price": 45.00,
    "specs": { "HDMI": "4K @ 60Hz", "Ethernet": "Gigabit", "Card Reader": "SD/TF" },
    "stock_count": 30,
    "image_url": "https://images.unsplash.com/photo-1625842268584-8f3296236761?w=600&auto=format&fit=crop&q=80"
  }
];

let cart = {}; 
let selectedCategory = "All";

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
const submitOrderBtn = document.getElementById("submitOrderBtn");

function init() {
  renderCategories();
  renderProducts();
  bindEvents();
  prefillTelegramUser();
}

function prefillTelegramUser() {
  const user = tg?.initDataUnsafe?.user;
  if (user) {
    const nameInput = document.getElementById("custName");
    const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ");
    if (fullName && nameInput) nameInput.value = fullName;
  }
}

function renderCategories() {
  const categories = ["All", ...new Set(products.map(p => p.category))];
  categoryContainer.innerHTML = categories.map(cat => `
    <button 
      type="button"
      class="px-3 py-1.5 rounded-lg whitespace-nowrap transition ${
        selectedCategory === cat 
          ? 'bg-brand text-white font-medium' 
          : 'bg-surface text-zinc-400 border border-border'
      }" 
      onclick="filterCategory('${cat}')">
      ${cat}
    </button>
  `).join("");
}

window.filterCategory = function(cat) {
  selectedCategory = cat;
  renderCategories();
  renderProducts();
};

function renderProducts() {
  const query = (searchInput?.value || "").toLowerCase().trim();
  const filtered = products.filter(p => {
    const matchesCategory = selectedCategory === "All" || p.category === selectedCategory;
    const matchesSearch = p.name.toLowerCase().includes(query) || p.category.toLowerCase().includes(query);
    return matchesCategory && matchesSearch;
  });

  if (filtered.length === 0) {
    productsGrid.innerHTML = `
      <div class="col-span-full py-12 text-center text-zinc-500 text-sm">
        No gear found matching your criteria.
      </div>
    `;
    return;
  }

  productsGrid.innerHTML = filtered.map(product => {
    const qty = cart[product.id] || 0;
    const specsEntries = Object.entries(product.specs || {});
    
    return `
      <div class="bg-surface border border-border rounded-xl p-3 flex flex-col justify-between">
        <div>
          <img src="${product.image_url}" alt="${product.name}" class="w-full h-36 object-cover rounded-lg bg-zinc-900 border border-border/50 mb-2" />
          <div class="flex items-center justify-between text-[11px] text-zinc-400 mb-1">
            <span>${product.category}</span>
            <span class="font-mono text-zinc-500">${product.stock_count} in stock</span>
          </div>
          <h3 class="font-medium text-sm text-zinc-100 leading-snug">${product.name}</h3>
          
          <div class="mt-2 space-y-0.5">
            ${specsEntries.map(([k, v]) => `
              <div class="text-[10px] text-zinc-400 flex justify-between">
                <span class="text-zinc-500">${k}:</span>
                <span class="font-mono">${v}</span>
              </div>
            `).join("")}
          </div>
        </div>

        <div class="mt-4 pt-3 border-t border-border flex items-center justify-between">
          <span class="font-bold text-sm text-white">$${product.price.toFixed(2)}</span>
          
          ${qty === 0 ? `
            <button type="button" onclick="updateQty(${product.id}, 1)" class="bg-brand hover:bg-blue-600 text-white text-xs px-3 py-1.5 rounded-lg transition font-medium">
              + Add
            </button>
          ` : `
            <div class="flex items-center bg-background border border-border rounded-lg">
              <button type="button" onclick="updateQty(${product.id}, -1)" class="px-2.5 py-1 text-zinc-300 hover:text-white text-xs">-</button>
              <span class="px-2 text-xs font-semibold text-white">${qty}</span>
              <button type="button" onclick="updateQty(${product.id}, 1)" class="px-2.5 py-1 text-zinc-300 hover:text-white text-xs">+</button>
            </div>
          `}
        </div>
      </div>
    `;
  }).join("");
}

window.updateQty = function(productId, delta) {
  const current = cart[productId] || 0;
  const target = current + delta;
  const product = products.find(p => p.id === productId);

  if (target > product.stock_count) {
    if (tg?.showAlert) tg.showAlert("Maximum available stock reached.");
    return;
  }

  if (target <= 0) {
    delete cart[productId];
  } else {
    cart[productId] = target;
  }
  
  updateCartState();
  renderProducts();
  renderCartDrawer();
};

function updateCartState() {
  const totalItems = Object.values(cart).reduce((a, b) => a + b, 0);
  if (totalItems > 0) {
    cartBadge.textContent = totalItems;
    cartBadge.classList.remove("hidden");
  } else {
    cartBadge.classList.add("hidden");
  }
}

function renderCartDrawer() {
  const itemIds = Object.keys(cart);
  if (itemIds.length === 0) {
    cartItemsList.innerHTML = `<p class="text-zinc-500 text-sm text-center py-8">Your cart is currently empty.</p>`;
    cartTotalPrice.textContent = "$0.00";
    toCheckoutBtn.disabled = true;
    toCheckoutBtn.classList.add("opacity-50", "pointer-events-none");
    return;
  }

  toCheckoutBtn.disabled = false;
  toCheckoutBtn.classList.remove("opacity-50", "pointer-events-none");

  let total = 0;
  cartItemsList.innerHTML = itemIds.map(id => {
    const product = products.find(p => p.id === parseInt(id));
    const qty = cart[id];
    const subtotal = product.price * qty;
    total += subtotal;

    return `
      <div class="flex items-center justify-between bg-background p-2.5 rounded-xl border border-border">
        <div class="flex-1 pr-2">
          <p class="text-xs font-medium text-white line-clamp-1">${product.name}</p>
          <p class="text-[11px] text-zinc-400 font-mono">$${product.price.toFixed(2)} × ${qty} = $${subtotal.toFixed(2)}</p>
        </div>
        <div class="flex items-center bg-surface border border-border rounded-lg">
          <button type="button" onclick="updateQty(${product.id}, -1)" class="px-2 py-0.5 text-zinc-400 hover:text-white text-xs">-</button>
          <span class="px-2 text-xs font-mono font-medium">${qty}</span>
          <button type="button" onclick="updateQty(${product.id}, 1)" class="px-2 py-0.5 text-zinc-400 hover:text-white text-xs">+</button>
        </div>
      </div>
    `;
  }).join("");

  cartTotalPrice.textContent = `$${total.toFixed(2)}`;
}

async function sendTelegramMessage(chatId, text) {
  try {
    await fetch(`https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: text,
        parse_mode: "Markdown"
      })
    });
  } catch (err) {
    console.error("API dispatch error:", err);
  }
}

function bindEvents() {
  searchInput.addEventListener("input", renderProducts);
  
  cartBtn.addEventListener("click", () => {
    renderCartDrawer();
    cartModal.classList.remove("hidden");
  });
  
  closeCartBtn.addEventListener("click", () => cartModal.classList.add("hidden"));

  toCheckoutBtn.addEventListener("click", () => {
    cartModal.classList.add("hidden");
    checkoutModal.classList.remove("hidden");
  });

  closeCheckoutBtn.addEventListener("click", () => {
    checkoutModal.classList.add("hidden");
    cartModal.classList.remove("hidden");
  });

  checkoutForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const customerName = document.getElementById("custName").value.trim();
    const phone = document.getElementById("custPhone").value.trim();
    const address = document.getElementById("custAddress").value.trim();
    const notes = document.getElementById("custNotes").value.trim();
    const paymentMethod = document.querySelector('input[name="paymentMethod"]:checked').value;
    const userId = tg?.initDataUnsafe?.user?.id;

    let total = 0;
    let itemsText = "";
    for (const [id, qty] of Object.entries(cart)) {
      const p = products.find(prod => prod.id === parseInt(id));
      const sub = p.price * qty;
      total += sub;
      itemsText += `• ${p.name} (x${qty}) — $${sub.toFixed(2)}\n`;
    }

    submitOrderBtn.disabled = true;
    submitOrderBtn.innerHTML = "<span>Processing order...</span>";

    // 1. Receipt Message
    let receipt = `✅ *Order Placed Successfully!*\n\n` +
      `*Customer:* ${customerName}\n` +
      `*Phone:* \`${phone}\`\n` +
      `*Delivery To:* ${address}\n`;
    if (notes) receipt += `*Notes:* ${notes}\n`;
    receipt += `\n*Items:*\n${itemsText}\n` +
      `*Total Amount:* \`$${total.toFixed(2)}\`\n` +
      `*Payment Method:* \`${paymentMethod}\`\n`;

    if (paymentMethod === "MOBILE_MONEY") {
      receipt += `\n⚠️ *Payment Required:*\nTransfer to Merchant ID: \`882910\`. Reply with your screenshot or transaction ID here.`;
    } else {
      receipt += `\n💵 Please have exact cash ready for the courier.`;
    }

    // 2. Admin Alert Message
    let adminAlert = `🚨 *NEW ORDER RECEIVED*\n\n` +
      `*Customer:* ${customerName} (${userId ? `[TG Profile](tg://user?id=${userId})` : "Direct"})\n` +
      `*Phone:* \`${phone}\`\n` +
      `*Address:* ${address}\n` +
      `\n*Items:*\n${itemsText}\n` +
      `*Total:* \`$${total.toFixed(2)}\`\n` +
      `*Payment:* \`${paymentMethod}\``;

    // Send customer receipt
    if (userId) {
      await sendTelegramMessage(userId, receipt);
    }

    // Send admin notification
    if (ADMIN_CHAT_ID && ADMIN_CHAT_ID !== "YOUR_ADMIN_ID_HERE") {
      await sendTelegramMessage(ADMIN_CHAT_ID, adminAlert);
    }

    // Attempt native sendData fallback
    try {
      if (tg?.sendData) {
        tg.sendData(JSON.stringify({ status: "SUCCESS" }));
      }
    } catch (_) {}

    // Close window
    setTimeout(() => {
      try {
        tg.close();
      } catch (err) {
        window.close();
      }
    }, 600);
  });
}

document.addEventListener("DOMContentLoaded", init);
