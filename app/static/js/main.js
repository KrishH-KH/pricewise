
const API_BASE = "/api";

// Format prices in Indian Rupees
function formatPrice(price) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0
    }).format(Number(price || 0));
}

// Fetch pricing plans from Flask API
async function fetchPlans() {
    try {
        const response = await fetch(`${API_BASE}/plans`);

        if (!response.ok) {
            throw new Error("Unable to load pricing plans.");
        }

        const data = await response.json();

        // Supports either a direct array or { plans: [...] }
        return Array.isArray(data) ? data : (data.plans || []);
    } catch (error) {
        console.error("Pricing API error:", error);
        return null;
    }
}

// Create pricing cards
function createPlanCard(plan, billingCycle = "monthly") {
    const price = billingCycle === "yearly"
        ? plan.yearly_price
        : plan.monthly_price;

    const billingLabel = billingCycle === "yearly" ? "/year" : "/month";

    const features = Array.isArray(plan.features) ? plan.features : [];

    return `
        <article class="pricing-card ${plan.is_popular ? "popular-plan" : ""}">
            ${plan.is_popular ? '<span class="popular-label">MOST POPULAR</span>' : ""}

            <div class="pricing-card-content">
                <h3>${escapeHTML(plan.name)}</h3>
                <p>${escapeHTML(plan.description || "")}</p>

                <div class="price-display">
                    <strong>${formatPrice(price)}</strong>
                    <span>${billingLabel}</span>
                </div>

                <ul class="pricing-features">
                    ${features.map(feature => `
                        <li>✓ ${escapeHTML(feature)}</li>
                    `).join("")}
                </ul>

                <a href="/checkout/${plan.id}?cycle=${billingCycle}" class="button ${plan.is_popular ? "button-primary" : "button-secondary"}">
    Choose Plan ↗
</a>
            </div>
        </article>
    `;
}

// Basic HTML escaping for text received from the API
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}

// Load pricing cards
async function loadPricingPlans() {
    const container = document.getElementById("pricing-container");
    if (!container) return;

    const plans = await fetchPlans();

    if (plans === null) {
        container.innerHTML = "<p>Unable to load plans. Please try again later.</p>";
        return;
    }

    if (plans.length === 0) {
        container.innerHTML = "<p>No pricing plans are currently available.</p>";
        return;
    }

    const selectedCycle = document.querySelector(".billing-option.active")?.dataset.cycle || "monthly";

    container.innerHTML = plans
        .filter(plan => plan.is_active !== false)
        .map(plan => createPlanCard(plan, selectedCycle))
        .join("");
}

// Load plan comparison table
async function loadComparison() {
    const container = document.getElementById("comparison-container");
    if (!container) return;

    const plans = await fetchPlans();

    if (plans === null) {
        container.innerHTML = "<p>Unable to load comparison. Please try again later.</p>";
        return;
    }

    if (plans.length === 0) {
        container.innerHTML = "<p>No plans available to compare.</p>";
        return;
    }

    const activePlans = plans.filter(plan => plan.is_active !== false);

    const allFeatures = [...new Set(
        activePlans.flatMap(plan =>
            Array.isArray(plan.features) ? plan.features : []
        )
    )];

    container.innerHTML = `
        <div class="table-responsive">
            <table class="comparison-table data-table">
                <thead>
                    <tr>
                        <th>Features</th>
                        ${activePlans.map(plan => `
                            <th>${escapeHTML(plan.name)}</th>
                        `).join("")}
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <th>Monthly Price</th>
                        ${activePlans.map(plan => `
                            <td>${formatPrice(plan.monthly_price)}</td>
                        `).join("")}
                    </tr>
                    <tr>
                        <th>Yearly Price</th>
                        ${activePlans.map(plan => `
                            <td>${formatPrice(plan.yearly_price)}</td>
                        `).join("")}
                    </tr>
                    ${allFeatures.map(feature => `
                        <tr>
                            <th>${escapeHTML(feature)}</th>
                            ${activePlans.map(plan => `
                                <td>
                                    ${Array.isArray(plan.features) && plan.features.includes(feature) ? "✓" : "—"}
                                </td>
                            `).join("")}
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        </div>
    `;
}

// Billing cycle toggle
document.addEventListener("click", event => {
    const button = event.target.closest(".billing-option");

    if (!button) return;

    document.querySelectorAll(".billing-option").forEach(option => {
        option.classList.remove("active");
    });

    button.classList.add("active");
    loadPricingPlans();
});

// Password visibility toggle
function initializePasswordToggles() {
    document.querySelectorAll(".password-toggle").forEach(button => {
        button.addEventListener("click", () => {
            const input = document.getElementById(button.dataset.target);

            if (!input) return;

            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            button.textContent = isPassword ? "Hide" : "Show";
        });
    });
}

// Initialize page functionality
document.addEventListener("DOMContentLoaded", () => {
    loadPricingPlans();
    loadComparison();
    initializePasswordToggles();
});

// =========================================
// CUSTOMER DASHBOARD DATA
// =========================================

async function loadCustomerDashboard() {
    const detailsContainer = document.getElementById("subscription-details");

    // Only run on the customer dashboard
    if (!detailsContainer) return;

    try {
        const response = await fetch("/api/me/dashboard");

        if (response.status === 401) {
            window.location.href = "/auth/login";
            return;
        }

        if (!response.ok) {
            throw new Error("Could not load dashboard data.");
        }

        const data = await response.json();

        // Subscription summary
        const subscription = data.subscription;

        if (subscription) {
            const plan = subscription.plan;

            document.getElementById("dashboard-plan").textContent =
                plan.name;

            document.getElementById("dashboard-status").textContent =
                subscription.status;

            document.getElementById("dashboard-cycle").textContent =
                subscription.billing_cycle;

            document.getElementById("dashboard-renewal").textContent =
                subscription.end_date
                    ? new Date(subscription.end_date).toLocaleDateString("en-IN")
                    : "Not scheduled";

            const features = Array.isArray(plan.features)
                ? plan.features
                : [];

            const price = subscription.billing_cycle === "yearly"
                ? plan.yearly_price
                : plan.monthly_price;

            detailsContainer.innerHTML = `
                <div class="customer-active-plan">
                    <span class="section-label">ACTIVE SUBSCRIPTION</span>
                    <h3>${escapeHTML(plan.name)}</h3>
                    <p>${escapeHTML(plan.description || "")}</p>

                    <div class="price-display">
                        <strong>${formatPrice(price)}</strong>
                        <span>/${escapeHTML(subscription.billing_cycle)}</span>
                    </div>

                    <p><strong>Status:</strong> ${escapeHTML(subscription.status)}</p>

                    <h4>Included features</h4>
                    <ul class="pricing-features">
                        ${features.map(feature => `
                            <li>✓ ${escapeHTML(feature)}</li>
                        `).join("")}
                    </ul>
                </div>
            `;
        } else {
            document.getElementById("dashboard-plan").textContent =
                "No active plan";

            document.getElementById("dashboard-status").textContent =
                "Not subscribed";

            document.getElementById("dashboard-cycle").textContent = "—";
            document.getElementById("dashboard-renewal").textContent = "—";
        }

        // Transaction history
        const transactionContainer =
            document.getElementById("customer-transactions");

        if (transactionContainer) {
            if (!data.transactions.length) {
                transactionContainer.innerHTML = `
                    <tr>
                        <td colspan="5" class="table-empty">
                            No transactions yet.
                        </td>
                    </tr>
                `;
            } else {
                transactionContainer.innerHTML =
                    data.transactions.map(transaction => `
                        <tr>
                            <td>${escapeHTML(transaction.reference)}</td>
                            <td>${new Date(transaction.created_at).toLocaleDateString("en-IN")}</td>
                            <td>${formatPrice(transaction.amount)}</td>
                            <td>${escapeHTML(transaction.payment_method)}</td>
                            <td>${escapeHTML(transaction.status)}</td>
                        </tr>
                    `).join("");
            }
        }

    } catch (error) {
        console.error("Customer dashboard error:", error);

        detailsContainer.innerHTML = `
            <p>Unable to load your subscription information. Please refresh.</p>
        `;
    }
}

// Initialize customer dashboard
document.addEventListener("DOMContentLoaded", () => {
    loadCustomerDashboard();
});
