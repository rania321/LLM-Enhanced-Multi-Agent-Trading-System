const socket = io();

document.getElementById("startBtn").onclick = () => {
    socket.emit("start_simulation");
};

const ctx = document.getElementById("chart").getContext("2d");

const chart = new Chart(ctx, {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "Price",
            borderColor: "#1d3557",
            data: []
        }]
    },
    options: {
        animation: false
    }
});

socket.on("update", data => {
    // Chart
    chart.data.labels.push("");
    chart.data.datasets[0].data.push(data.price);
    chart.update();

    // News
    document.getElementById("news").innerText = data.news;

    // Baseline agents
    let decHtml = "";
    data.decisions.forEach(d => {
        decHtml += `<p><b>${d.name}</b>: ${d.action} | cash=${d.cash} | pos=${d.pos} | value=${d.value}</p>`;
    });
    document.getElementById("decisions").innerHTML = decHtml;

    // LLM pipeline
    const llm = data.llm;

    document.getElementById("bullish").innerText = llm.bullish;
    document.getElementById("bearish").innerText = llm.bearish;

    document.getElementById("llmProposal").innerText =
        `Action: ${llm.proposal.action.toUpperCase()} | Size: ${llm.proposal.size}\n` +
        `Rationale: ${llm.proposal.rationale}`;

    let riskHtml = "";
    llm.risk_assessments.forEach(r => {
        riskHtml += `<p><b>${r.name}</b> → approved=${r.approved}, size=${r.size}<br>${r.comment}</p>`;
    });
    document.getElementById("riskAssessments").innerHTML = riskHtml;

    document.getElementById("managerDecision").innerText =
        `Approved: ${llm.manager_decision.approved}, ` +
        `Action: ${llm.manager_decision.final_action.toUpperCase()}, ` +
        `Size: ${llm.manager_decision.final_size}\n` +
        llm.manager_decision.comment;

    document.getElementById("llmPortfolio").innerText =
        `cash=${llm.portfolio.cash} | pos=${llm.portfolio.pos} | value=${llm.portfolio.value}`;
});
