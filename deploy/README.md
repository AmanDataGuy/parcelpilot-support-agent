# EC2 Deployment

Plain venv + systemd, no Docker, no reverse proxy — matches the scale of this app.

## 1. Launch the instance

- **AMI**: Ubuntu 22.04 LTS
- **Instance type**: t3.micro is enough (FastAPI + Streamlit + pandas, no GPU/heavy compute)
- **Security group**: inbound TCP 22 (SSH, restrict to your IP), 8501 (Streamlit, `0.0.0.0/0`), 8000 (FastAPI, `0.0.0.0/0` — or restrict if you don't want the API directly reachable)
- **Key pair**: create or reuse one you can SSH in with

## 2. Bootstrap

```bash
ssh -i your-key.pem ubuntu@<instance-public-ip>
curl -fsSL https://raw.githubusercontent.com/AmanDataGuy/parcelpilot-support-agent/main/deploy/setup.sh | bash
```

This clones the repo to `~/parcelpilot`, creates a venv, and installs both requirement files. The data pack (PDFs + xlsx) is already committed in the repo, so nothing further to upload.

## 3. Configure and start

```bash
nano ~/parcelpilot/.env                 # set GEMINI_API_KEY

sudo cp ~/parcelpilot/deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now parcelpilot-backend parcelpilot-frontend
```

## 4. Verify

```bash
curl http://localhost:8000/accounts     # on the instance
sudo systemctl status parcelpilot-backend parcelpilot-frontend
journalctl -u parcelpilot-backend -f    # logs, if something's wrong
```

Then open `http://<instance-public-ip>:8501` in a browser.

## Updating after a code change

```bash
cd ~/parcelpilot && git pull
./.venv/bin/pip install -r backend/requirements.txt -r frontend/requirements.txt
sudo systemctl restart parcelpilot-backend parcelpilot-frontend
```
