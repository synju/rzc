# RZC Core - Agent Instructions

## Python Virtual Environment

**ALWAYS** use the `venv` folder in the project root:
```
./venv/
```

**NEVER** create or reference a `.venv` folder. The correct venv is named `venv` (not hidden).

## Activating the venv

```bash
cd /path/to/rzc-core
source venv/bin/activate
```

## Running the App

```bash
cd /path/to/rzc-core
source venv/bin/activate
python app.py
```

## Installing Dependencies

```bash
cd /path/to/rzc-core
source venv/bin/activate
pip install -r requirements.txt
```

## Database

- Container name: `rzc-postgres`
- Database: `rzc_cloud_wallet_db`
- User: `rzc`
- Password: `rzc_password`
- Port: `5432`

## Running Scripts

```bash
cd /path/to/rzc-core
source venv/bin/activate
python <script_name>.py
```
