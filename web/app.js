/**
 * SpendSense — Frontend Application Controller (Vanilla JS)
 * 
 * Manages state, API communication, table filtering/sorting,
 * dynamic SVG charts, and safe DOM manipulation.
 */

"use strict";

const CATEGORY_COLORS = {
  "Dining": "#fbbf24",        // Amber / Gold
  "Groceries": "#34d399",     // Mint / Emerald
  "Subscriptions": "#c084fc", // Purple / Violet
  "Transport": "#38bdf8",     // Sky / Cyan
  "Transfer": "#7dd3fc",      // Light Cyan
  "Income": "#4ade80",        // Green
  "Refund": "#f472b6",        // Pink
  "Uncategorized": "#94a3b8", // Slate
  "Other Credit": "#cbd5e1",  // Light Slate
};

class SpendSenseApp {
  constructor() {
    this.data = null;
    this.pendingFile = null;
    this.pendingFileContent = null;
    this.activeTab = "tab-dashboard";

    this.initElements();
    this.initEventListeners();
  }

  initElements() {
    // Navigation
    this.tabButtons = document.querySelectorAll(".tab-btn");
    this.tabContents = document.querySelectorAll(".tab-content");

    // Badges & Counters
    this.datasetBadgeText = document.getElementById("datasetBadgeText");
    this.datasetBadge = document.getElementById("datasetBadge");
    this.navTxCount = document.getElementById("navTxCount");
    this.navOutlierCount = document.getElementById("navOutlierCount");

    // Metrics Quartet
    this.totalExpensesVal = document.getElementById("totalExpensesVal");
    this.expenseCountLabel = document.getElementById("expenseCountLabel");
    this.totalCreditsVal = document.getElementById("totalCreditsVal");
    this.creditCountLabel = document.getElementById("creditCountLabel");
    this.totalTransfersVal = document.getElementById("totalTransfersVal");
    this.transferCountLabel = document.getElementById("transferCountLabel");
    this.outlierCountVal = document.getElementById("outlierCountVal");
    this.outlierSummaryLabel = document.getElementById("outlierSummaryLabel");

    // Dashboard
    this.dashboardOutlierAlert = document.getElementById("dashboardOutlierAlert");
    this.dashboardOutlierText = document.getElementById("dashboardOutlierText");
    this.categoryDonutSvg = document.getElementById("categoryDonutSvg");
    this.donutCenterAmount = document.getElementById("donutCenterAmount");
    this.categoryBarsList = document.getElementById("categoryBarsList");
    this.categoryCountBadge = document.getElementById("categoryCountBadge");
    this.recentTransactionsList = document.getElementById("recentTransactionsList");

    // Transactions Table & Controls
    this.txSearchInput = document.getElementById("txSearchInput");
    this.filterCategory = document.getElementById("filterCategory");
    this.filterType = document.getElementById("filterType");
    this.sortOrder = document.getElementById("sortOrder");
    this.transactionsTbody = document.getElementById("transactionsTbody");
    this.tableResultsCount = document.getElementById("tableResultsCount");

    // Spending Tab
    this.spendingCategoriesTbody = document.getElementById("spendingCategoriesTbody");
    this.creditsBreakdownList = document.getElementById("creditsBreakdownList");
    this.transfersBreakdownList = document.getElementById("transfersBreakdownList");

    // Outliers Tab
    this.flaggedOutliersContainer = document.getElementById("flaggedOutliersContainer");
    this.flaggedCountBadge = document.getElementById("flaggedCountBadge");
    this.notEvaluatedList = document.getElementById("notEvaluatedList");

    // Import Tab
    this.dropZone = document.getElementById("dropZone");
    this.fileInput = document.getElementById("fileInput");
    this.fileSelectedBox = document.getElementById("fileSelectedBox");
    this.selectedFileName = document.getElementById("selectedFileName");
    this.selectedFileSize = document.getElementById("selectedFileSize");
    this.btnCancelFile = document.getElementById("btnCancelFile");
    this.btnExecuteImport = document.getElementById("btnExecuteImport");
    this.importSpinner = document.getElementById("importSpinner");
    this.importResultAlert = document.getElementById("importResultAlert");
    this.importResultIcon = document.getElementById("importResultIcon");
    this.importResultTitle = document.getElementById("importResultTitle");
    this.importResultMessage = document.getElementById("importResultMessage");
    this.rejectionsDetailBox = document.getElementById("rejectionsDetailBox");
    this.rejectionsTbody = document.getElementById("rejectionsTbody");

    // Quick Actions & Dataset Selectors
    this.btnOpenImport = document.getElementById("btnOpenImport");
    this.btnReloadSample = document.getElementById("btnReloadSample");
    this.btnQuickLoadSample = document.getElementById("btnQuickLoadSample");
    this.headerDatasetSelect = document.getElementById("headerDatasetSelect");
    this.btnLoadHeaderDataset = document.getElementById("btnLoadHeaderDataset");
    this.btnExampleLoadList = document.querySelectorAll(".btn-example-load");
  }

  initEventListeners() {
    // Tab switching
    this.tabButtons.forEach(btn => {
      btn.addEventListener("click", () => {
        const targetTab = btn.getAttribute("data-tab");
        this.switchTab(targetTab);
      });
    });

    // Quick Action: open import tab
    if (this.btnOpenImport) {
      this.btnOpenImport.addEventListener("click", () => this.switchTab("tab-import"));
    }

    // Quick Action: reload sample
    if (this.btnReloadSample) {
      this.btnReloadSample.addEventListener("click", () => this.loadSampleData());
    }
    if (this.btnQuickLoadSample) {
      this.btnQuickLoadSample.addEventListener("click", () => this.loadSampleData());
    }

    // Dataset Selector & Examples
    if (this.btnLoadHeaderDataset && this.headerDatasetSelect) {
      this.btnLoadHeaderDataset.addEventListener("click", () => {
        this.loadExampleData(this.headerDatasetSelect.value);
      });
      this.headerDatasetSelect.addEventListener("change", () => {
        this.loadExampleData(this.headerDatasetSelect.value);
      });
    }

    if (this.btnExampleLoadList) {
      this.btnExampleLoadList.forEach(btn => {
        btn.addEventListener("click", () => {
          const ex = btn.getAttribute("data-example");
          if (ex) this.loadExampleData(ex);
        });
      });
    }

    // Transaction filtering & search
    if (this.txSearchInput) {
      this.txSearchInput.addEventListener("input", () => this.renderTransactionsTable());
    }
    if (this.filterCategory) {
      this.filterCategory.addEventListener("change", () => this.renderTransactionsTable());
    }
    if (this.filterType) {
      this.filterType.addEventListener("change", () => this.renderTransactionsTable());
    }
    if (this.sortOrder) {
      this.sortOrder.addEventListener("change", () => this.renderTransactionsTable());
    }

    // File Drag and Drop
    if (this.dropZone && this.fileInput) {
      this.dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        this.dropZone.classList.add("dragover");
      });
      this.dropZone.addEventListener("dragleave", () => {
        this.dropZone.classList.remove("dragover");
      });
      this.dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        this.dropZone.classList.remove("dragover");
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
          this.handleFileSelected(e.dataTransfer.files[0]);
        }
      });

      this.fileInput.addEventListener("change", (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.handleFileSelected(e.target.files[0]);
        }
      });
    }

    // Cancel selected file
    if (this.btnCancelFile) {
      this.btnCancelFile.addEventListener("click", () => this.clearSelectedFile());
    }

    // Execute import
    if (this.btnExecuteImport) {
      this.btnExecuteImport.addEventListener("click", () => this.executeImport());
    }
  }

  switchTab(tabId) {
    this.activeTab = tabId;
    this.tabButtons.forEach(btn => {
      const match = btn.getAttribute("data-tab") === tabId;
      btn.classList.toggle("active", match);
      btn.setAttribute("aria-selected", match ? "true" : "false");
    });

    this.tabContents.forEach(content => {
      content.classList.toggle("active", content.id === tabId);
    });
  }

  async loadInitialData() {
    try {
      const res = await fetch("/api/data");
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      this.data = await res.json();
      this.renderAll();
    } catch (err) {
      console.error("Failed to fetch initial SpendSense data:", err);
      this.datasetBadgeText.textContent = "Error connecting to server";
      this.datasetBadge.classList.replace("badge-neutral", "badge-warning-pill");
    }
  }

  renderAll() {
    if (!this.data) return;

    this.renderHeaderStatus();
    this.renderMetricCards();
    this.renderDashboard();
    this.renderTransactionsTable();
    this.renderSpendingTab();
    this.renderOutliersTab();
  }

  renderHeaderStatus() {
    const importStats = this.data.import_stats || {};
    const count = (this.data.transactions || []).length;
    const source = importStats.source || "Database";

    if (count > 0) {
      this.datasetBadgeText.textContent = `${source} (${count} records)`;
      this.datasetBadge.className = "status-badge badge-neutral";
    } else {
      this.datasetBadgeText.textContent = "No dataset loaded";
      this.datasetBadge.className = "status-badge badge-warning-pill";
    }

    if (this.navTxCount) this.navTxCount.textContent = count;
    
    const outlierCount = (this.data.outliers?.potential_outliers || []).length;
    if (this.navOutlierCount) this.navOutlierCount.textContent = outlierCount;
  }

  renderMetricCards() {
    const summary = this.data.summary || {};
    const outliers = this.data.outliers || {};

    // 1. Ordinary Expenses
    this.totalExpensesVal.textContent = summary.total_expenses_inr || "₹0.00";
    let debitCount = 0;
    (summary.expenses_by_category || []).forEach(c => debitCount += c.transaction_count);
    this.expenseCountLabel.textContent = `${debitCount} debit transactions`;

    // 2. Credits
    this.totalCreditsVal.textContent = summary.total_credits_inr || "₹0.00";
    let creditCount = 0;
    (summary.credits_by_category || []).forEach(c => creditCount += c.transaction_count);
    this.creditCountLabel.textContent = `${creditCount} credit entries`;

    // 3. Transfers
    const transfers = summary.transfers || {};
    this.totalTransfersVal.textContent = transfers.total_inr || "₹0.00";
    this.transferCountLabel.textContent = `${transfers.transaction_count || 0} transfers tracked`;

    // 4. Outliers
    const outlierCount = (outliers.potential_outliers || []).length;
    this.outlierCountVal.textContent = outlierCount;
    if (outlierCount > 0) {
      this.outlierSummaryLabel.textContent = "Flagged: |Z| > 3.5";
      document.getElementById("outlierMetricCard").style.borderColor = "var(--color-warning)";
    } else {
      this.outlierSummaryLabel.textContent = "No anomalies detected";
      document.getElementById("outlierMetricCard").style.borderColor = "var(--border-subtle)";
    }
  }

  renderDashboard() {
    const summary = this.data.summary || {};
    const outliers = this.data.outliers || {};
    const categories = summary.expenses_by_category || [];
    const totalPaise = summary.total_expenses_paise || 0;

    // Outlier Alert Banner
    const flagged = outliers.potential_outliers || [];
    if (flagged.length > 0) {
      this.dashboardOutlierAlert.style.display = "flex";
      const first = flagged[0];
      this.dashboardOutlierText.textContent = 
        `${first.description} (${first.amount_inr}) in ${first.category} has a Modified Z-score of ${first.modified_z_score}, exceeding threshold 3.5.`;
    } else {
      this.dashboardOutlierAlert.style.display = "none";
    }

    // Donut Chart & Category Bars
    this.categoryCountBadge.textContent = `${categories.length} categories`;
    this.donutCenterAmount.textContent = summary.total_expenses_inr || "₹0.00";
    this.renderDonutChart(categories, totalPaise);

    // Recent Transactions (first 5)
    this.recentTransactionsList.innerHTML = "";
    const txs = this.data.transactions || [];
    const recent = txs.slice(0, 5);

    if (recent.length === 0) {
      const emptyItem = document.createElement("div");
      emptyItem.className = "recent-item";
      emptyItem.textContent = "No recent transactions found.";
      this.recentTransactionsList.appendChild(emptyItem);
      return;
    }

    recent.forEach(tx => {
      const item = document.createElement("div");
      item.className = "recent-item";

      const left = document.createElement("div");
      left.className = "recent-left";

      const badge = document.createElement("span");
      badge.className = `cat-badge cat-${tx.category.toLowerCase().replace(/[^a-z0-9]/g, "")}`;
      badge.textContent = tx.category;

      const descBox = document.createElement("div");
      const desc = document.createElement("div");
      desc.className = "recent-desc";
      desc.textContent = tx.description;

      const meta = document.createElement("div");
      meta.className = "recent-meta";
      meta.textContent = `${tx.transaction_date} • ${tx.transaction_type}`;

      descBox.appendChild(desc);
      descBox.appendChild(meta);
      left.appendChild(badge);
      left.appendChild(descBox);

      const amount = document.createElement("div");
      amount.className = `recent-amount amount-${tx.transaction_type.toLowerCase()}`;
      if (tx.category === "Transfer") {
        amount.className = "recent-amount amount-transfer";
      }
      amount.textContent = tx.amount_inr;

      item.appendChild(left);
      item.appendChild(amount);
      this.recentTransactionsList.appendChild(item);
    });
  }

  renderDonutChart(categories, totalPaise) {
    this.categoryDonutSvg.innerHTML = "";
    this.categoryBarsList.innerHTML = "";

    const radius = 60;
    const circumference = 2 * Math.PI * radius; // ~376.99
    let accumulatedOffset = 0;

    if (categories.length === 0 || totalPaise === 0) {
      // Empty placeholder ring
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", "80");
      circle.setAttribute("cy", "80");
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", "transparent");
      circle.setAttribute("stroke", "var(--border-subtle)");
      circle.setAttribute("stroke-width", "20");
      this.categoryDonutSvg.appendChild(circle);
      return;
    }

    categories.forEach((cat) => {
      const color = CATEGORY_COLORS[cat.category] || "#94a3b8";
      const fraction = cat.total_paise / totalPaise;
      const strokeLength = fraction * circumference;
      const strokeGap = circumference - strokeLength;

      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", "80");
      circle.setAttribute("cy", "80");
      circle.setAttribute("r", radius);
      circle.setAttribute("fill", "transparent");
      circle.setAttribute("stroke", color);
      circle.setAttribute("stroke-width", "20");
      circle.setAttribute("stroke-dasharray", `${strokeLength} ${strokeGap}`);
      circle.setAttribute("stroke-dashoffset", -accumulatedOffset);
      this.categoryDonutSvg.appendChild(circle);

      accumulatedOffset += strokeLength;

      // Category Bar Row
      const barItem = document.createElement("div");
      barItem.className = "cat-bar-item";

      const header = document.createElement("div");
      header.className = "cat-bar-header";

      const nameSpan = document.createElement("span");
      nameSpan.className = "cat-bar-name";
      const dot = document.createElement("span");
      dot.className = "cat-color-dot";
      dot.style.backgroundColor = color;
      nameSpan.appendChild(dot);
      nameSpan.appendChild(document.createTextNode(cat.category));

      const amountSpan = document.createElement("span");
      amountSpan.className = "cat-bar-amount";
      amountSpan.textContent = `${cat.total_inr} (${cat.percentage}%)`;

      header.appendChild(nameSpan);
      header.appendChild(amountSpan);

      const track = document.createElement("div");
      track.className = "cat-bar-track";
      const fill = document.createElement("div");
      fill.className = "cat-bar-fill";
      fill.style.backgroundColor = color;
      fill.style.width = `${cat.percentage}%`;
      track.appendChild(fill);

      barItem.appendChild(header);
      barItem.appendChild(track);
      this.categoryBarsList.appendChild(barItem);
    });
  }

  renderTransactionsTable() {
    if (!this.data) return;

    const allTx = this.data.transactions || [];
    const outlierIds = new Set(
      (this.data.outliers?.potential_outliers || []).map(o => o.id)
    );

    // Populate category dropdown options if not yet populated
    if (this.filterCategory.options.length <= 1) {
      const categories = new Set(allTx.map(t => t.category));
      categories.forEach(cat => {
        const opt = document.createElement("option");
        opt.value = cat;
        opt.textContent = cat;
        this.filterCategory.appendChild(opt);
      });
    }

    const searchQuery = (this.txSearchInput?.value || "").trim().toLowerCase();
    const selectedCat = this.filterCategory.value;
    const selectedType = this.filterType.value;
    const sortVal = this.sortOrder.value;

    let filtered = allTx.filter(t => {
      if (selectedCat !== "ALL" && t.category !== selectedCat) return false;
      if (selectedType !== "ALL" && t.transaction_type !== selectedType) return false;
      if (searchQuery && !t.description.toLowerCase().includes(searchQuery)) return false;
      return true;
    });

    // Sorting
    filtered.sort((a, b) => {
      if (sortVal === "date-desc") return b.transaction_date.localeCompare(a.transaction_date);
      if (sortVal === "date-asc") return a.transaction_date.localeCompare(b.transaction_date);
      if (sortVal === "amount-desc") return b.amount_paise - a.amount_paise;
      if (sortVal === "amount-asc") return a.amount_paise - b.amount_paise;
      return 0;
    });

    this.transactionsTbody.innerHTML = "";
    this.tableResultsCount.textContent = `Showing ${filtered.length} of ${allTx.length} transactions`;

    if (filtered.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 7;
      td.style.textAlign = "center";
      td.style.padding = "24px";
      td.textContent = "No transactions match your search and filter criteria.";
      tr.appendChild(td);
      this.transactionsTbody.appendChild(tr);
      return;
    }

    filtered.forEach(tx => {
      const isOutlier = outlierIds.has(tx.id);
      const tr = document.createElement("tr");
      if (isOutlier) tr.className = "tr-outlier";

      // ID
      const tdId = document.createElement("td");
      tdId.textContent = `#${tx.id}`;

      // Date
      const tdDate = document.createElement("td");
      tdDate.textContent = tx.transaction_date;

      // Description
      const tdDesc = document.createElement("td");
      tdDesc.style.fontWeight = "500";
      tdDesc.style.color = "var(--text-primary)";
      tdDesc.textContent = tx.description;
      if (isOutlier) {
        const tag = document.createElement("span");
        tag.className = "outlier-pill-tag";
        tag.textContent = "Outlier";
        tdDesc.appendChild(tag);
      }

      // Category
      const tdCat = document.createElement("td");
      const catBadge = document.createElement("span");
      catBadge.className = `cat-badge cat-${tx.category.toLowerCase().replace(/[^a-z0-9]/g, "")}`;
      catBadge.textContent = tx.category;
      tdCat.appendChild(catBadge);

      // Rule ID
      const tdRule = document.createElement("td");
      tdRule.style.fontFamily = "var(--font-mono)";
      tdRule.style.fontSize = "11px";
      tdRule.textContent = tx.rule_id;

      // Type
      const tdType = document.createElement("td");
      const typeSpan = document.createElement("span");
      typeSpan.className = `type-${tx.transaction_type.toLowerCase()}`;
      typeSpan.textContent = tx.transaction_type;
      tdType.appendChild(typeSpan);

      // Amount
      const tdAmount = document.createElement("td");
      tdAmount.style.textAlign = "right";
      tdAmount.style.fontWeight = "600";
      if (tx.transaction_type === "CREDIT") {
        tdAmount.style.color = "var(--color-credit)";
      } else if (tx.category === "Transfer") {
        tdAmount.style.color = "var(--color-transfer)";
      } else {
        tdAmount.style.color = "var(--text-primary)";
      }
      tdAmount.textContent = tx.amount_inr;

      tr.appendChild(tdId);
      tr.appendChild(tdDate);
      tr.appendChild(tdDesc);
      tr.appendChild(tdCat);
      tr.appendChild(tdRule);
      tr.appendChild(tdType);
      tr.appendChild(tdAmount);

      this.transactionsTbody.appendChild(tr);
    });
  }

  renderSpendingTab() {
    if (!this.data) return;

    const summary = this.data.summary || {};
    const categories = summary.expenses_by_category || [];

    // Category Table
    this.spendingCategoriesTbody.innerHTML = "";
    if (categories.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 4;
      td.style.textAlign = "center";
      td.textContent = "No ordinary debit expenses found.";
      tr.appendChild(td);
      this.spendingCategoriesTbody.appendChild(tr);
    } else {
      categories.forEach(cat => {
        const tr = document.createElement("tr");

        const tdName = document.createElement("td");
        const dot = document.createElement("span");
        dot.className = "cat-color-dot";
        dot.style.backgroundColor = CATEGORY_COLORS[cat.category] || "#94a3b8";
        dot.style.marginRight = "8px";
        tdName.appendChild(dot);
        tdName.appendChild(document.createTextNode(cat.category));

        const tdCount = document.createElement("td");
        tdCount.style.textAlign = "center";
        tdCount.textContent = cat.transaction_count;

        const tdAmount = document.createElement("td");
        tdAmount.style.textAlign = "right";
        tdAmount.style.fontWeight = "600";
        tdAmount.textContent = cat.total_inr;

        const tdBar = document.createElement("td");
        const barWrap = document.createElement("div");
        barWrap.className = "cat-bar-track";
        const fill = document.createElement("div");
        fill.className = "cat-bar-fill";
        fill.style.backgroundColor = CATEGORY_COLORS[cat.category] || "#94a3b8";
        fill.style.width = `${cat.percentage}%`;
        barWrap.appendChild(fill);
        tdBar.appendChild(barWrap);

        tr.appendChild(tdName);
        tr.appendChild(tdCount);
        tr.appendChild(tdAmount);
        tr.appendChild(tdBar);
        this.spendingCategoriesTbody.appendChild(tr);
      });
    }

    // Credits Breakdown
    this.creditsBreakdownList.innerHTML = "";
    const credits = summary.credits_by_category || [];
    if (credits.length === 0) {
      this.creditsBreakdownList.innerHTML = "<div class='breakdown-row'><span>No credits recorded</span></div>";
    } else {
      credits.forEach(c => {
        const row = document.createElement("div");
        row.className = "breakdown-row";
        row.innerHTML = `
          <span class="breakdown-cat-name">${c.category} (${c.transaction_count})</span>
          <span class="breakdown-amount" style="color: var(--color-credit)">${c.total_inr}</span>
        `;
        this.creditsBreakdownList.appendChild(row);
      });
    }

    // Transfers Breakdown
    this.transfersBreakdownList.innerHTML = "";
    const transfers = summary.transfers?.by_type || [];
    if (transfers.length === 0) {
      this.transfersBreakdownList.innerHTML = "<div class='breakdown-row'><span>No transfers recorded</span></div>";
    } else {
      transfers.forEach(t => {
        const row = document.createElement("div");
        row.className = "breakdown-row";
        row.innerHTML = `
          <span class="breakdown-cat-name">${t.transaction_type} Transfer (${t.transaction_count})</span>
          <span class="breakdown-amount" style="color: var(--color-transfer)">${t.total_inr}</span>
        `;
        this.transfersBreakdownList.appendChild(row);
      });
    }
  }

  renderOutliersTab() {
    if (!this.data) return;

    const outliers = this.data.outliers || {};
    const flagged = outliers.potential_outliers || [];
    const notEvaluated = outliers.not_evaluated || [];

    this.flaggedCountBadge.textContent = `${flagged.length} flagged`;
    this.flaggedOutliersContainer.innerHTML = "";

    if (flagged.length === 0) {
      const emptyCard = document.createElement("div");
      emptyCard.className = "panel card-panel";
      emptyCard.style.gridColumn = "1 / -1";
      emptyCard.style.textAlign = "center";
      emptyCard.style.padding = "36px";
      emptyCard.innerHTML = `
        <h3 style="color: var(--color-credit); margin-bottom: 6px;">Zero Outliers Flagged</h3>
        <p style="color: var(--text-muted); font-size: 13px;">All evaluated categories conform to standard dispersion thresholds (|Modified Z| &le; 3.5).</p>
      `;
      this.flaggedOutliersContainer.appendChild(emptyCard);
    } else {
      flagged.forEach(o => {
        const card = document.createElement("div");
        card.className = "outlier-card";

        card.innerHTML = `
          <div class="outlier-card-top">
            <span class="outlier-merchant">${o.description}</span>
            <span class="outlier-score-pill">Z = ${o.modified_z_score}</span>
          </div>
          <div class="outlier-amount">${o.amount_inr}</div>
          <div class="outlier-meta-row">
            <span><strong>Date:</strong> ${o.transaction_date}</span>
            <span><strong>Category:</strong> ${o.category}</span>
            <span><strong>ID:</strong> #${o.id}</span>
          </div>
          <p class="outlier-explanation">${o.explanation}</p>
        `;
        this.flaggedOutliersContainer.appendChild(card);
      });
    }

    // Guardrails List
    this.notEvaluatedList.innerHTML = "";
    if (notEvaluated.length === 0) {
      this.notEvaluatedList.innerHTML = "<p style='color: var(--text-muted)'>All categories had sufficient history and non-zero MAD.</p>";
    } else {
      notEvaluated.forEach(item => {
        const div = document.createElement("div");
        div.className = "guardrail-item";
        div.innerHTML = `
          <div class="guardrail-cat-header">
            <span class="guardrail-cat-title">${item.category}</span>
            <span class="guardrail-status-pill">${item.status}</span>
          </div>
          <p class="guardrail-reason">${item.reason}</p>
        `;
        this.notEvaluatedList.appendChild(div);
      });
    }
  }

  handleFileSelected(file) {
    if (!file) return;
    this.pendingFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
      this.pendingFileContent = e.target.result;
      this.selectedFileName.textContent = file.name;
      this.selectedFileSize.textContent = `${(file.size / 1024).toFixed(1)} KB`;
      this.fileSelectedBox.style.display = "block";
      this.importResultAlert.style.display = "none";
    };
    reader.readAsText(file, "UTF-8");
  }

  clearSelectedFile() {
    this.pendingFile = null;
    this.pendingFileContent = null;
    this.fileSelectedBox.style.display = "none";
    this.fileInput.value = "";
  }

  async executeImport() {
    if (!this.pendingFileContent) return;

    this.importSpinner.style.display = "inline-block";
    this.btnExecuteImport.disabled = true;

    try {
      const response = await fetch("/api/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: this.pendingFile.name,
          csv_content: this.pendingFileContent
        }),
      });

      const result = await response.json();
      this.importSpinner.style.display = "none";
      this.btnExecuteImport.disabled = false;

      if (response.ok && result.success) {
        this.data = result;
        this.renderAll();

        this.showImportResult(
          true,
          "Import Successful!",
          `Successfully ingested and categorized ${result.import_stats.accepted_count} transactions. Dataset atomically replaced.`
        );

        // If there were any rejected rows in a mixed CSV
        const rejections = result.import_stats.rejected_records || [];
        if (rejections.length > 0) {
          this.renderRejections(rejections);
        } else {
          this.rejectionsDetailBox.style.display = "none";
        }

        this.clearSelectedFile();
      } else {
        // Validation or File failure (Database preserved!)
        const err = result.error || "Failed to import CSV file.";
        this.showImportResult(
          false,
          "Import Rejected — Prior Database Preserved",
          err
        );

        const rejections = result.import_stats?.rejected_records || [];
        if (rejections.length > 0) {
          this.renderRejections(rejections);
        } else {
          this.rejectionsDetailBox.style.display = "none";
        }
      }
    } catch (err) {
      this.importSpinner.style.display = "none";
      this.btnExecuteImport.disabled = false;
      this.showImportResult(
        false,
        "Network Error",
        `Could not reach the local SpendSense server: ${err.message}`
      );
    }
  }

  async loadSampleData() {
    return this.loadExampleData("sample_transactions.csv");
  }

  async loadExampleData(datasetName) {
    try {
      const res = await fetch("/api/load-example", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset: datasetName })
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.error || `Server returned HTTP ${res.status}`);
      }
      this.data = await res.json();
      if (this.headerDatasetSelect) {
        this.headerDatasetSelect.value = datasetName;
      }
      this.renderAll();
      this.showImportResult(
        true,
        "Dataset Loaded Successfully",
        `Loaded "${datasetName}" (${this.data.transactions?.length || 0} records). Analysis and outlier screening updated immediately.`
      );
    } catch (err) {
      alert(`Could not load example dataset: ${err.message}`);
    }
  }

  showImportResult(isSuccess, title, message) {
    this.importResultAlert.style.display = "flex";
    this.importResultAlert.className = `alert-callout ${isSuccess ? "alert-success" : "alert-danger"}`;
    this.importResultTitle.textContent = title;
    this.importResultMessage.textContent = message;

    this.importResultIcon.innerHTML = isSuccess 
      ? `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
      : `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
  }

  renderRejections(rejections) {
    this.rejectionsDetailBox.style.display = "block";
    this.rejectionsTbody.innerHTML = "";

    rejections.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${r.record_number || "-"}</td>
        <td>${r.line_number || "-"}</td>
        <td style="color: var(--color-danger)">${r.reason}</td>
      `;
      this.rejectionsTbody.appendChild(tr);
    });
  }
}

// Bootstrap app on DOM load
const app = new SpendSenseApp();
document.addEventListener("DOMContentLoaded", () => {
  app.loadInitialData();
});
