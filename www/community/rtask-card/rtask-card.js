class RTaskCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.longPressTimer = null;
    this.longPressDelay = 800; // 800ms for long press
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error('You need to define an entity');
    }
    this.config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  render() {
    if (!this._hass || !this.config) return;

    const entity = this._hass.states[this.config.entity];
    if (!entity) {
      this.shadowRoot.innerHTML = `
        <ha-card>
          <div class="error">Entity "${this.config.entity}" not found</div>
        </ha-card>
      `;
      return;
    }

    const state = entity.state;
    const attributes = entity.attributes;
    const taskName = attributes.task_name || 'Unknown Task';
    
    // Calculate time remaining/overdue
    const timeInfo = this.getTimeInfo(entity);
    
    // Get status color
    const statusColor = this.getStatusColor(state);
    
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          cursor: pointer;
          transition: box-shadow 0.3s ease;
        }
        ha-card:hover {
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .rtask-container {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px;
          border-radius: 8px;
          border-left: 6px solid var(--divider-color);
          background: var(--card-background-color);
          transition: all 0.3s ease;
        }
        .rtask-info {
          flex: 1;
          position: relative;
          z-index: 2;
        }
        .task-name {
          font-size: 18px;
          font-weight: 600;
          margin-bottom: 6px;
        }
        .task-status {
          font-size: 15px;
          font-weight: 500;
          margin-bottom: 4px;
          padding: 4px 12px;
          border-radius: 16px;
          display: inline-block;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .time-info {
          font-size: 13px;
          color: var(--secondary-text-color);
          font-weight: 400;
        }
        .status-indicator {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          margin-left: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          font-weight: bold;
          color: white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.2);
          position: relative;
          z-index: 2;
        }
        
        /* Status-specific styles */
        .status-never-done .rtask-container { 
          border-left-color: var(--disabled-text-color);
          background: linear-gradient(135deg, var(--card-background-color) 0%, rgba(158, 158, 158, 0.05) 100%);
        }
        .status-never-done .task-status { 
          background-color: var(--disabled-text-color);
          color: white;
        }
        .status-never-done .status-indicator { 
          background-color: var(--disabled-text-color);
        }
        
        .status-done .rtask-container { 
          border-left-color: var(--success-color);
          background: linear-gradient(135deg, var(--card-background-color) 0%, rgba(76, 175, 80, 0.08) 100%);
        }
        .status-done .task-status { 
          background-color: var(--success-color);
          color: white;
        }
        .status-done .status-indicator { 
          background-color: var(--success-color);
        }
        
        .status-due .rtask-container { 
          border-left-color: var(--warning-color);
          background: linear-gradient(135deg, var(--card-background-color) 0%, rgba(255, 193, 7, 0.08) 100%);
        }
        .status-due .task-status { 
          background-color: var(--warning-color);
          color: var(--text-primary-color);
        }
        .status-due .status-indicator { 
          background-color: var(--warning-color);
          color: var(--text-primary-color);
        }
        
        .status-overdue .rtask-container { 
          border-left-color: var(--error-color);
          background: linear-gradient(135deg, var(--card-background-color) 0%, rgba(244, 67, 54, 0.08) 100%);
          animation: pulse-overdue 2s infinite;
        }
        .status-overdue .task-status { 
          background-color: var(--error-color);
          color: white;
        }
        .status-overdue .status-indicator { 
          background-color: var(--error-color);
        }
        
        @keyframes pulse-overdue {
          0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.3); }
          70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
          100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
        }
        
        .long-press-active {
          transform: scale(0.98);
          box-shadow: 0 0 20px rgba(33, 150, 243, 0.4);
          transition: all 0.2s ease;
        }
        
        .long-press-progress {
          position: absolute;
          top: 0;
          left: 0;
          height: 100%;
          background: linear-gradient(90deg, rgba(33, 150, 243, 0.2) 0%, rgba(33, 150, 243, 0.4) 100%);
          border-radius: 8px;
          transform-origin: left;
          transform: scaleX(0);
          transition: transform 0.8s linear;
          z-index: 1;
        }
        
        .long-press-progress.active {
          transform: scaleX(1);
        }
        
        .rtask-container {
          position: relative;
          overflow: hidden;
        }
        .error {
          color: var(--error-color);
          padding: 16px;
        }
      </style>
      
      <ha-card>
        <div class="rtask-container status-${state.toLowerCase().replace(' ', '-')}">
          <div class="long-press-progress"></div>
          <div class="rtask-info">
            <div class="task-name">${taskName}</div>
            <div class="task-status">${state}</div>
            <div class="time-info">${timeInfo}</div>
          </div>
          <div class="status-indicator">${this.getStatusIcon(state)}</div>
        </div>
      </ha-card>
    `;

    // Add long press event listeners
    const card = this.shadowRoot.querySelector('ha-card');
    const container = this.shadowRoot.querySelector('.rtask-container');
    const progressBar = this.shadowRoot.querySelector('.long-press-progress');
    
    // Mouse events
    card.addEventListener('mousedown', (e) => this.startLongPress(e, container, progressBar));
    card.addEventListener('mouseup', () => this.endLongPress(container, progressBar));
    card.addEventListener('mouseleave', () => this.cancelLongPress(container, progressBar));
    
    // Touch events for mobile
    card.addEventListener('touchstart', (e) => this.startLongPress(e, container, progressBar));
    card.addEventListener('touchend', () => this.endLongPress(container, progressBar));
    card.addEventListener('touchcancel', () => this.cancelLongPress(container, progressBar));
  }

  getTimeInfo(entity) {
    const attributes = entity.attributes;
    const state = entity.state;
    
    if (state === 'Never Done') {
      return 'Never completed';
    }
    
    if (!attributes.last_completed) {
      return '';
    }

    const secondsSince = attributes.seconds_since_completed || 0;
    const minSeconds = attributes.min_duration_seconds || 0;
    const maxSeconds = attributes.max_duration_seconds || 0;

    if (state === 'Done') {
      const timeUntilDue = minSeconds - secondsSince;
      return `Due in ${this.formatDuration(timeUntilDue)}`;
    } else if (state === 'Due') {
      const timeUntilOverdue = maxSeconds - secondsSince;
      return `Overdue in ${this.formatDuration(timeUntilOverdue)}`;
    } else if (state === 'Overdue') {
      const timeOverdue = secondsSince - maxSeconds;
      return `Overdue by ${this.formatDuration(timeOverdue)}`;
    }

    return '';
  }

  formatDuration(seconds) {
    if (seconds < 0) seconds = 0;
    
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
  }

  getStatusColor(state) {
    switch (state.toLowerCase()) {
      case 'never done': return 'var(--disabled-text-color)';
      case 'done': return 'var(--success-color)';
      case 'due': return 'var(--warning-color)';
      case 'overdue': return 'var(--error-color)';
      default: return 'var(--primary-color)';
    }
  }

  getStatusIcon(state) {
    switch (state.toLowerCase()) {
      case 'never done': return '○';  // Empty circle
      case 'done': return '✓';       // Checkmark
      case 'due': return '!';        // Exclamation mark
      case 'overdue': return '⚠';    // Warning symbol
      default: return '?';
    }
  }

  startLongPress(event, container, progressBar) {
    // Prevent default to avoid text selection
    event.preventDefault();
    
    // Clear any existing timer
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
    }
    
    // Add visual feedback
    container.classList.add('long-press-active');
    progressBar.classList.add('active');
    
    // Start the long press timer
    this.longPressTimer = setTimeout(() => {
      this.handleLongPress();
      this.endLongPress(container, progressBar);
    }, this.longPressDelay);
  }
  
  endLongPress(container, progressBar) {
    if (this.longPressTimer) {
      clearTimeout(this.longPressTimer);
      this.longPressTimer = null;
    }
    
    // Remove visual feedback
    container.classList.remove('long-press-active');
    progressBar.classList.remove('active');
  }
  
  cancelLongPress(container, progressBar) {
    this.endLongPress(container, progressBar);
  }

  handleLongPress() {
    if (!this._hass || !this.config.entity) return;

    const entity = this._hass.states[this.config.entity];
    if (!entity) return;

    // Call the mark_done service
    this._hass.callService('rtask', 'mark_done', {
      entity_id: this.config.entity
    });
    
    // Optional: Add haptic feedback if available
    if (navigator.vibrate) {
      navigator.vibrate(50);
    }
  }

  getCardSize() {
    return 1;
  }
}

customElements.define('rtask-card', RTaskCard);

// Tell Home Assistant about this card
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'rtask-card',
  name: 'RTask Card',
  description: 'A card for displaying and managing RTask entities'
});

console.info(
  `%c  RTASK-CARD %c v1.0.0 `,
  'color: orange; font-weight: bold; background: black',
  'color: white; font-weight: bold; background: dimgray'
);