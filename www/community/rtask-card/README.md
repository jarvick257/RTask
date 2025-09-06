# RTask Card

A custom Lovelace card for the RTask Home Assistant integration.

## Installation

The card is automatically installed when you install the RTask integration.

## Usage

Add the card to your dashboard:

```yaml
type: custom:rtask-card
entity: sensor.rtask_your_task_name
```

## Features

- Click to mark task as done
- Visual status indicators with colors:
  - Gray: Never Done
  - Green: Done (recently completed)
  - Yellow: Due (can be done now)
  - Red: Overdue (should be done)
- Time remaining/overdue information
- Responsive design

## Configuration

The card requires only one parameter:

- `entity` (required): The RTask sensor entity ID

Example:
```yaml
type: custom:rtask-card
entity: sensor.rtask_water_plants
```