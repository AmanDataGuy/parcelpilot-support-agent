"""Streamlit chat UI: account switcher, chat, tool-use trace, action confirm.

ponytail: Streamlit's own st.session_state is the whole client-side state
store — no Redux-style store, no separate frontend framework.
"""
import os
from pathlib import Path

import requests
import streamlit as st

API_URL = os.environ.get("PARCELPILOT_API_URL", "http://localhost:8000")
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo.svg"

st.set_page_config(page_title="ParcelPilot Support", page_icon=str(LOGO_PATH))

header_logo, header_title = st.columns([1, 8], vertical_alignment="center")
header_logo.image(str(LOGO_PATH), width=48)
header_title.title("ParcelPilot Support")

# --- account switcher (mocked login) ---------------------------------------
accounts = requests.get(f"{API_URL}/accounts", timeout=10).json()
account_labels = {a["account_id"]: f"{a['account_name']} ({a['account_id']}, {a['plan']})" for a in accounts}
selected_account = st.sidebar.selectbox(
    "Logged in as",
    options=list(account_labels.keys()),
    format_func=lambda aid: account_labels[aid],
)
st.sidebar.caption("Mocked auth: this dropdown stands in for a real customer login.")

if "chat_history" not in st.session_state or st.session_state.get("account_id") != selected_account:
    st.session_state.chat_history = []  # [(role, text)]
    st.session_state.account_id = selected_account
    st.session_state.pending_actions = []

# --- confirmation banner for any pending action -----------------------------
for pending in st.session_state.pending_actions:
    with st.container(border=True):
        st.warning(f"Proposed action: **{pending['action_type']}** — {pending['details']}")
        col1, col2 = st.columns(2)
        if col1.button("Confirm", key=f"confirm_{pending['action_id']}"):
            resp = requests.post(f"{API_URL}/confirm", json={"action_id": pending["action_id"]}, timeout=10)
            st.session_state.pending_actions.remove(pending)
            # st.success/st.error here would be wiped by st.rerun() below before
            # the user ever sees them — record the outcome in chat_history
            # instead, so it survives the rerun and stays in the conversation log.
            if resp.ok:
                note = f"✅ Action executed: **{pending['action_type']}** (id `{pending['action_id']}`)."
            else:
                note = f"❌ Action failed: {resp.json().get('detail', 'unknown error')}"
            st.session_state.chat_history.append(("assistant", note))
            st.rerun()
        if col2.button("Cancel", key=f"cancel_{pending['action_id']}"):
            st.session_state.pending_actions.remove(pending)
            st.rerun()

# --- chat history ------------------------------------------------------------
for role, text in st.session_state.chat_history:
    st.chat_message(role).write(text)

user_message = st.chat_input("Ask about an order, cancellation, SLA, or account issue...")
if user_message:
    st.session_state.chat_history.append(("user", user_message))
    st.chat_message("user").write(user_message)

    with st.spinner("Thinking..."):
        resp = requests.post(
            f"{API_URL}/chat",
            json={"account_id": selected_account, "message": user_message},
            timeout=60,
        )
    if not resp.ok:
        st.error(resp.text)
    else:
        data = resp.json()
        st.session_state.chat_history.append(("assistant", data["reply"]))
        st.chat_message("assistant").write(data["reply"])

        if data["trace"]:
            with st.expander(f"🔧 Tool calls this turn ({len(data['trace'])})"):
                for step in data["trace"]:
                    st.markdown(f"**{step['tool']}**")
                    st.json({"input": step["input"], "result": step["result"]})

        st.session_state.pending_actions.extend(data["pending_actions"])
        if data["pending_actions"]:
            st.rerun()
