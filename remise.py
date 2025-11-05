import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO

# ============================================================
# 🔐 AUTHENTIFICATION
# ============================================================
if "login" not in st.session_state:
    st.session_state["login"] = False
if "page" not in st.session_state:
    st.session_state["page"] = "Accueil"

def login(username, password):
    users = {
        "aurore": {"password": "12345", "name": "Aurore Demoulin"},
        "laure.froidefond": {"password": "Laure2019$", "name": "Laure Froidefond"},
        "Bruno": {"password": "Toto1963$", "name": "Toto El Gringo"},
        "Manana": {"password": "193827", "name": "Manana"}
    }
    if username in users and password == users[username]["password"]:
        st.session_state["login"] = True
        st.session_state["username"] = username
        st.session_state["name"] = users[username]["name"]
        st.session_state["page"] = "Accueil"
        st.success(f"Bienvenue {st.session_state['name']} 👋")
        st.rerun()
    else:
        st.error("❌ Identifiants incorrects")

if not st.session_state["login"]:
    st.title("🔑 Connexion espace expert-comptable")
    username_input = st.text_input("Identifiant")
    password_input = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        login(username_input, password_input)
    st.stop()

# ============================================================
# 🧾 PAGE PRINCIPALE - Remise de chèques
# ============================================================
st.title("🏦 Génération d’écritures comptables - Remise de chèques")
st.write("Uploadez un fichier PDF de remise de chèques pour générer automatiquement les écritures comptables correspondantes.")

uploaded_file = st.file_uploader("📤 Importer le PDF de remise de chèques", type=["pdf"])

if uploaded_file:
    try:
        # --- Lecture du texte du PDF ---
        with pdfplumber.open(uploaded_file) as pdf:
            texte_complet = ""
            for page in pdf.pages:
                texte_complet += page.extract_text() + "\n"

        # --- Aperçu du texte brut (debug) ---
        st.subheader("🪶 Aperçu du texte extrait du PDF (1000 premiers caractères)")
        st.text(texte_complet[:1000])

        # --- Extraction de la date de remise ---
        match_date = re.search(r"\d{2}/\d{2}/\d{2}", texte_complet)
        date_remise = match_date.group(0) if match_date else ""

        # --- Nouvelle regex hyper robuste ---
        pattern = (
            r"([A-ZÉÈÊÂÎÔÛÀÙÇa-zéèêâîôûàùç\s]+?)"  # Nom du tireur
            r"\s+([\d,\s]+(?:\(non soldé\))?)"     # Numéro(s) de chèque + (non soldé) éventuel
            r"\s*/\s*\d{2}/\d{2}/\d{4}"            # Date
            r"\s+([\d\s,]+)"                       # Montant
        )

        lignes = re.findall(pattern, texte_complet)

        data = []
        total_remise = 0.0

        for tireur, num_cheque, montant in lignes:
            # Nettoyage du nom et du numéro
            tireur_clean = tireur.strip().title()
            num_cheque_clean = re.sub(r"\(.*?\)", "", num_cheque).replace(" ", "").strip(",")
            tireur_nom = tireur_clean.split()[0].upper()
            compte = f"4110{tireur_nom[0]}"

            # Conversion du montant
            try:
                montant_float = float(montant.replace(" ", "").replace(",", "."))
            except:
                continue
            total_remise += montant_float

            libelle = f"{tireur_clean} - {num_cheque_clean}"
            data.append([date_remise, "OD", compte, libelle, "", round(montant_float, 2)])

        # --- Ligne banque (débit global) ---
        data.append([date_remise, "OD", "5112", f"Remise de chèques {date_remise}", round(total_remise, 2), ""])

        # --- Création du DataFrame ---
        df = pd.DataFrame(data, columns=["Date", "Journal", "Compte", "Libellé", "Débit", "Crédit"])

        # ============================================================
        # ✅ Vérification de l'équilibre comptable
        # ============================================================
        debit_total = df["Débit"].apply(pd.to_numeric, errors="coerce").sum()
        credit_total = df["Crédit"].apply(pd.to_numeric, errors="coerce").sum()
        ecart = round(debit_total - credit_total, 2)

        if ecart == 0:
            st.success(f"✅ Écritures équilibrées (Total Débit = Total Crédit = {debit_total:,.2f} €)")
        else:
            st.warning(f"⚠️ Écart détecté : {ecart:,.2f} € (Débit={debit_total:,.2f} / Crédit={credit_total:,.2f})")

        # --- Affichage du tableau ---
        st.dataframe(df, use_container_width=True)

        # ============================================================
        # 💾 Export Excel en mémoire
        # ============================================================
        buffer = BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            label="📥 Télécharger le fichier Excel",
            data=buffer,
            file_name=f"remise_cheques_{date_remise.replace('/', '-')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"❌ Erreur lors du traitement du fichier : {e}")
