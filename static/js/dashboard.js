// Socket.IO and Chart.js are available as global variables from CDN scripts
const io = window.io // Declare the io variable
const socket = io()

// Chart instances
let priceChart = null
let comparisonChart = null
let actionsChart = null

// Data storage
const priceData = []
let agentPerformance = {}
let actionCounts = { buy: 0, sell: 0, hold: 0 }
let isPaused = false

// Initialize charts
function initCharts() {
  // Price Chart
  const priceCtx = document.getElementById("priceChart").getContext("2d")
  priceChart = new Chart(priceCtx, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: "Market Price",
          data: [],
          borderColor: "#667eea",
          backgroundColor: "rgba(102, 126, 234, 0.1)",
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          pointRadius: 0,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 750,
        easing: "easeInOutQuart",
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          backgroundColor: "rgba(0, 0, 0, 0.8)",
          padding: 12,
          cornerRadius: 8,
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
        },
      },
    },
  })

  // Comparison Chart
  const compCtx = document.getElementById("comparisonChart").getContext("2d")
  comparisonChart = new Chart(compCtx, {
    type: "bar",
    data: {
      labels: [],
      datasets: [
        {
          label: "Portfolio Value",
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
  actionsChart = new Chart(actionsCtx, {
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
          labels: { padding: 20 },
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

// Update LLM pipeline visualization
function updateLLMPipeline(llm) {
  // Bullish evidence
  document.getElementById("bullishEvidence").textContent = llm.bullish

  // Bearish evidence
  document.getElementById("bearishEvidence").textContent = llm.bearish

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

// Start simulation
document.getElementById("startBtn").addEventListener("click", () => {
  const startBtn = document.getElementById("startBtn")
  const statusBadge = document.getElementById("statusBadge")
  const progressContainer = document.getElementById("progressContainer")

  startBtn.disabled = true
  statusBadge.innerHTML = '<span class="status-dot"></span><span>Running...</span>'
  progressContainer.style.display = "block"

  // Reset data
  agentPerformance = {}
  actionCounts = { buy: 0, sell: 0, hold: 0 }

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

    // Update active tab
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"))
    tab.classList.add("active")

    // Update active content
    document.querySelectorAll(".tab-content").forEach((content) => {
      content.classList.remove("active")
    })
    document.getElementById(`${tabName}Tab`).classList.add("active")
  })
})

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

  // Update all components
  updatePriceChart(data.price, data.step)
  updateNews(data.news, data.price, data.history)
  updateAgents(data.decisions)
  updateLLMPipeline(data.llm)
  updatePortfolioStats(data.decisions, data.llm, data.price)
})

socket.on("simulation_finished", (data) => {
  const startBtn = document.getElementById("startBtn")
  const statusBadge = document.getElementById("statusBadge")

  startBtn.disabled = false
  statusBadge.innerHTML = '<span class="status-dot" style="background: #10b981;"></span><span>Completed</span>'

  console.log("Simulation finished:", data.message)
})

// Initialize charts on page load
window.addEventListener("DOMContentLoaded", () => {
  initCharts()
})
