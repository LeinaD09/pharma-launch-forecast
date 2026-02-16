"""
Pharma Launch Forecast – Multi-Page Application
================================================
Five use cases accessible via sidebar navigation.
"""

import sys
import os
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st

st.set_page_config(
    page_title="Pharma Launch Forecast",
    page_icon="\U0001f48a",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Reload to bust Streamlit Cloud .pyc cache after deployments
import models.brand_competition_engine as _bce
importlib.reload(_bce)

from main import show as eliquis_show
import glp1 as _glp1_mod
importlib.reload(_glp1_mod)
from glp1 import show as glp1_show
from rx_otc import show as rx_otc_show
from sildenafil import show as sildenafil_show
from sildenafil_patient import show as sildenafil_patient_show
from ophthalmology import show as ophthalmology_show

# ─── Pages ──────────────────────────────────────────────────────────────
eliquis_page = st.Page(eliquis_show, title="Eliquis Generic Entry", icon="\U0001f4c9", url_path="eliquis", default=True)
glp1_page = st.Page(glp1_show, title="GLP-1 Brand Competition", icon="\U0001f489", url_path="glp1")
rx_otc_page = st.Page(rx_otc_show, title="Rx-to-OTC Switch (PPI)", icon="\U0001f6d2", url_path="rx-otc")
sildenafil_page = st.Page(sildenafil_show, title="Sildenafil Rx-to-OTC Switch", icon="\U0001f48a", url_path="sildenafil")
sildenafil_patient_page = st.Page(sildenafil_patient_show, title="Sildenafil Patient-Based", icon="\U0001f9ec", url_path="sildenafil-patient")
ophthalmology_page = st.Page(ophthalmology_show, title="Eye Care Franchise", icon="\U0001f441", url_path="eyecare")

nav = st.navigation(
    {
        "Launch Forecasts": [eliquis_page, glp1_page, rx_otc_page, sildenafil_page, sildenafil_patient_page, ophthalmology_page],
    }
)
nav.run()
