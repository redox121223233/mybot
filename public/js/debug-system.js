// Advanced Debug System for Sticker Creator
class DebugSystem {
    constructor() {
        this.logs = [];
        this.userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id || 'unknown';
        this.sessionId = Date.now();
        this.init();
    }

    init() {
        // Override console methods to capture logs
        const originalConsole = {
            log: console.log,
            error: console.error,
            warn: console.warn,
            info: console.info
        };

        console.log = (...args) => {
            originalConsole.log(...args);
            this.sendLog('info', args.join(' '));
        };

        console.error = (...args) => {
            originalConsole.error(...args);
            this.sendLog('error', args.join(' '));
        };

        console.warn = (...args) => {
            originalConsole.warn(...args);
            this.sendLog('warn', args.join(' '));
        };

        console.info = (...args) => {
            originalConsole.info(...args);
            this.sendLog('info', args.join(' '));
        };

        // Log page load
        this.sendLog('info', 'Page loaded successfully');
        
        // Log user info
        this.sendLog('info', `User ID: ${this.userId}, Session: ${this.sessionId}`);

        // Add window error handler
        window.addEventListener('error', (event) => {
            this.sendLog('error', `Window Error: ${event.message} at ${event.filename}:${event.lineno}`);
        });

        // Add unhandled promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            this.sendLog('error', `Unhandled Promise Rejection: ${event.reason}`);
        });
    }

    sendLog(level, message) {
        const logEntry = {
            timestamp: new Date().toISOString(),
            level: level.toUpperCase(),
            message: message,
            userId: this.userId,
            sessionId: this.sessionId,
            url: window.location.href,
            userAgent: navigator.userAgent
        };

        this.logs.push(logEntry);

        // Send to server
        fetch('/api/log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(logEntry)
        }).catch(err => {
            // If logging fails, try to log locally
            originalConsole.error('Failed to send log:', err);
        });

        // Also show in debug panel if exists
        this.updateDebugPanel(logEntry);
    }

    updateDebugPanel(logEntry) {
        const debugPanel = document.getElementById('debugPanel');
        if (debugPanel) {
            const logLine = document.createElement('div');
            logLine.className = `debug-log debug-${logEntry.level.toLowerCase()}`;
            logLine.innerHTML = `<span class="debug-time">${logEntry.timestamp.split('T')[1].split('.')[0]}</span> [${logEntry.level}] ${logEntry.message}`;
            debugPanel.appendChild(logLine);
            debugPanel.scrollTop = debugPanel.scrollHeight;

            // Keep only last 50 logs in panel
            while (debugPanel.children.length > 50) {
                debugPanel.removeChild(debugPanel.firstChild);
            }
        }
    }

    // Special method for tracking specific actions
    trackAction(action, data = {}) {
        this.sendLog('info', `ACTION: ${action} - ${JSON.stringify(data)}`);
    }

    // Special method for tracking errors with context
    trackError(error, context = {}) {
        const errorData = {
            message: error.message || error,
            stack: error.stack || 'No stack trace',
            context: context
        };
        this.sendLog('error', `ERROR: ${JSON.stringify(errorData)}`);
    }

    // Get all logs for debugging
    getLogs() {
        return this.logs;
    }

    // Clear logs
    clearLogs() {
        this.logs = [];
    }
}

// Initialize debug system
window.debugSystem = new DebugSystem();

// Global error tracking function
window.trackError = (error, context) => {
    window.debugSystem.trackError(error, context);
};

// Global action tracking function  
window.trackAction = (action, data) => {
    window.debugSystem.trackAction(action, data);
};