class RTaskCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
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
        }
        .rtask-info {
          flex: 1;
        }
        .task-name {
          font-size: 16px;
          font-weight: 500;
          margin-bottom: 4px;
        }
        .task-status {
          font-size: 14px;
          color: var(--secondary-text-color);
          margin-bottom: 2px;
        }
        .time-info {
          font-size: 12px;
          color: var(--secondary-text-color);
        }
        .status-indicator {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          margin-left: 12px;
        }
        .status-never { background-color: var(--disabled-text-color); }
        .status-done { background-color: var(--success-color); }
        .status-due { background-color: var(--warning-color); }
        .status-overdue { background-color: var(--error-color); }
        .error {
          color: var(--error-color);
          padding: 16px;
        }
      </style>
      
      <ha-card @click="${this.handleClick}">
        <div class="rtask-container">
          <div class="rtask-info">
            <div class="task-name">${taskName}</div>
            <div class="task-status">${state}</div>
            <div class="time-info">${timeInfo}</div>
          </div>
          <div class="status-indicator status-${state.toLowerCase().replace(' ', '-')}"></div>
        </div>
      </ha-card>
    `;

    // Add click event listener
    this.shadowRoot.querySelector('ha-card').addEventListener('click', () => this.handleClick());
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

  handleClick() {
    if (!this._hass || !this.config.entity) return;

    const entity = this._hass.states[this.config.entity];
    if (!entity) return;

    // Call the mark_done service
    this._hass.callService('rtask', 'mark_done', {
      entity_id: this.config.entity
    });
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