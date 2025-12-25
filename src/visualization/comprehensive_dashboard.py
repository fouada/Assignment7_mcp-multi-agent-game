"""
Comprehensive Real-Time Dashboard - Complete Game League Data
=============================================================

Shows ALL real-time data from game league:
1. Each player's strategy
2. Current round / Total rounds / Remaining rounds
3. Live standings with strategies
4. Each player's move/choice in every match
5. Round-by-round history
6. Winner celebration
7. Match details with scores

This is the complete, comprehensive dashboard the user requested.
"""

COMPREHENSIVE_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MCP Game League - Comprehensive Real-Time Dashboard</title>
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

        .container {
            max-width: 1900px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Round Progress Banner */
        .round-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
        .round-stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 15px;
        }
        .round-stat {
            text-align: center;
        }
        .round-stat-label {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: rgba(255,255,255,0.7);
            margin-bottom: 8px;
        }
        .round-stat-value {
            font-size: 32px;
            font-weight: 800;
            color: #fff;
        }
        .round-progress-bar {
            height: 10px;
            background: rgba(255,255,255,0.2);
            border-radius: 5px;
            overflow: hidden;
            margin-top: 15px;
        }
        .round-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981, #22c55e);
            transition: width 0.5s ease;
            border-radius: 5px;
        }
        .round-progress-text {
            text-align: center;
            margin-top: 8px;
            font-size: 14px;
            color: rgba(255,255,255,0.9);
            font-weight: 600;
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

        /* Standings Table */
        .standings-table {
            width: 100%;
            border-collapse: collapse;
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
            justify-content: center;
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

        /* Live Matches */
        .matches-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
        }
        .match-card {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            border-radius: 12px;
            padding: 25px;
            border: 2px solid #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
        }
        .match-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(255,255,255,0.1);
        }
        .match-id {
            font-weight: 700;
            color: #667eea;
            font-size: 18px;
        }
        .round-badge {
            background: rgba(102, 126, 234, 0.3);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            color: #fff;
            font-weight: 600;
        }
        .player-match-slot {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
        }
        .player-match-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .player-match-name {
            font-weight: 600;
            font-size: 18px;
            flex: 1;
        }
        .move-display {
            font-size: 48px;
            font-weight: 900;
            color: #667eea;
            background: rgba(102, 126, 234, 0.2);
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 3px solid #667eea;
        }
        .move-pending {
            color: #a0aec0;
            font-size: 24px;
        }
        .vs-divider {
            text-align: center;
            font-weight: bold;
            color: #667eea;
            font-size: 24px;
            padding: 15px 0;
        }
        .match-score {
            display: flex;
            justify-content: space-around;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid rgba(255,255,255,0.1);
        }
        .score-item {
            text-align: center;
        }
        .score-label {
            font-size: 12px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 5px;
        }
        .score-value {
            font-size: 28px;
            font-weight: 700;
            color: #10b981;
        }

        /* Match History */
        .history-list {
            max-height: 600px;
            overflow-y: auto;
        }
        .history-item {
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 12px;
            border-left: 4px solid #667eea;
        }
        .history-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }
        .history-round {
            font-weight: 600;
            color: #667eea;
            font-size: 15px;
        }
        .history-time {
            font-size: 12px;
            color: #a0aec0;
        }
        .history-players {
            display: grid;
            grid-template-columns: 1fr auto 1fr;
            gap: 15px;
            align-items: center;
        }
        .history-player {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .history-player-name {
            font-weight: 600;
            margin-bottom: 4px;
        }
        .history-player-move {
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
        }
        .history-result {
            text-align: center;
            padding: 8px;
            border-radius: 8px;
            font-weight: 600;
        }
        .result-win {
            background: rgba(16, 185, 129, 0.2);
            color: #10b981;
        }
        .result-loss {
            background: rgba(239, 68, 68, 0.2);
            color: #ef4444;
        }

        /* Winner Modal */
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
        .winner-modal.hidden { display: none; }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .winner-content {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            padding: 60px 50px;
            border-radius: 24px;
            text-align: center;
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
        }
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-30px); }
        }
        .winner-title {
            color: #ffd700;
            font-size: 52px;
            margin: 20px 0;
            font-weight: 800;
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
        .winner-strategy-name {
            font-size: 28px;
            color: #ffd700;
            font-weight: 700;
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
        }
        .winner-stat-box .stat-label {
            font-size: 13px;
            color: #a0aec0;
            text-transform: uppercase;
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
        }
        .close-winner-btn:hover {
            transform: scale(1.1);
        }

        /* Controls */
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
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
        }
        button:hover {
            background: #5568d3;
        }

        /* Grid */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>
            🎮 MCP Game League - Comprehensive Dashboard
            <span id="status" class="connection-status disconnected">Disconnected</span>
        </h1>
    </div>

    <div class="container">
        <div class="controls">
            <button onclick="connectWebSocket()">🔌 Connect</button>
            <button onclick="location.reload()">🔄 Refresh</button>
            <button onclick="exportData()">💾 Export Data</button>
        </div>

        <!-- Round Progress Banner -->
        <div class="round-banner">
            <div class="round-stats">
                <div class="round-stat">
                    <div class="round-stat-label">Current Round</div>
                    <div class="round-stat-value" id="current-round">0</div>
                </div>
                <div class="round-stat">
                    <div class="round-stat-label">Total Rounds</div>
                    <div class="round-stat-value" id="total-rounds">0</div>
                </div>
                <div class="round-stat">
                    <div class="round-stat-label">Rounds Played</div>
                    <div class="round-stat-value" id="rounds-played">0</div>
                </div>
                <div class="round-stat">
                    <div class="round-stat-label">Rounds Remaining</div>
                    <div class="round-stat-value" id="rounds-remaining">0</div>
                </div>
            </div>
            <div class="round-progress-bar">
                <div class="round-progress-fill" id="round-progress-fill" style="width: 0%"></div>
            </div>
            <div class="round-progress-text" id="round-progress-text">Ready to start...</div>
        </div>

        <!-- Standings Table -->
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

        <!-- Live Matches -->
        <div class="card">
            <h2>🎮 Live Matches - Player Moves in Real-Time</h2>
            <div id="active-matches" class="matches-grid">
                <p style="color: #a0aec0; text-align: center; padding: 40px;">No active matches</p>
            </div>
        </div>

        <!-- Match History -->
        <div class="card">
            <h2>📊 Match History - All Moves & Results</h2>
            <div id="match-history" class="history-list">
                <p style="color: #a0aec0; text-align: center; padding: 40px;">No matches played yet</p>
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
                <div style="font-size: 14px; color: #a0aec0; margin-bottom: 8px;">Winning Strategy</div>
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
            currentRound: 0,
            totalRounds: 0,
            standings: [],
            activeMatches: [],
            matchHistory: []
        };

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            ws = new WebSocket(`${protocol}//${host}/ws`);

            ws.onopen = () => {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'connection-status connected';
                console.log('Connected to dashboard');
            };

            ws.onclose = () => {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'connection-status disconnected';
            };

            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                handleMessage(message);
            };
        }

        function handleMessage(message) {
            switch (message.type) {
                case 'tournament_update':
                    handleTournamentUpdate(message.data);
                    break;
                case 'match_update':
                    handleMatchUpdate(message.data);
                    break;
                case 'tournament_complete':
                    handleTournamentComplete(message.data);
                    break;
            }
        }

        function handleTournamentUpdate(data) {
            tournamentData.currentRound = data.current_round || 0;
            tournamentData.totalRounds = data.total_rounds || 0;
            tournamentData.standings = data.standings || [];

            updateRoundProgress();
            updateStandingsTable();
        }

        function updateRoundProgress() {
            const current = tournamentData.currentRound;
            const total = tournamentData.totalRounds;
            const remaining = Math.max(0, total - current);
            const percentage = total > 0 ? (current / total * 100) : 0;

            document.getElementById('current-round').textContent = current;
            document.getElementById('total-rounds').textContent = total;
            document.getElementById('rounds-played').textContent = current;
            document.getElementById('rounds-remaining').textContent = remaining;
            document.getElementById('round-progress-fill').style.width = percentage + '%';
            document.getElementById('round-progress-text').textContent =
                `${percentage.toFixed(1)}% Complete - Round ${current} of ${total}`;
        }

        function updateStandingsTable() {
            const tbody = document.getElementById('standings-tbody');
            const standings = tournamentData.standings;

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

                const playerId = player.player_id || player.player || `Player ${rank}`;
                const strategy = player.strategy || 'Unknown';
                const score = (player.score || player.total_score || 0).toFixed(1);
                const wins = player.wins || player.total_wins || 0;
                const matches = player.total_matches || player.matches_played || 0;
                const winRate = matches > 0 ? ((wins / matches) * 100).toFixed(1) : '0.0';

                return `
                    <tr>
                        <td><div class="rank-badge ${rankClass}">${rank}</div></td>
                        <td>
                            <div class="player-cell">
                                <div class="player-avatar">${playerId.substring(0, 2)}</div>
                                <div class="player-details">
                                    <div class="player-name">${playerId}</div>
                                    <span class="strategy-badge">${strategy}</span>
                                </div>
                            </div>
                        </td>
                        <td class="score-cell">${score}</td>
                        <td class="wins-cell">${wins}</td>
                        <td>${matches}</td>
                        <td>${winRate}%</td>
                    </tr>
                `;
            }).join('');
        }

        function handleMatchUpdate(data) {
            // Handle both single match and array of matches
            const matches = Array.isArray(data) ? data : [data];
            tournamentData.activeMatches = matches;

            updateLiveMatches(matches);

            // Add completed matches to history
            matches.forEach(match => {
                if (match.state === 'COMPLETE') {
                    addToMatchHistory(match);
                }
            });
        }

        function updateLiveMatches(matches) {
            const container = document.getElementById('active-matches');

            if (!matches || matches.length === 0 || !matches[0].match_id) {
                container.innerHTML = '<p style="color: #a0aec0; text-align: center; padding: 40px;">No active matches</p>';
                return;
            }

            container.innerHTML = matches.map(match => {
                const player_a = match.player_a || {};
                const player_b = match.player_b || {};

                return `
                    <div class="match-card">
                        <div class="match-header">
                            <span class="match-id">${match.match_id || 'Match'}</span>
                            <span class="round-badge">Round ${match.round || 0}/${match.total_rounds || 0}</span>
                        </div>

                        <div class="player-match-slot">
                            <div class="player-match-header">
                                <div class="player-avatar">${(player_a.id || 'P1').substring(0,2)}</div>
                                <div class="player-match-name">${player_a.name || player_a.id || 'Player 1'}</div>
                                <span class="strategy-badge">${player_a.strategy || 'Unknown'}</span>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 12px; color: #a0aec0; margin-bottom: 8px;">MOVE</div>
                                <div class="move-display ${player_a.move ? '' : 'move-pending'}">
                                    ${player_a.move || '?'}
                                </div>
                            </div>
                        </div>

                        <div class="vs-divider">VS</div>

                        <div class="player-match-slot">
                            <div class="player-match-header">
                                <div class="player-avatar">${(player_b.id || 'P2').substring(0,2)}</div>
                                <div class="player-match-name">${player_b.name || player_b.id || 'Player 2'}</div>
                                <span class="strategy-badge">${player_b.strategy || 'Unknown'}</span>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 12px; color: #a0aec0; margin-bottom: 8px;">MOVE</div>
                                <div class="move-display ${player_b.move ? '' : 'move-pending'}">
                                    ${player_b.move || '?'}
                                </div>
                            </div>
                        </div>

                        <div class="match-score">
                            <div class="score-item">
                                <div class="score-label">${player_a.name || 'P1'} Score</div>
                                <div class="score-value">${player_a.score || 0}</div>
                            </div>
                            <div class="score-item">
                                <div class="score-label">${player_b.name || 'P2'} Score</div>
                                <div class="score-value">${player_b.score || 0}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function addToMatchHistory(match) {
            // Check if already in history
            if (tournamentData.matchHistory.some(m => m.match_id === match.match_id && m.round === match.round)) {
                return;
            }

            tournamentData.matchHistory.unshift(match);
            updateMatchHistory();
        }

        function updateMatchHistory() {
            const container = document.getElementById('match-history');
            const history = tournamentData.matchHistory;

            if (!history || history.length === 0) {
                container.innerHTML = '<p style="color: #a0aec0; text-align: center; padding: 40px;">No matches played yet</p>';
                return;
            }

            container.innerHTML = history.map(match => {
                const player_a = match.player_a || {};
                const player_b = match.player_b || {};
                const winner = match.winner || player_a.id;

                return `
                    <div class="history-item">
                        <div class="history-header">
                            <span class="history-round">Round ${match.round || 0} - ${match.match_id || 'Match'}</span>
                            <span class="history-time">${new Date().toLocaleTimeString()}</span>
                        </div>
                        <div class="history-players">
                            <div class="history-player">
                                <div class="player-avatar">${(player_a.id || 'P1').substring(0,2)}</div>
                                <div>
                                    <div class="history-player-name">${player_a.name || player_a.id || 'Player 1'}</div>
                                    <span class="strategy-badge">${player_a.strategy || 'Unknown'}</span>
                                    <div class="history-player-move">Move: ${player_a.move || '?'}</div>
                                </div>
                            </div>
                            <div class="history-result ${winner === player_a.id ? 'result-win' : 'result-loss'}">
                                ${winner === player_a.id ? 'WIN' : 'LOSS'}
                            </div>
                            <div class="history-player">
                                <div>
                                    <div class="history-player-name">${player_b.name || player_b.id || 'Player 2'}</div>
                                    <span class="strategy-badge">${player_b.strategy || 'Unknown'}</span>
                                    <div class="history-player-move">Move: ${player_b.move || '?'}</div>
                                </div>
                                <div class="player-avatar">${(player_b.id || 'P2').substring(0,2)}</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
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

        function exportData() {
            const dataStr = JSON.stringify(tournamentData, null, 2);
            const dataBlob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(dataBlob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `tournament_data_${Date.now()}.json`;
            link.click();
        }

        // Auto-connect on load
        window.onload = () => {
            connectWebSocket();
        };
    </script>
</body>
</html>
"""
