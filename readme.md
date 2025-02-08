# Karmine Corp Calendar

[![Backend](https://img.shields.io/badge/backend-python-blue)](https://www.python.org/)
[![Donate](https://img.shields.io/badge/donate-❤️-ff69b4?label=buy%20me%20a%20coffee)](https://www.buymeacoffee.com/totama)

- [Description](#description)
- [Features](#features)
- [Technologies used](#technologies-used)
- [Installation](#installation)
- [Usage](#usage)
- [Contribution](#contribution)

## Description

This project provides a calendar solution for Karmine Corp. It includes a backend that generates a calendar file, allowing users to subscribe and automatically receive updates on matches and events. Future development will include a frontend for additional features.

## Features

- **Backend**
  - Generation of a calendar file in ICS format.
  - Automatic updates of events and matches.
  - Integration with Google Calendar and other compatible applications.
- **Frontend** (Coming Soon):
  - Additional features and functionalities (details to be revealed).

## Technologies used

- **Backend**: Python with FastAPI
- **API**: Pandascore for fetching match data
- **Frontend**: (Details to be announced)

## Installation

1. backend

```bash
git clone https://github.com/Totamaa/kcalendar
cd kcalendar/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
nano .env # setup environments variables by following /backend/config/settings.py variables
fastapi dev main.py
```

## Usage

To subscribe to the calendar, use the following link in your preferred calendar application:

<https://kcalendar.eu/api/files/calendar.ics>

## Contribution

Contributions are welcome! Feel free to open an issue or submit a pull request.
