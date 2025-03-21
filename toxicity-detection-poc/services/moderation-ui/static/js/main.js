// Configuration
const REFRESH_INTERVAL = 2000; // 2 seconds
const INACTIVE_THRESHOLD = 30; // 30 seconds

// State variables
let currentMessageId = null;
let refreshTimer = null;
let lastPolledTime = Date.now();
let lastHistoryUpdate = 0;

// DOM Ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the app
    initApp();
    
    // Set up event listeners
    setupEventListeners();
    
    // Start auto-refresh timer
    startRefreshTimer();
});

// Initialize the application
function initApp() {
    // Initial data loading
    updateSystemStatus();
    loadCurrentMessage();
    loadModerationHistory();
    
    // Show moderation tab by default
    showModerationTab();
}

// Setup event listeners for buttons and tabs
function setupEventListeners() {
    // Tab navigation
    document.getElementById('moderation-tab-btn').addEventListener('click', showModerationTab);
    document.getElementById('stats-tab-btn').addEventListener('click', showStatsTab);
    
    // Action buttons in sidebar
    document.getElementById('restart-consumer-btn').addEventListener('click', restartConsumer);
    document.getElementById('load-messages-btn').addEventListener('click', loadMessagesFromKafka);
    document.getElementById('add-test-message-btn').addEventListener('click', addTestMessage);
    document.getElementById('clear-queue-btn').addEventListener('click', clearMessageQueue);
    
    // No messages view
    document.getElementById('search-messages-btn').addEventListener('click', loadMessagesFromKafka);
    
    // Moderation decision buttons
    document.getElementById('approve-btn').addEventListener('click', () => submitDecision('OK'));
    document.getElementById('block-btn').addEventListener('click', () => submitDecision('TOXIC'));
    document.getElementById('skip-btn').addEventListener('click', () => submitDecision('SKIP'));
}

// Start auto-refresh timer
function startRefreshTimer() {
    if (refreshTimer) {
        clearInterval(refreshTimer);
    }
    
    refreshTimer = setInterval(() => {
        updateSystemStatus();
        
        // Only reload message if we're in the moderation tab
        if (document.getElementById('moderation-tab').classList.contains('d-none') === false) {
            loadCurrentMessage();
        }
        
        // Update history less frequently to reduce load
        const now = Date.now();
        if (now - lastHistoryUpdate > 10000) { // 10 seconds
            loadModerationHistory();
            lastHistoryUpdate = now;
        }
    }, REFRESH_INTERVAL);
}

// Show the moderation tab
function showModerationTab() {
    document.getElementById('moderation-tab').classList.remove('d-none');
    document.getElementById('stats-tab').classList.add('d-none');
    
    document.getElementById('moderation-tab-btn').classList.add('active');
    document.getElementById('stats-tab-btn').classList.remove('active');
    
    loadCurrentMessage(); // Refresh immediately when switching to this tab
}

// Show the statistics tab
function showStatsTab() {
    document.getElementById('stats-tab').classList.remove('d-none');
    document.getElementById('moderation-tab').classList.add('d-none');
    
    document.getElementById('stats-tab-btn').classList.add('active');
    document.getElementById('moderation-tab-btn').classList.remove('active');
    
    loadModerationHistory(); // Refresh immediately when switching to this tab
}

// Update system status information
async function updateSystemStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Update Kafka connection info
        document.getElementById('kafka-server').textContent = data.kafka_server;
        document.getElementById('input-topic').textContent = data.input_topic;
        document.getElementById('output-topic').textContent = data.output_topic;
        
        // Update debug info
        document.getElementById('queue-size').textContent = data.queue_size;
        document.getElementById('inactive-seconds').textContent = Math.floor(data.inactive_seconds);
        
        const lastActivityDate = new Date(data.last_activity * 1000);
        document.getElementById('last-activity').textContent = lastActivityDate.toLocaleTimeString();
        
        // Update consumer status
        const consumerStatusElement = document.getElementById('consumer-status');
        const consumerStatusMainElement = document.getElementById('consumer-status-main');
        const consumerAlertElement = document.getElementById('consumer-alert');
        
        // Determine status text and class
        let statusText = data.consumer_running ? 'Actif' : 'Inactif';
        let statusClass = data.consumer_running ? 'status-active' : 'status-inactive';
        let alertClass = data.consumer_running ? 'alert-success' : 'alert-danger';
        
        // Check if active but no recent activity
        if (data.consumer_running && data.inactive_seconds > INACTIVE_THRESHOLD) {
            statusText = `Actif (Inactif depuis ${Math.floor(data.inactive_seconds)}s)`;
            statusClass = 'status-warning';
            alertClass = 'alert-warning';
        }
        
        consumerStatusElement.textContent = statusText;
        consumerStatusElement.className = statusClass;
        
        consumerStatusMainElement.textContent = statusText;
        consumerStatusMainElement.className = statusClass;
        
        // Update alert class
        consumerAlertElement.className = 'alert ' + alertClass;
        
        // Update lastPolledTime
        lastPolledTime = Date.now();
        
    } catch (error) {
        console.error('Error updating system status:', error);
    }
}

// Load current message to moderate
async function loadCurrentMessage() {
    try {
        const response = await fetch('/api/messages/current');
        const data = await response.json();
        
        const messageView = document.getElementById('message-view');
        const noMessagesView = document.getElementById('no-messages-view');
        
        if (data.status === 'empty') {
            // No messages to moderate
            messageView.classList.add('d-none');
            noMessagesView.classList.remove('d-none');
            currentMessageId = null;
            return;
        }
        
        // We have a message to display
        messageView.classList.remove('d-none');
        noMessagesView.classList.add('d-none');
        
        const message = data.message;
        
        // Only update the UI if this is a different message than we're currently displaying
        if (currentMessageId !== message.message_id) {
            currentMessageId = message.message_id;
            
            // Update queue count
            document.getElementById('queue-count').textContent = document.getElementById('queue-size').textContent;
            
            // Basic info
            document.getElementById('message-id').textContent = message.message_id || '-';
            document.getElementById('sender-id').textContent = message.sender_id || '-';
            document.getElementById('game-id').textContent = message.game_id || '-';
            document.getElementById('channel-id').textContent = message.channel_id || '-';
            
            // Friends info
            const isFriends = message.is_friends || {};
            const friendsCount = Object.values(isFriends).filter(Boolean).length;
            const totalRecipients = Object.keys(isFriends).length;
            document.getElementById('friends-info').textContent = totalRecipients > 0 
                ? `${friendsCount}/${totalRecipients} destinataires` 
                : 'Aucune info d\'amitié';
            
            // Classification
            const classification = message.classification || {};
            if (classification.toxicity_score !== undefined) {
                const score = classification.toxicity_score;
                const uncertainty = classification.uncertainty || 0;
                
                document.getElementById('classification-score').textContent = score.toFixed(2);
                document.getElementById('classification-uncertainty').textContent = uncertainty.toFixed(2);
                document.getElementById('classification-score-bar').style.width = `${score * 100}%`;
            } else {
                document.getElementById('classification-score').textContent = '-';
                document.getElementById('classification-uncertainty').textContent = '-';
                document.getElementById('classification-score-bar').style.width = '0%';
            }
            
            // Deep analysis
            const deepAnalysis = message.deep_analysis || {};
            if (deepAnalysis.toxicity_score !== undefined) {
                const score = deepAnalysis.toxicity_score;
                const uncertainty = deepAnalysis.uncertainty || 0;
                
                document.getElementById('deep-analysis-score').textContent = score.toFixed(2);
                document.getElementById('deep-analysis-uncertainty').textContent = uncertainty.toFixed(2);
                document.getElementById('deep-analysis-score-bar').style.width = `${score * 100}%`;
            } else {
                document.getElementById('deep-analysis-score').textContent = '-';
                document.getElementById('deep-analysis-uncertainty').textContent = '-';
                document.getElementById('deep-analysis-score-bar').style.width = '0%';
            }
            
            // Message content
            document.getElementById('message-content').value = message.content || '';
            
            // Metadata
            const metadata = message.metadata || {};
            document.getElementById('metadata-json').textContent = JSON.stringify(metadata, null, 2);
            
            // Reset reason input
            document.getElementById('reason-input').value = '';
        }
        
    } catch (error) {
        console.error('Error loading current message:', error);
        showNotification('Erreur', 'Impossible de charger le message actuel.', 'error');
    }
}

// Load moderation history
async function loadModerationHistory() {
    try {
        const response = await fetch('/api/history');
        const data = await response.json();
        
        if (data.status !== 'success') {
            console.error('Error loading history:', data.message);
            return;
        }
        
        const history = data.history || [];
        
        const statsView = document.getElementById('stats-view');
        const noStatsView = document.getElementById('no-stats-view');
        
        if (history.length === 0) {
            // No history data
            statsView.classList.add('d-none');
            noStatsView.classList.remove('d-none');
            return;
        }
        
        // We have history data to display
        statsView.classList.remove('d-none');
        noStatsView.classList.add('d-none');
        
        // Update metrics
        const totalDecisions = history.length;
        const toxicCount = history.filter(item => item.decision === 'TOXIC').length;
        const okCount = history.filter(item => item.decision === 'OK').length;
        
        document.getElementById('total-decisions').textContent = totalDecisions;
        document.getElementById('toxic-count').textContent = toxicCount;
        document.getElementById('ok-count').textContent = okCount;
        
        // Update table with most recent decisions
        const tbody = document.getElementById('decisions-tbody');
        tbody.innerHTML = ''; // Clear existing rows
        
        // Show most recent 10 decisions
        const recentDecisions = [...history].reverse().slice(0, 10);
        
        recentDecisions.forEach(decision => {
            const row = document.createElement('tr');
            
            // Format timestamp
            let timestamp = decision.timestamp;
            if (typeof timestamp === 'string') {
                timestamp = new Date(timestamp);
            } else {
                timestamp = new Date();
            }
            
            // Create cells
            const timeCell = document.createElement('td');
            timeCell.textContent = timestamp.toLocaleString();
            
            const idCell = document.createElement('td');
            idCell.textContent = decision.message_id;
            
            const decisionCell = document.createElement('td');
            const decisionBadge = document.createElement('span');
            decisionBadge.classList.add('badge');
            
            if (decision.decision === 'TOXIC') {
                decisionBadge.classList.add('bg-danger');
                decisionBadge.textContent = 'TOXIC';
            } else {
                decisionBadge.classList.add('bg-success');
                decisionBadge.textContent = 'OK';
            }
            
            decisionCell.appendChild(decisionBadge);
            
            const reasonCell = document.createElement('td');
            reasonCell.textContent = decision.reason || '-';
            
            // Add cells to row
            row.appendChild(timeCell);
            row.appendChild(idCell);
            row.appendChild(decisionCell);
            row.appendChild(reasonCell);
            
            // Add row to table
            tbody.appendChild(row);
        });
        
    } catch (error) {
        console.error('Error loading moderation history:', error);
    }
}

// Submit a moderation decision
// Submit a moderation decision
async function submitDecision(decision) {
    // If no message is currently loaded, do nothing
    if (!currentMessageId) {
        showNotification('Erreur', 'Aucun message à modérer.', 'error');
        return;
    }
    
    // Get reason from input
    const reason = document.getElementById('reason-input').value.trim();
    
    // Verify reason is provided for toxic messages
    if (decision === 'TOXIC' && !reason) {
        showNotification('Erreur', 'Une raison est obligatoire pour bloquer un message.', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/decision', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                decision: decision,
                reason: reason
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Show success notification
            let actionText = '';
            if (decision === 'OK') actionText = 'autorisé';
            else if (decision === 'TOXIC') actionText = 'bloqué';
            else actionText = 'ignoré';
            
            showNotification('Succès', `Message ${actionText} avec succès.`, 'success');
            
            // Forcer l'actualisation de la liste des messages
            currentMessageId = null;
            
            // Attendre un court instant avant de recharger
            setTimeout(() => {
                // Forcer le rechargement de tous les éléments nécessaires
                loadCurrentMessage();
                updateSystemStatus();
                
                // Mise à jour de l'historique si une décision a été prise
                if (decision !== 'SKIP') {
                    loadModerationHistory();
                    lastHistoryUpdate = Date.now();
                }
            }, 500);
        } else {
            showNotification('Erreur', data.message || 'Erreur lors du traitement de la décision.', 'error');
        }
    } catch (error) {
        console.error('Error submitting decision:', error);
        showNotification('Erreur', 'Erreur de communication avec le serveur.', 'error');
    }
}

// Restart Kafka consumer
async function restartConsumer() {
    try {
        const response = await fetch('/api/actions/restart-consumer', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('Succès', 'Consumer Kafka redémarré.', 'success');
            
            // Force UI refresh
            currentMessageId = null;
            setTimeout(() => {
                updateSystemStatus();
                loadCurrentMessage();
            }, 1000);
        } else {
            showNotification('Erreur', data.message || 'Impossible de redémarrer le consumer.', 'error');
        }
    } catch (error) {
        console.error('Error restarting consumer:', error);
        showNotification('Erreur', 'Erreur de communication avec le serveur.', 'error');
    }
}

// Load messages directly from Kafka
async function loadMessagesFromKafka() {
    try {
        showNotification('Information', 'Chargement des messages depuis Kafka...', 'info');
        
        const response = await fetch('/api/actions/load-messages', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('Succès', data.message, 'success');
            
            // Force UI refresh
            currentMessageId = null;
            loadCurrentMessage();
        } else {
            showNotification(data.status === 'warning' ? 'Avertissement' : 'Erreur', data.message, data.status);
        }
    } catch (error) {
        console.error('Error loading messages from Kafka:', error);
        showNotification('Erreur', 'Erreur de communication avec le serveur.', 'error');
    }
}

// Add a test message
async function addTestMessage() {
    try {
        const response = await fetch('/api/actions/add-test-message', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('Succès', 'Message de test ajouté.', 'success');
            
            // Force UI refresh
            currentMessageId = null;
            loadCurrentMessage();
        } else {
            showNotification('Erreur', data.message || 'Impossible d\'ajouter le message de test.', 'error');
        }
    } catch (error) {
        console.error('Error adding test message:', error);
        showNotification('Erreur', 'Erreur de communication avec le serveur.', 'error');
    }
}

// Clear message queue
async function clearMessageQueue() {
    try {
        const response = await fetch('/api/actions/clear-queue', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            showNotification('Succès', 'File d\'attente vidée.', 'success');
            
            // Force UI refresh
            currentMessageId = null;
            loadCurrentMessage();
        } else {
            showNotification('Erreur', data.message || 'Impossible de vider la file d\'attente.', 'error');
        }
    } catch (error) {
        console.error('Error clearing queue:', error);
        showNotification('Erreur', 'Erreur de communication avec le serveur.', 'error');
    }
}

// Show a notification toast
function showNotification(title, message, type = 'info') {
    const toast = document.getElementById('notification-toast');
    const toastTitle = document.getElementById('toast-title');
    const toastMessage = document.getElementById('toast-message');
    
    // Set content
    toastTitle.textContent = title;
    toastMessage.textContent = message;
    
    // Set toast color based on type
    toast.className = 'toast';
    switch (type) {
        case 'success':
            toast.classList.add('text-white', 'bg-success');
            break;
        case 'error':
            toast.classList.add('text-white', 'bg-danger');
            break;
        case 'warning':
            toast.classList.add('text-dark', 'bg-warning');
            break;
        case 'info':
        default:
            toast.classList.add('text-white', 'bg-info');
            break;
    }
    
    // Show the toast
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}