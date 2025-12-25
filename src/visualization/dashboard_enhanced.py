"""
Enhanced Dashboard with Player Strategies, Rounds, Standings, and Winner Display
================================================================================

This enhanced version prominently displays:
1. Each player's strategy (visible in all views)
2. Round-by-round progress
3. Detailed standings table with strategies
4. Winner celebration with strategy breakdown

To use: Replace the HTML in dashboard.py or import from here.
"""

ENHANCED_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Game League - Enhanced Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0e27;
            color: #e0e0e0;
            overflow-x: hidden;
        }

        /* Header */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .header h1 {
            color: white;
            font-size: 28px;
            font-weight: 600;
        }
        .connection-status {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            margin-left: 20px;
        }
        .connected { background: #10b981; color: white; }
        .disconnected { background: #ef4444; color: white; }

        /* Main Container */
        .container {
            max-width: 1800px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Card Styles */
        .card {
            background: #1a1f3a;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            border: 1px solid #2a2f4a;
            margin-bottom: 20px;
        }
        .card h2 {
            font-size: 22px;
            margin-bottom: 20px;
            color: #667eea;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* Enhanced Standings Table */
        .standings-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .standings-table thead {
            background: rgba(102, 126, 234, 0.2);
        }
        .standings-table th {
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #667eea;
            border-bottom: 2px solid #667eea;
        }
        .standings-table td {
            padding: 15px;
            border-bottom: 1px solid #2a2f4a;
        }
        .standings-table tr:hover {
            background: rgba(102, 126, 234, 0.1);
        }
        .rank-badge {
            display: inline-flex;
            align-items: center;
            justify-center;
            width: 35px;
            height: 35px;
            border-radius: 50%;
            font-weight: bold;
            font-size: 16px;
        }
        .rank-1 {
            background: linear-gradient(135deg, #ffd700, #ffed4e);
            color: #000;
        }
        .rank-2 {
            background: linear-gradient(135deg, #c0c0c0, #e8e8e8);
            color: #000;
        }
        .rank-3 {
            background: linear-gradient(135deg, #cd7f32, #e89547);
            color: #fff;
        }
        .rank-other {
            background: rgba(255,255,255,0.1);
            color: #a0aec0;
        }
        .player-cell {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .player-avatar {
            width: 45px;
            height: 45px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 16px;
        }
        .player-details {
            flex: 1;
        }
        .player-name {
            font-weight: 600;
            font-size: 16px;
            margin-bottom: 4px;
        }
        .strategy-badge {
            font-size: 11px;
            color: #fff;
            background: linear-gradient(135deg, #667eea, #764ba2);
            padding: 3px 10px;
            border-radius: 12px;
            display: inline-block;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .score-cell {
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }
        .wins-cell {
            color: #10b981;
            font-weight: 600;
        }
        .winrate-cell {
            font-weight: 600;
        }

        /* Round Progress */
        .round-progress {
            margin: 20px 0;
        }
        .round-indicator {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .round-text {
            font-size: 18px;
            font-weight: 600;
            color: #667eea;
        }
        .round-bar {
            height: 12px;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
            overflow: hidden;
            position: relative;
        }
        .round-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.5s ease;
            border-radius: 6px;
        }

        /* Winner Modal Enhancement */
        .winner-modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            animation: fadeIn 0.5s ease;
        }
        .winner-modal.hidden {
            display: none;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .winner-content {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            padding: 60px 50px;
            border-radius: 24px;
            text-align: center;
            position: relative;
            max-width: 700px;
            border: 4px solid #ffd700;
            box-shadow: 0 0 60px rgba(255, 215, 0, 0.6);
            animation: scaleIn 0.7s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        @keyframes scaleIn {
            from { transform: scale(0.3) rotate(-10deg); opacity: 0; }
            to { transform: scale(1) rotate(0deg); opacity: 1; }
        }
        .winner-trophy {
            font-size: 100px;
            animation: bounce 1.5s ease infinite;
            text-shadow: 0 0 30px rgba(255, 215, 0, 0.8);
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-30px); }
        }
        .winner-title {
            color: #ffd700;
            font-size: 52px;
            margin: 20px 0;
            text-shadow: 0 0 30px rgba(255, 215, 0, 0.8);
            animation: glow 2s ease-in-out infinite;
            font-weight: 800;
        }
        @keyframes glow {
            0%, 100% { text-shadow: 0 0 20px rgba(255, 215, 0, 0.5); }
            50% { text-shadow: 0 0 50px rgba(255, 215, 0, 1); }
        }
        .winner-name {
            font-size: 42px;
            color: #fff;
            margin: 25px 0;
            font-weight: 700;
        }
        .winner-strategy-box {
            background: rgba(255, 215, 0, 0.15);
            border: 2px solid rgba(255, 215, 0, 0.4);
            border-radius: 16px;
            padding: 20px 30px;
            margin: 25px 0;
        }
        .winner-strategy-label {
            font-size: 14px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 2px;
            margin-bottom: 8px;
        }
        .winner-strategy-name {
            font-size: 28px;
            color: #ffd700;
            font-weight: 700;
            text-transform: uppercase;
        }
        .winner-stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin: 35px 0;
        }
        .winner-stat-box {
            background: rgba(255, 215, 0, 0.1);
            padding: 25px;
            border-radius: 16px;
            border: 2px solid rgba(255, 215, 0, 0.3);
        }
        .winner-stat-box .stat-value {
            font-size: 42px;
            font-weight: 800;
            color: #ffd700;
            margin-bottom: 10px;
        }
        .winner-stat-box .stat-label {
            font-size: 13px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 1.5px;
        }
        .close-winner-btn {
            margin-top: 30px;
            padding: 18px 50px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            border: none;
            border-radius: 30px;
            color: white;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .close-winner-btn:hover {
            transform: scale(1.1);
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.6);
        }

        /* Controls */
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }
        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }

        /* Event Log */
        .event-log {
            max-height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }
        .event {
            padding: 10px;
            margin: 6px 0;
            background: #0f1321;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }
        .timestamp {
            color: #10b981;
            margin-right: 10px;
            font-weight: 600;
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            🎮 MCP Game League - Enhanced Dashboard
            <span id="status" class="connection-status disconnected">Disconnected</span>
        </h1>
    </div>

    <div class="container">
        <div class="controls">
            <button onclick="connectWebSocket()">🔌 Connect</button>
            <button onclick="refreshData()">🔄 Refresh</button>
            <button onclick="exportData()">💾 Export Data</button>
            <button onclick="showWinnerModal()">🏆 Show Winner</button>
        </div>

        <!-- Round Progress -->
        <div class="card">
            <h2>⏱️ Round Progress</h2>
            <div class="round-progress">
                <div class="round-indicator">
                    <span class="round-text" id="round-display">Round 0 / 0</span>
                    <span id="round-percentage" style="color: #a0aec0;">0%</span>
                </div>
                <div class="round-bar">
                    <div class="round-fill" id="round-fill" style="width: 0%"></div>
                </div>
            </div>
        </div>

        <!-- Enhanced Standings Table -->
        <div class="card">
            <h2>🏆 Player Standings & Strategies</h2>
            <table class="standings-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Player & Strategy</th>
                        <th>Score</th>
                        <th>Wins</th>
                        <th>Matches</th>
                        <th>Win Rate</th>
                    </tr>
                </thead>
                <tbody id="standings-tbody">
                    <tr>
                        <td colspan="6" style="text-align: center; color: #a0aec0; padding: 40px;">
                            Waiting for tournament data...
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="grid">
            <!-- Tournament Overview -->
            <div class="card">
                <h2>📊 Tournament Info</h2>
                <div style="display: flex; flex-direction: column; gap: 15px;">
                    <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                        <span style="color: #a0aec0;">Game Type</span>
                        <span style="font-weight: 600; color: #667eea;" id="game-type">-</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                        <span style="color: #a0aec0;">Active Players</span>
                        <span style="font-weight: 600; color: #667eea;" id="active-players">-</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                        <span style="color: #a0aec0;">Total Rounds</span>
                        <span style="font-weight: 600; color: #667eea;" id="total-rounds">-</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px;">
                        <span style="color: #a0aec0;">Matches Played</span>
                        <span style="font-weight: 600; color: #667eea;" id="matches-played">-</span>
                    </div>
                </div>
            </div>

            <!-- Live Event Log -->
            <div class="card">
                <h2>📝 Live Events</h2>
                <div id="event-log" class="event-log"></div>
            </div>
        </div>
    </div>

    <!-- Winner Modal -->
    <div id="winner-modal" class="winner-modal hidden">
        <div class="winner-content">
            <div class="winner-trophy">🏆</div>
            <h1 class="winner-title">Tournament Champion!</h1>
            <h2 class="winner-name" id="winner-name">Champion</h2>

            <div class="winner-strategy-box">
                <div class="winner-strategy-label">Winning Strategy</div>
                <div class="winner-strategy-name" id="winner-strategy">Unknown</div>
            </div>

            <div class="winner-stats-grid">
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-score">0</div>
                    <div class="stat-label">Total Score</div>
                </div>
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-wins">0</div>
                    <div class="stat-label">Wins</div>
                </div>
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-matches">0</div>
                    <div class="stat-label">Matches</div>
                </div>
                <div class="winner-stat-box">
                    <div class="stat-value" id="winner-winrate">0%</div>
                    <div class="stat-label">Win Rate</div>
                </div>
            </div>

            <button class="close-winner-btn" onclick="closeWinnerModal()">Close</button>
        </div>
    </div>

    <script>
        let ws = null;
        let tournamentData = {
            players: [],
            currentRound: 0,
            totalRounds: 0,
            standings: []
        };

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            ws = new WebSocket(`${protocol}//${host}/ws`);

            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'connection-status connected';
                addLog('Connected to dashboard');
            };

            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'connection-status disconnected';
                addLog('Disconnected');
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleMessage(message);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                addLog('Connection error', 'error');
            };
        }

        function handleMessage(message) {
            switch (message.type) {
                case 'tournament_update':
                    handleTournamentUpdate(message.data);
                    break;
                case 'game_event':
                    handleGameEvent(message.data);
                    break;
                case 'tournament_complete':
                    handleTournamentComplete(message.data);
                    break;
            }
        }

        function handleTournamentUpdate(data) {
            tournamentData = data;

            // Update round progress
            const currentRound = data.current_round || 0;
            const totalRounds = data.total_rounds || 1;
            const percentage = (currentRound / totalRounds * 100).toFixed(1);

            document.getElementById('round-display').textContent = `Round ${currentRound} / ${totalRounds}`;
            document.getElementById('round-percentage').textContent = `${percentage}%`;
            document.getElementById('round-fill').style.width = `${percentage}%`;

            // Update tournament info
            document.getElementById('game-type').textContent = data.game_type || 'Odd/Even';
            document.getElementById('active-players').textContent = data.players?.length || 0;
            document.getElementById('total-rounds').textContent = totalRounds;
            document.getElementById('matches-played').textContent = data.matches_played || 0;

            // Update standings table
            updateStandingsTable(data.standings || []);
        }

        function updateStandingsTable(standings) {
            const tbody = document.getElementById('standings-tbody');

            if (!standings || standings.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #a0aec0; padding: 40px;">No data yet</td></tr>';
                return;
            }

            tbody.innerHTML = standings.map((player, index) => {
                const rank = index + 1;
                let rankClass = 'rank-other';
                if (rank === 1) rankClass = 'rank-1';
                else if (rank === 2) rankClass = 'rank-2';
                else if (rank === 3) rankClass = 'rank-3';

                const winRate = player.total_matches > 0
                    ? ((player.wins / player.total_matches) * 100).toFixed(1)
                    : 0;

                return `
                    <tr>
                        <td>
                            <div class="rank-badge ${rankClass}">${rank}</div>
                        </td>
                        <td>
                            <div class="player-cell">
                                <div class="player-avatar">${player.player_id.substring(0, 2)}</div>
                                <div class="player-details">
                                    <div class="player-name">${player.player_id}</div>
                                    <span class="strategy-badge">${player.strategy || 'Unknown'}</span>
                                </div>
                            </div>
                        </td>
                        <td class="score-cell">${player.score.toFixed(1)}</td>
                        <td class="wins-cell">${player.wins}</td>
                        <td>${player.total_matches || 0}</td>
                        <td class="winrate-cell">${winRate}%</td>
                    </tr>
                `;
            }).join('');
        }

        function handleGameEvent(data) {
            addLog(`Round ${data.round}: ${data.event_type}`);
        }

        function handleTournamentComplete(data) {
            const winner = data.winner;
            if (winner) {
                document.getElementById('winner-name').textContent = winner.player_id || 'Champion';
                document.getElementById('winner-strategy').textContent = winner.strategy || 'Unknown';
                document.getElementById('winner-score').textContent = winner.score?.toFixed(1) || '0';
                document.getElementById('winner-wins').textContent = winner.wins || '0';
                document.getElementById('winner-matches').textContent = winner.total_matches || '0';

                const winRate = winner.total_matches > 0
                    ? ((winner.wins / winner.total_matches) * 100).toFixed(1)
                    : 0;
                document.getElementById('winner-winrate').textContent = `${winRate}%`;

                showWinnerModal();
            }
        }

        function showWinnerModal() {
            document.getElementById('winner-modal').classList.remove('hidden');
        }

        function closeWinnerModal() {
            document.getElementById('winner-modal').classList.add('hidden');
        }

        function addLog(message, type = 'info') {
            const log = document.getElementById('event-log');
            const timestamp = new Date().toLocaleTimeString();
            const event = document.createElement('div');
            event.className = 'event';
            event.innerHTML = `<span class="timestamp">${timestamp}</span>${message}`;
            log.insertBefore(event, log.firstChild);

            // Keep only last 50 events
            while (log.children.length > 50) {
                log.removeChild(log.lastChild);
            }
        }

        function refreshData() {
            // Request fresh data from server
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send('refresh');
                addLog('Refreshing data...');
            }
        }

        function exportData() {
            const dataStr = JSON.stringify(tournamentData, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `tournament_data_${Date.now()}.json`;
            link.click();
            addLog('Data exported');
        }

        // Auto-connect on load
        window.onload = () => {
            connectWebSocket();
        };
    </script>
</body>
</html>
"""
