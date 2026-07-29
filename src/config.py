import os
from dotenv import load_dotenv

load_dotenv()

def get_secret(key: str) -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets[key]
    except Exception:
        return None
