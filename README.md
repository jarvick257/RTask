# RTask - Recurring Task Tracker for Home Assistant

**RTask** is a Home Assistant custom integration that helps you track and manage recurring household tasks with flexible time windows and persistent completion tracking.

## What is RTask?

RTask is designed for **recurring tasks that don't have fixed schedules** but need to be done within certain time intervals. Instead of rigid "every Tuesday" schedules, RTask uses flexible time windows.

### Perfect for tasks like:
- 🪴 **Watering plants** (every 3-5 days, depending on weather)
- 🧽 **Cleaning appliances** (descale coffee machine every 2-3 months)
- 🐱 **Pet care** (clean litter box every 12-24 hours)
- 🏠 **Home maintenance** (change air filter every 3-6 months)
- 🧹 **Household chores** (vacuum stairs weekly, but some flexibility is fine)

## What RTask is NOT

❌ **Not a calendar or scheduler** - It doesn't automatically schedule tasks or send notifications
❌ **Not for one-time tasks** - Use Home Assistant's built-in to-do lists for those
❌ **No automatic task detection** - RTask doesn't automatically detect when tasks are completed (like sensing when you water plants), but you can integrate it with Home Assistant automations

## Why RTask?

### The Problem
Many household tasks need regular attention but don't require rigid scheduling:
- Did I water the plants this week?
- When did I last descale the washing machine?
- Has anyone cleaned the cat's litter box today?

Traditional calendars and reminders are too rigid - life happens, schedules change, and sometimes tasks can wait an extra day or two.

### The Solution
RTask gives each task a **flexible time window**:
- **Minimum interval**: "Don't worry about this yet" (e.g., plant watered 2 days ago)
- **Maximum interval**: "This really needs attention now" (e.g., plant not watered for 7 days)

### Key Benefits
✅ **Persistent tracking** - Completion times survive Home Assistant restarts
✅ **Flexible scheduling** - Time windows instead of rigid schedules
✅ **Accidental-completion protection** - Long-press prevents misclicks
✅ **Multiple time units** - Configure in seconds, minutes, hours, or days

And with a little help from [auto-entities](https://github.com/thomasloven/lovelace-auto-entities):
✅ **Visual dashboard** - See all tasks and their urgency at a glance
✅ **Priority sorting** - Overdue tasks automatically appear first

## Installation

This integration is available through HACS (Home Assistant Community Store).

1. Install RTask through HACS
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Add Integration
4. Search for "RTask" and add your first task

## Dashboard Setup

For the best user experience, we recommend creating a dedicated RTask dashboard with automatic sorting and an easy way to add new tasks.

### Prerequisites

Install the **auto-entities** card from HACS:
1. Open HACS > Frontend
2. Search for "auto-entities" by Thomas Lovén
3. Install and restart Home Assistant

### Dashboard Configuration

Create a new dashboard or add this to an existing one:

```yaml
title: Task Dashboard
views:
  - title: Tasks
    cards:
      # Add Task Button
      - type: button
        name: "Add New Task"
        icon: mdi:plus-circle
        tap_action:
          action: navigate
          navigation_path: "/config/integrations/integration/rtask"
        card_mod:
          style: |
            ha-card {
              --ha-card-background: var(--primary-color);
              color: white;
            }

      # Automatically sorted task list
      - type: custom:auto-entities
        card:
          type: vertical-stack
          title: "Current Tasks"
        filter:
          include:
            - domain: sensor
              integration: rtask
              options:
                type: custom:rtask-card
        sort:
          method: attribute
          attribute: state
          numeric: false
          # Sort by priority: Overdue -> Due -> Never Done -> Done
          map:
            "Overdue": 1
            "Due": 2
            "Never Done": 3
            "Done": 4
```

### Alternative: Simple Manual Layout

If you prefer not to use auto-entities, you can create a manual layout:

```yaml
title: Task Dashboard
views:
  - title: Tasks
    cards:
      # Add Task Button
      - type: button
        name: "Add New Task"
        icon: mdi:plus-circle
        tap_action:
          action: navigate
          navigation_path: "/config/integrations/integration/rtask"

      # Manual task cards (add your entity IDs)
      - type: custom:rtask-card
        entity: sensor.rtask_water_plants
      - type: custom:rtask-card
        entity: sensor.rtask_descale_washing_machine
      - type: custom:rtask-card
        entity: sensor.rtask_clean_cat_toilet
```

### Using the Dashboard

- **Long press** any task card for 0.8 seconds to mark it as completed
- **Click "Add New Task"** to quickly add new tasks
- Tasks are automatically sorted by priority (Overdue tasks appear first)
- Visual indicators make it easy to see which tasks need attention

The cards use color coding:
- 🔴 **Red (Overdue)**: Tasks that should have been done already (with pulsing animation)
- 🟡 **Yellow (Due)**: Tasks that are ready to be done
- ⚫ **Gray (Never Done)**: Tasks that haven't been completed yet
- 🟢 **Green (Done)**: Recently completed tasks

## Automation Integration

While RTask tasks are manually marked complete by default, you can create Home Assistant automations to automatically mark tasks as done when certain conditions are met.

### Available Service

RTask provides the `rtask.mark_done` service that can be called from any automation:

```yaml
service: rtask.mark_done
data:
  entity_id: sensor.rtask_your_task_name
```

### Automation Examples

**Smart Plant Watering Detection:**
```yaml
automation:
  - alias: "Mark plant watering task done"
    description: "Automatically mark plant task done when moisture sensor detects watering"
    trigger:
      - platform: state
        entity_id: sensor.plant_moisture_sensor
        to: "wet"
    condition:
      - condition: state
        entity_id: sensor.rtask_water_plants
        state: "Due"  # Only mark done if task is actually due
    action:
      - service: rtask.mark_done
        data:
          entity_id: sensor.rtask_water_plants
```

**Robot Vacuum Completion:**
```yaml
automation:
  - alias: "Mark vacuum task done"
    description: "Mark vacuum task complete when robot finishes cleaning"
    trigger:
      - platform: state
        entity_id: vacuum.robot_vacuum
        to: "returning"
    action:
      - service: rtask.mark_done
        data:
          entity_id: sensor.rtask_vacuum_living_room
```

**Time-based Medication Reminder:**
```yaml
automation:
  - alias: "Mark daily medication done"
    description: "Automatically mark medication task done at specific time"
    trigger:
      - platform: time
        at: "08:00:00"
    condition:
      - condition: state
        entity_id: input_boolean.took_medication_today  # Your manual confirmation
        state: "on"
    action:
      - service: rtask.mark_done
        data:
          entity_id: sensor.rtask_daily_medication
      - service: input_boolean.turn_off
        target:
          entity_id: input_boolean.took_medication_today
```

This flexibility allows you to start with manual task completion and gradually add smart home integration as your system grows!

