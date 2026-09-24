document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatContainer = document.getElementById('chat-container');
    const suggestionChips = document.querySelectorAll('.suggestion-chip');
    
    // View switching
    const navChat = document.getElementById('nav-chat');
    const navLogs = document.getElementById('nav-logs');
    const chatView = document.getElementById('chat-view');
    const logsView = document.getElementById('logs-view');
    const logsContainer = document.getElementById('logs-container');
    
    let sessionLogs = [];

    // Right sidebar elements
    const traceList = document.getElementById('trace-list');
    const agentNameDisplay = document.getElementById('agent-name-display');
    const flowAgentName = document.getElementById('flow-agent-name');
    const currentStepTitle = document.getElementById('current-step-title');
    const currentStepDesc = document.getElementById('current-step-desc');
    const totalTimeDisplay = document.getElementById('total-time-display');
    
    const metricLatency = document.getElementById('metric-latency');
    const metricTokens = document.getElementById('metric-tokens');
    const metricCost = document.getElementById('metric-cost');

    function appendUserMessage(text) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message-wrapper user';
        msgDiv.innerHTML = `
            <div class="message user-message">
                <div class="msg-avatar"><i class="fa-solid fa-user"></i></div>
                <div class="msg-content">
                    <div class="msg-header">
                        <span>You</span>
                        <span class="msg-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                    <div class="msg-bubble">${text}</div>
                </div>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function appendAgentMessage(text, agentName) {
        // Formatting the text a bit to make lists look nice if there are bullets
        const formattedText = text.replace(/- /g, '• ');
        const name = agentName || "Support Agent";

        const msgDiv = document.createElement('div');
        msgDiv.className = 'message-wrapper agent';
        msgDiv.innerHTML = `
            <div class="message agent-message">
                <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-content">
                    <div class="msg-header">
                        <span>${name}</span>
                        <span class="badge" style="font-size: 0.65rem">Active</span>
                        <span class="msg-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                    </div>
                    <div class="msg-bubble" style="white-space: pre-wrap;">${formattedText}</div>
                </div>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    const flowSteps = document.querySelectorAll('.flow-step');
    const flowIcons = document.querySelectorAll('.flow-icon');

    function setActiveStep(stepIndex) {
        flowSteps.forEach((step, i) => {
            if (i === stepIndex) {
                step.classList.add('active-flow');
                flowIcons[i].classList.add('active-icon');
            } else {
                step.classList.remove('active-flow');
                flowIcons[i].classList.remove('active-icon');
            }
        });
    }

    function updateRightSidebar(traceArray, durationSecs) {
        // ... (rest of the logic remains unchanged until we set active step)
        traceList.innerHTML = '';
        traceArray.forEach(traceItem => {
            const li = document.createElement('li');
            li.innerHTML = `
                <div class="trace-title">${traceItem}</div>
                <div class="trace-desc">Step completed</div>
            `;
            traceList.appendChild(li);
        });

        let agentName = "General Agent";
        const routeTrace = traceArray.find(t => t.includes("assigned to"));
        if(routeTrace) {
            if(routeTrace.includes("technical")) agentName = "Technical Support";
            if(routeTrace.includes("billing")) agentName = "Billing Support";
        }

        agentNameDisplay.innerText = agentName;
        flowAgentName.innerText = agentName;
        
        currentStepTitle.innerText = "Response Ready";
        currentStepDesc.innerText = "Successfully processed and answered.";
        
        totalTimeDisplay.innerText = durationSecs.toFixed(1) + "s";
        metricLatency.innerText = durationSecs.toFixed(1) + "s";
        
        const mockTokens = Math.floor(Math.random() * 500) + 200;
        metricTokens.innerText = mockTokens;
        
        const mockCost = (mockTokens * 0.000002).toFixed(4);
        metricCost.innerText = "$" + mockCost;
        
        // Final Step: Response
        setActiveStep(3);
    }

    function resetSidebarToPending() {
        agentNameDisplay.innerText = "Processing...";
        flowAgentName.innerText = "Thinking...";
        currentStepTitle.innerText = "Analyzing Query";
        currentStepDesc.innerText = "Routing to appropriate agent...";
        
        traceList.innerHTML = `
            <li class="pending">
                <div class="trace-title">Receiving query</div>
                <div class="trace-desc">Initiating graph execution</div>
            </li>
        `;
        
        // Start Step: User Query
        setActiveStep(0);
        
        // Simulate traversal while waiting for backend
        setTimeout(() => setActiveStep(1), 500); // Agent
        setTimeout(() => setActiveStep(2), 1500); // Processing
    }

    async function handleSend(text) {
        if (!text.trim()) return;
        
        // UI Updates for sending
        appendUserMessage(text);
        chatInput.value = '';
        resetSidebarToPending();

        const startTime = Date.now();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: text })
            });

            if(!response.ok) throw new Error("API Error");
            
            const data = await response.json();
            const durationSecs = (Date.now() - startTime) / 1000;

            let finalAnswer = data.final_answer;
            if(!finalAnswer && data.trace && data.trace.length > 0) {
               // Fallback if final_answer wasn't properly returned by the graph
               finalAnswer = "I've processed your request. (See trace for details)";
            }

            appendAgentMessage(finalAnswer);
            updateRightSidebar(data.trace || [], durationSecs);
            
            // Save to logs
            sessionLogs.push({
                question: text,
                answer: finalAnswer,
                trace: data.trace || [],
                time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'})
            });

        } catch (error) {
            console.error("Error:", error);
            appendAgentMessage("Sorry, there was an error processing your request. Please check the backend connection.");
            
            currentStepTitle.innerText = "Error";
            currentStepDesc.innerText = "Failed to connect to the agent server.";
        }
    }

    // Event Listeners
    sendBtn.addEventListener('click', () => {
        handleSend(chatInput.value);
    });

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSend(chatInput.value);
        }
    });

    suggestionChips.forEach(chip => {
        chip.addEventListener('click', () => {
            handleSend(chip.innerText);
        });
    });

    // View Switching Logic
    let chartsRendered = false;
    
    if(navChat && navLogs) {
        const navDashboard = document.getElementById('nav-dashboard');
        const dashboardView = document.getElementById('dashboard-view');

        navChat.addEventListener('click', (e) => {
            e.preventDefault();
            navChat.classList.add('active');
            navLogs.classList.remove('active');
            navDashboard.classList.remove('active');
            chatView.style.display = 'flex';
            logsView.style.display = 'none';
            dashboardView.style.display = 'none';
        });

        navDashboard.addEventListener('click', (e) => {
            e.preventDefault();
            navDashboard.classList.add('active');
            navChat.classList.remove('active');
            navLogs.classList.remove('active');
            chatView.style.display = 'none';
            logsView.style.display = 'none';
            dashboardView.style.display = 'flex';
            
            if(!chartsRendered) {
                renderDashboardCharts();
                chartsRendered = true;
            }
        });

        navLogs.addEventListener('click', (e) => {
            e.preventDefault();
            navLogs.classList.add('active');
            navChat.classList.remove('active');
            navDashboard.classList.remove('active');
            chatView.style.display = 'none';
            logsView.style.display = 'flex';
            dashboardView.style.display = 'none';
            renderLogs();
        });
    }

    function renderLogs() {
        if(sessionLogs.length === 0) {
            logsContainer.innerHTML = '<div class="empty-logs" id="empty-logs">No logs recorded yet. Start a chat to see traces!</div>';
            return;
        }
        
        logsContainer.innerHTML = '';
        
        // Reverse so newest is at top
        [...sessionLogs].reverse().forEach((log, index) => {
            const card = document.createElement('div');
            card.className = 'log-card';
            
            const traceHtml = log.trace.map(t => `<li>${t}</li>`).join('');
            
            card.innerHTML = `
                <h4>Log Entry #${sessionLogs.length - index} <span class="log-time">${log.time}</span></h4>
                <div class="log-question"><strong>Q:</strong> ${log.question}</div>
                <div class="log-answer"><strong>A:</strong> ${log.answer}</div>
                <div class="log-trace-title">Execution Trace</div>
                <ul class="log-trace-list">
                    ${traceHtml}
                </ul>
            `;
            logsContainer.appendChild(card);
        });
    }

    async function renderDashboardCharts() {
        const trafficCtx = document.getElementById('trafficChart');
        const workloadCtx = document.getElementById('workloadChart');
        if (!trafficCtx || !workloadCtx) return;

        let data = {
            total_queries: 0,
            success_rate: 0,
            workload: { technical: 0, billing: 0, general: 0 },
            traffic: {},
            tool_usage: {},
            tool_accuracy: {}
        };

        try {
            const res = await fetch('/api/metrics');
            if (res.ok) {
                data = await res.json();
            }
        } catch(e) {
            console.error("Failed to fetch metrics", e);
        }

        // Update Success Rate UI
        const successRateEl = document.getElementById('metric-success-rate');
        const successBarEl = document.getElementById('metric-success-bar');
        if (successRateEl && successBarEl) {
            successRateEl.innerText = data.success_rate + '%';
            successBarEl.style.width = data.success_rate + '%';
        }

        // Line Chart for Queries Over Time
        const trafficLabels = Object.keys(data.traffic).length > 0 ? Object.keys(data.traffic) : ['No Data'];
        const trafficValues = Object.keys(data.traffic).length > 0 ? Object.values(data.traffic) : [0];

        new Chart(trafficCtx, {
            type: 'line',
            data: {
                labels: trafficLabels,
                datasets: [{
                    label: 'Total Queries',
                    data: trafficValues,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { borderDash: [2, 4], color: '#e5e7eb' }, ticks: { stepSize: 1 } },
                    x: { grid: { display: false } }
                }
            }
        });

        // Doughnut Chart for Agent Workload
        const workload = data.workload;
        new Chart(workloadCtx, {
            type: 'doughnut',
            data: {
                labels: ['Technical', 'Billing', 'General'],
                datasets: [{
                    data: [workload.technical || 0, workload.billing || 0, workload.general || 0],
                    backgroundColor: ['#8b5cf6', '#3b82f6', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } }
                }
            }
        });

        // Tool Charts
        const toolUsageCtx = document.getElementById('toolUsageChart');
        const toolAccuracyCtx = document.getElementById('toolAccuracyChart');
        
        const toolNames = Object.keys(data.tool_usage || {});
        const toolUsageVals = Object.values(data.tool_usage || {});
        const toolAccuracyVals = toolNames.map(name => data.tool_accuracy[name] || 0);

        if (toolUsageCtx) {
            new Chart(toolUsageCtx, {
                type: 'bar',
                data: {
                    labels: toolNames.length > 0 ? toolNames : ['No Data'],
                    datasets: [{
                        label: 'Uses',
                        data: toolUsageVals.length > 0 ? toolUsageVals : [0],
                        backgroundColor: '#8b5cf6'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }

        if (toolAccuracyCtx) {
            new Chart(toolAccuracyCtx, {
                type: 'bar',
                data: {
                    labels: toolNames.length > 0 ? toolNames : ['No Data'],
                    datasets: [{
                        label: 'Accuracy (%)',
                        data: toolAccuracyVals.length > 0 ? toolAccuracyVals : [0],
                        backgroundColor: '#10b981'
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false, scales: { y: { max: 100, beginAtZero: true } } }
            });
        }
    }
});
