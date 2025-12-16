// Socket.IO and Chart.js are available as global variables from CDN scripts
const socket = window.io()

// Chart instances
let priceChart = null
let comparisonChart = null
let actionsChart = null
let performanceChart = null

// Data storage
const priceData = []
let agentPerformance = {}
let actionCounts = { buy: 0, sell: 0, hold: 0 }
let isPaused = false
let simulationHistory = []
let traderHistory = {}

// Function to render history
function renderHistory(history, filter = "all", searchTerm = "") {
  const historyContainer = document.getElementById("historyContainer")
  historyContainer.innerHTML = ""

  history.forEach((step, index) => {
    const stepDiv = document.createElement("div")
    stepDiv.className = "history-step"

    // Filter by step number if filter is "step"
    if (filter === "step" && index + 1 !== Number.parseInt(searchTerm)) return

    // Filter by news content if filter is "news"
    if (filter === "news" && !step.news.includes(searchTerm)) return

    stepDiv.innerHTML = `
      <h5>Step ${index + 1}</h5>
      <p><strong>Price:</strong> $${step.price.toFixed(2)}</p>
      <p><strong>News:</strong> ${step.news}</p>
      <div class="agents-actions">
        ${step.decisions
          .map(
            (agent) => `
          <div class="agent-action">
            <span class="action-badge ${agent.action}">${agent.action}</span>
            <span>${agent.name}</span>
          </div>
        `,
          )
          .join("")}
      </div>
    `

    historyContainer.appendChild(stepDiv)
  })
}

// Initialize charts
function initCharts() {
  // Price Chart
  const priceCtx = document.getElementById("priceChart").getContext("2d")
  priceChart = new window.Chart(priceCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Price",
          data: [],
          borderColor: "#667eea",
          backgroundColor: "rgba(102, 126, 234, 0.1)",
          borderWidth: 3,
          tension: 0.4,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 300,
      },
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          display: true,
          grid: { display: false },
        },
        y: {
          display: true,
          grid: { color: "rgba(0, 0, 0, 0.05)" },
        },
      },
    },
  })

  // Comparison Chart
  const compCtx = document.getElementById("comparisonChart").getContext("2d")
  comparisonChart = new window.Chart(compCtx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Final Value ($)",
          data: [],
          backgroundColor: [
            "rgba(102, 126, 234, 0.8)",
            "rgba(245, 158, 11, 0.8)",
            "rgba(16, 185, 129, 0.8)",
            "rgba(239, 68, 68, 0.8)",
            "rgba(139, 92, 246, 0.8)",
          ],
          borderRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "rgba(0, 0, 0, 0.05)" },
        },
      },
    },
  })

  // Actions Chart
  const actionsCtx = document.getElementById("actionsChart").getContext("2d")
  actionsChart = new window.Chart(actionsCtx, {
    type: "doughnut",
    data: {
      labels: ["Buy", "Sell", "Hold"],
      datasets: [
        {
          data: [0, 0, 0],
          backgroundColor: ["rgba(16, 185, 129, 0.8)", "rgba(239, 68, 68, 0.8)", "rgba(99, 102, 241, 0.8)"],
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
        },
      },
    },
  })

  const performanceCtx = document.getElementById("performanceChart").getContext("2d")
  performanceChart = new window.Chart(performanceCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 0,
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
        tooltip: {
          mode: "index",
          intersect: false,
        },
      },
      scales: {
        x: {
          display: true,
          grid: { display: false },
        },
        y: {
          display: true,
          grid: { color: "rgba(0, 0, 0, 0.05)" },
          title: {
            display: true,
            text: "Portfolio Value ($)",
          },
        },
      },
    },
  })
}

// Update price chart
function updatePriceChart(price, step) {
  if (!priceChart || isPaused) return

  priceChart.data.labels.push(`Step ${step}`)
  priceChart.data.datasets[0].data.push(price)

  // Keep last 30 data points
  if (priceChart.data.labels.length > 30) {
    priceChart.data.labels.shift()
    priceChart.data.datasets[0].data.shift()
  }

  priceChart.update("none")
}

// Update news display
function updateNews(news, price, history) {
  const newsText = document.getElementById("newsText")
  const newsIcon = document.getElementById("newsIcon")
  const sentimentBadge = document.getElementById("sentimentBadge")

  newsText.textContent = news

  // Determine sentiment
  let sentiment = "neutral"
  let sentimentColor = "#e0e7ff"
  let iconColor = "#667eea"

  if (news.includes("Very positive") || news.includes("rally")) {
    sentiment = "Bullish"
    sentimentColor = "#d1fae5"
    iconColor = "#10b981"
  } else if (news.includes("positive") || news.includes("upward")) {
    sentiment = "Positive"
    sentimentColor = "#d1fae5"
    iconColor = "#10b981"
  } else if (news.includes("Very negative") || news.includes("crash")) {
    sentiment = "Bearish"
    sentimentColor = "#fee2e2"
    iconColor = "#ef4444"
  } else if (news.includes("negative") || news.includes("declin")) {
    sentiment = "Negative"
    sentimentColor = "#fee2e2"
    iconColor = "#ef4444"
  }

  sentimentBadge.textContent = sentiment
  sentimentBadge.style.background = sentimentColor
  sentimentBadge.style.color = iconColor

  newsIcon.style.background = sentimentColor
  newsIcon.querySelector("svg").style.stroke = iconColor
}

// Update agents display
function updateAgents(decisions) {
  const agentsList = document.getElementById("agentsList")
  agentsList.innerHTML = ""

  decisions.forEach((agent, index) => {
    const agentItem = document.createElement("div")
    agentItem.className = "agent-item update"

    // Generate avatar color based on agent name
    const colors = ["#667eea", "#f59e0b", "#10b981", "#ef4444"]
    const avatarColor = colors[index % colors.length]

    agentItem.innerHTML = `
            <div class="agent-info">
                <div class="agent-avatar" style="background: ${avatarColor}">
                    ${agent.name.charAt(0)}
                </div>
                <div class="agent-details">
                    <h4>${agent.name}</h4>
                    <p>Cash: $${agent.cash} | Position: ${agent.pos}</p>
                </div>
            </div>
            <div class="agent-stats">
                <span class="agent-action ${agent.action}">${agent.action}</span>
                <div class="agent-value">$${agent.value}</div>
            </div>
        `

    agentsList.appendChild(agentItem)

    // Store performance data
    agentPerformance[agent.name] = agent.value

    // Count actions
    if (agent.action in actionCounts) {
      actionCounts[agent.action]++
    }
  })

  // Update comparison chart
  updateComparisonChart()
  updateActionsChart()
}

function updateLLMPipeline(llm) {
  // Bullish evidence
  document.getElementById("bullishEvidence").textContent = llm.bullish

  // Bearish evidence
  document.getElementById("bearishEvidence").textContent = llm.bearish

  // General analysis
  if (llm.general_analysis) {
    const stanceBadge = document.getElementById("generalStance").querySelector(".stance-badge")
    const generalEvidence = document.getElementById("generalEvidence")

    stanceBadge.textContent = llm.general_analysis.stance.toUpperCase()
    stanceBadge.className = `stance-badge ${llm.general_analysis.stance}`
    generalEvidence.textContent = llm.general_analysis.text
  }

  // Proposal
  const proposalBox = document.getElementById("proposalBox")
  proposalBox.innerHTML = `
        <h5>Action: <span style="color: #667eea; font-weight: 700;">${llm.proposal.action.toUpperCase()}</span></h5>
        <p><strong>Size:</strong> ${llm.proposal.size}</p>
        <p><strong>Rationale:</strong> ${llm.proposal.rationale}</p>
    `

  // Risk assessments
  const riskGrid = document.getElementById("riskGrid")
  riskGrid.innerHTML = ""

  llm.risk_assessments.forEach((risk) => {
    const riskCard = document.createElement("div")
    riskCard.className = `risk-card ${risk.approved ? "approved" : "rejected"}`
    riskCard.innerHTML = `
            <h5>${risk.name}</h5>
            <p><strong>Status:</strong> ${risk.approved ? "✅ Approved" : "❌ Rejected"}</p>
            <p><strong>Suggested Size:</strong> ${risk.size}</p>
            <p>${risk.comment}</p>
        `
    riskGrid.appendChild(riskCard)
  })

  // Manager decision
  const decisionBox = document.getElementById("decisionBox")
  const statusColor = llm.manager_decision.approved ? "#10b981" : "#ef4444"
  decisionBox.innerHTML = `
        <h5 style="color: ${statusColor};">
            ${llm.manager_decision.approved ? "✅ APPROVED" : "❌ REJECTED"}
        </h5>
        <p><strong>Action:</strong> ${llm.manager_decision.final_action.toUpperCase()}</p>
        <p><strong>Size:</strong> ${llm.manager_decision.final_size}</p>
        <p>${llm.manager_decision.comment}</p>
    `

  // Update LLM portfolio stats
  document.getElementById("llmValue").textContent = `$${llm.portfolio.value}`

  // Add LLM fund to performance tracking
  agentPerformance["LLM Fund"] = llm.portfolio.value
  updateComparisonChart()
}

// Update portfolio stats
function updatePortfolioStats(decisions, llm, price) {
  // Find best and worst performers
  const allAgents = [...decisions, { name: "LLM Fund", value: llm.portfolio.value }]
  allAgents.sort((a, b) => b.value - a.value)

  document.getElementById("bestAgent").textContent = `${allAgents[0].name} ($${allAgents[0].value})`
  document.getElementById("worstAgent").textContent =
    `${allAgents[allAgents.length - 1].name} ($${allAgents[allAgents.length - 1].value})`
  document.getElementById("currentPrice").textContent = `$${price.toFixed(2)}`
}

// Update comparison chart
function updateComparisonChart() {
  if (!comparisonChart) return

  const agents = Object.keys(agentPerformance)
  const values = Object.values(agentPerformance)

  comparisonChart.data.labels = agents
  comparisonChart.data.datasets[0].data = values
  comparisonChart.update("none")
}

// Update actions chart
function updateActionsChart() {
  if (!actionsChart) return

  actionsChart.data.datasets[0].data = [actionCounts.buy, actionCounts.sell, actionCounts.hold]
  actionsChart.update("none")
}

function updatePerformanceChart() {
  if (!performanceChart || simulationHistory.length === 0) return

  const steps = simulationHistory.map((h, i) => `Step ${i + 1}`)

  const traders = new Set()
  simulationHistory.forEach((step) => {
    step.decisions.forEach((d) => traders.add(d.name))
  })

  const colors = {
    Random: "rgba(102, 126, 234, 0.8)",
    Trend: "rgba(245, 158, 11, 0.8)",
    MeanReversion: "rgba(16, 185, 129, 0.8)",
    Holder: "rgba(239, 68, 68, 0.8)",
    "LLM Fund": "rgba(139, 92, 246, 0.8)",
  }

  const datasets = []

  traders.forEach((traderName) => {
    const data = simulationHistory.map((step) => {
      const trader = step.decisions.find((d) => d.name === traderName)
      return trader ? trader.value : null
    })

    datasets.push({
      label: traderName,
      data: data,
      borderColor: colors[traderName] || "rgba(99, 102, 241, 0.8)",
      backgroundColor: (colors[traderName] || "rgba(99, 102, 241, 0.8)").replace("0.8", "0.1"),
      borderWidth: 2,
      tension: 0.4,
      fill: false,
      pointRadius: 2,
      pointHoverRadius: 6,
    })
  })

  const llmData = simulationHistory.map((step) => step.llm.portfolio.value)
  datasets.push({
    label: "LLM Fund",
    data: llmData,
    borderColor: colors["LLM Fund"],
    backgroundColor: colors["LLM Fund"].replace("0.8", "0.1"),
    borderWidth: 3,
    tension: 0.4,
    fill: false,
    pointRadius: 2,
    pointHoverRadius: 6,
  })

  performanceChart.data.labels = steps
  performanceChart.data.datasets = datasets
  performanceChart.update("none")
}

function trackTraderHistory(decisions, step, llm) {
  decisions.forEach((agent) => {
    if (!traderHistory[agent.name]) {
      traderHistory[agent.name] = []
    }
    traderHistory[agent.name].push({
      step: step,
      action: agent.action,
      cash: agent.cash,
      position: agent.pos,
      value: agent.value,
    })
  })

  // Track LLM Fund
  if (!traderHistory["LLM Fund"]) {
    traderHistory["LLM Fund"] = []
  }
  traderHistory["LLM Fund"].push({
    step: step,
    action: llm.manager_decision.final_action,
    cash: llm.portfolio.cash,
    position: llm.portfolio.pos,
    value: llm.portfolio.value,
  })
}

function renderTraderHistory() {
  const traderTabs = document.getElementById("traderTabs")
  const traderHistoryContent = document.getElementById("traderHistoryContent")

  traderTabs.innerHTML = ""
  traderHistoryContent.innerHTML = ""

  const traders = Object.keys(traderHistory)

  traders.forEach((traderName, index) => {
    const tabBtn = document.createElement("button")
    tabBtn.className = `trader-tab ${index === 0 ? "active" : ""}`
    tabBtn.textContent = traderName
    tabBtn.dataset.trader = traderName
    tabBtn.addEventListener("click", () => switchTraderTab(traderName))
    traderTabs.appendChild(tabBtn)

    const content = document.createElement("div")
    content.className = `trader-content ${index === 0 ? "active" : ""}`
    content.id = `trader-${traderName.replace(/\s+/g, "-")}`

    const history = traderHistory[traderName]
    const startValue = history[0].value
    const endValue = history[history.length - 1].value
    const totalReturn = (((endValue - startValue) / startValue) * 100).toFixed(2)
    const returnClass = totalReturn >= 0 ? "positive" : "negative"

    content.innerHTML = `
      <div class="trader-summary">
        <div class="trader-stat">
          <span class="stat-label">Starting Value</span>
          <span class="stat-value">$${startValue.toFixed(2)}</span>
        </div>
        <div class="trader-stat">
          <span class="stat-label">Final Value</span>
          <span class="stat-value">$${endValue.toFixed(2)}</span>
        </div>
        <div class="trader-stat">
          <span class="stat-label">Total Return</span>
          <span class="stat-value ${returnClass}">${totalReturn >= 0 ? "+" : ""}${totalReturn}%</span>
        </div>
        <div class="trader-stat">
          <span class="stat-label">Total Trades</span>
          <span class="stat-value">${history.filter((h) => h.action !== "hold").length}</span>
        </div>
      </div>
      <div class="trader-history-table">
        <table>
          <thead>
            <tr>
              <th>Step</th>
              <th>Action</th>
              <th>Cash</th>
              <th>Position</th>
              <th>Value</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            ${history
              .map((h, i) => {
                const prevValue = i > 0 ? history[i - 1].value : h.value
                const valueChange = h.value - prevValue
                const changePercent = prevValue > 0 ? ((valueChange / prevValue) * 100).toFixed(2) : "0.00"
                const changeClass = valueChange >= 0 ? "positive" : "negative"

                return `
                <tr>
                  <td><strong>Step ${h.step}</strong></td>
                  <td><span class="action-badge ${h.action}">${h.action.toUpperCase()}</span></td>
                  <td>$${h.cash.toFixed(2)}</td>
                  <td>${h.position}</td>
                  <td><strong>$${h.value.toFixed(2)}</strong></td>
                  <td class="${changeClass}">
                    ${valueChange >= 0 ? "+" : ""}${valueChange.toFixed(2)} (${changePercent >= 0 ? "+" : ""}${changePercent}%)
                  </td>
                </tr>
              `
              })
              .join("")}
          </tbody>
        </table>
      </div>
    `

    traderHistoryContent.appendChild(content)
  })
}

function switchTraderTab(traderName) {
  // Update active tab
  document.querySelectorAll(".trader-tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.trader === traderName)
  })

  // Update active content
  document.querySelectorAll(".trader-content").forEach((content) => {
    content.classList.toggle("active", content.id === `trader-${traderName.replace(/\s+/g, "-")}`)
  })
}

function exportHistory() {
  const dataStr = JSON.stringify(simulationHistory, null, 2)
  const dataBlob = new Blob([dataStr], { type: "application/json" })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement("a")
  link.href = url
  link.download = `trading-simulation-${new Date().toISOString()}.json`
  link.click()
  URL.revokeObjectURL(url)
}

function exportTraderData() {
  const dataStr = JSON.stringify(traderHistory, null, 2)
  const dataBlob = new Blob([dataStr], { type: "application/json" })
  const url = URL.createObjectURL(dataBlob)
  const link = document.createElement("a")
  link.href = url
  link.download = `trader-history-${new Date().toISOString()}.json`
  link.click()
  URL.revokeObjectURL(url)
}

// Start simulation
document.getElementById("startBtn").addEventListener("click", () => {
  const startBtn = document.getElementById("startBtn")
  const statusBadge = document.getElementById("statusBadge")
  const progressContainer = document.getElementById("progressContainer")
  const historyCard = document.getElementById("historyCard")
  const traderHistoryCard = document.getElementById("traderHistoryCard")

  startBtn.disabled = true
  statusBadge.innerHTML = '<span class="status-dot"></span><span>Running...</span>'
  progressContainer.style.display = "block"
  historyCard.style.display = "none"
  traderHistoryCard.style.display = "none"

  // Reset data
  agentPerformance = {}
  actionCounts = { buy: 0, sell: 0, hold: 0 }
  simulationHistory = []
  traderHistory = {}

  socket.emit("start_simulation")
})

// Pause/Resume button
document.getElementById("pauseBtn").addEventListener("click", () => {
  isPaused = !isPaused
  const pauseBtn = document.getElementById("pauseBtn")

  if (isPaused) {
    pauseBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
        `
    pauseBtn.title = "Resume"
  } else {
    pauseBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <rect x="6" y="4" width="4" height="16"/>
                <rect x="14" y="4" width="4" height="16"/>
            </svg>
        `
    pauseBtn.title = "Pause"
  }
})

// Tab switching
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const tabName = tab.dataset.tab

    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"))
    tab.classList.add("active")

    document.querySelectorAll(".tab-content").forEach((content) => content.classList.remove("active"))

    if (tabName === "comparison") {
      document.getElementById("comparisonTab").classList.add("active")
    } else if (tabName === "actions") {
      document.getElementById("actionsTab").classList.add("active")
    } else if (tabName === "performance") {
      document.getElementById("performanceTab").classList.add("active")
      updatePerformanceChart()
    }
  })
})

document.getElementById("historyFilter")?.addEventListener("change", (e) => {
  const searchTerm = document.getElementById("historySearch").value
  renderHistory(simulationHistory, e.target.value, searchTerm)
})

document.getElementById("historySearch")?.addEventListener("input", (e) => {
  const filter = document.getElementById("historyFilter").value
  renderHistory(simulationHistory, filter, e.target.value)
})

document.getElementById("exportHistoryBtn")?.addEventListener("click", exportHistory)
document.getElementById("exportTradersBtn")?.addEventListener("click", exportTraderData)

// Socket.IO event handlers
socket.on("connect", () => {
  console.log("Connected to server")
})

socket.on("update", (data) => {
  if (isPaused) return

  // Update progress
  const progressBar = document.getElementById("progressBar")
  const progressText = document.getElementById("progressText")
  const progress = (data.step / data.total_steps) * 100
  progressBar.style.width = `${progress}%`
  progressText.textContent = `Step ${data.step} / ${data.total_steps}`

  simulationHistory.push(data)

  // Update all components
  updatePriceChart(data.price, data.step)
  updateNews(data.news, data.price, data.history)
  updateAgents(data.decisions)
  updateLLMPipeline(data.llm)
  updatePortfolioStats(data.decisions, data.llm, data.price)

  trackTraderHistory(data.decisions, data.step, data.llm)
  updatePerformanceChart()
})

socket.on("simulation_finished", (data) => {
  const startBtn = document.getElementById("startBtn")
  const statusBadge = document.getElementById("statusBadge")
  const historyCard = document.getElementById("historyCard")
  const traderHistoryCard = document.getElementById("traderHistoryCard")

  startBtn.disabled = false
  statusBadge.innerHTML = '<span class="status-dot" style="background: #10b981;"></span><span>Completed</span>'

  historyCard.style.display = "block"
  traderHistoryCard.style.display = "block"
  simulationHistory = data.history || simulationHistory
  renderHistory(simulationHistory)
  renderTraderHistory()

  // Scroll to history
  historyCard.scrollIntoView({ behavior: "smooth", block: "start" })

  console.log("Simulation finished:", data.message)
})

// Initialize charts on page load
window.addEventListener("DOMContentLoaded", () => {
  initCharts()
})
